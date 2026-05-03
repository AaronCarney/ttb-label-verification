# Epoch 6 — Batch Processor + SSE + Override

> **Parent:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **Tier:** L1 (epoch-level).
> **Substitutability seam owned:** none — but the `BatchInFlightState` shape is designed so a future production swap (Kafka consumer groups / RabbitMQ `prefetch=1` per ARCH §4.2.7 / T6 §Q6.7) can replace the asyncio.Queue without changing the Web layer.
> **Depends on:** **E5** (`Evaluator.evaluate()` + audit/metrics envelopes).

---

## 1. Goal

Wrap the single-label flow in a pull-based, reactive-streams-style batch processor that handles 50 labels at human pace; stream per-label results via SSE; ship the override endpoint that records reviewer disagreement with audit fidelity. After E6, `POST /batches` accepts a PRD §6.3 envelope, the SSE endpoint streams per-label PRD §6.2 envelopes augmented with `queue_position`, the M-of-N anomaly detector fires non-blocking advisories, mid-batch overrides do not stop the queue, and `POST /labels/{eid}/overrides` records FR-801 audit fields.

**Performance posture.** First label of a batch returns under NFR-PERF-001 (FR-401); subsequent labels are pre-fetched at `LOOKAHEAD_K=3` so the reviewer never blocks on extraction. P/R ≈ 0.01 (T6 TL;DR) — the system is human-bound and lookahead is generous coverage, not a throughput optimization.

---

## 2. Components delivered

### 2.1 Batch state (`app/batch/state.py`)

Per ARCH §6.7:

- `BatchItem` (frozen Pydantic, except `state` / `result` mutate via `model_copy`): `label_id`, `application_ref`, `state ∈ {queued, processing, ready, presented, reviewed, disposed}`, with side-edge `failed(reason)`; `result: DispositionEnvelope | None`; `enqueued_at`.
- `BatchInFlightState`: `batch_id` (UUID4), `agent_id` (single-value MVP), `items: list[BatchItem]` (in submission order), `current_index`, `lookahead_k` (default 3), `recent_dispositions: deque[ReasonCode | None]` (sliding window length 10), `calls: deque[CallRecord]` (`maxlen=200`).
- `app.state.batches: dict[str, BatchInFlightState]` — process-local; evicted on session end.

### 2.2 Worker (`app/batch/worker.py`)

Per ARCH §4.2.7 / §5.2:

- `BatchWorker.run(batch_id: str)` — async coroutine; consumes from the per-batch asyncio.Queue (`maxsize=k+1`); calls `Evaluator.evaluate()` per item; writes results to `BatchInFlightState`; emits SSE events through a per-batch event bus.
- Pull-based demand: `request(n)` semantics are emulated by the SSE consumer's `EventSource` reconnect/backpressure behavior. The producer (Web layer's intake) does **not** enqueue beyond outstanding demand. The asyncio.Queue's bounded `maxsize` is the structural enforcement.
- First-label-individual: the worker **does not** wait to fill the lookahead window before responding on item 1 (FR-401). Validates AC-FR-401: first label returns under NFR-PERF-001 even with a 50-item submission.
- Mid-batch override (FR-404): the override endpoint mutates the `BatchItem.result` and surfaces an SSE event; the worker continues — it does not check overrides as a stop condition.

### 2.3 Bounded queue (`app/batch/queue.py`)

Per ARCH §4.2.7:

- Thin wrapper around `asyncio.Queue(maxsize=k+1)` with type hints for `BatchItem`.
- Accept-side (intake): `await queue.put(item)` blocks if full → backpressure to producer.
- Pop-side (worker): `await queue.get()` blocks if empty → cooperative yield.

### 2.4 Anomaly detector (`app/batch/anomaly.py`)

Per ARCH §5.2 / FR-405:

- `AnomalyDetector.observe(reason_code: ReasonCode | None) -> AnomalyAdvisory | None`.
- Sliding window length 10; fires when M-of-N (default M=5, N=10) consecutive labels have the **same** reason code.
- Non-blocking — emits an advisory event over SSE that the UI displays as a dismissable toast/alert.
- Reset on advisory dismissal (the dismissal handler clears the window).

### 2.5 Batch endpoints (`app/api/batches.py`)

Per ARCH §3.2:

- `POST /batches` — accepts a PRD §6.3 envelope (zip or multi-file); validates; spawns the worker via `asyncio.create_task`; returns `202 Accepted` with `batch_id`.
- `GET /batches/{batch_id}/stream` — SSE subscription via `sse-starlette`; emits per-label disposition envelopes augmented with `queue_position` and `batch_id`; emits anomaly advisories; emits `stream-end` when the batch completes.
- `GET /batches/{batch_id}` — returns current batch state + per-label disposition list (snapshot, no streaming).
- Both endpoints are **not** gated by DEV_MODE — they are part of the standard MVP surface.

### 2.6 Override endpoint (`app/api/overrides.py`)

Per PRD FR-800–804 / ARCH §3.2:

- `POST /labels/{evaluation_id}/overrides` — accepts:
  ```json
  { "reason_code": "BIN.SUB.SPECIFIC", "applied_disposition": "pass | fail | needs_review", "justification_text": "string | null" }
  ```
- Validates `reason_code` against the loaded reason-code registry (E2).
- Mutates the `BatchItem.result.audit_trail.overrides` list with an `OverrideEntry`: `field_name | null`, `original_disposition`, `applied_disposition`, `reason_code`, `justification_text`, `reviewer_id` (session-scoped — for prototype, a placeholder that's logged as `"session-<random-uuid>"`), `timestamp`.
- Justification is **optional** in MVP per FR-804.
- Surfaces the updated audit-trail entry on the SSE stream.

### 2.7 SSE event bus (`app/api/_sse_bus.py`)

A small per-batch async event bus. Each subscriber gets its own `asyncio.Queue`; broadcast pushes to all subscribers. The Web layer's SSE response loop pulls from the subscriber queue and yields `sse_starlette.EventSourceResponse`.

Connection-close detection: when the client disconnects (FastAPI raises `ClientDisconnect`), the subscriber is removed; the worker continues so a reconnecting consumer can resume from `current_index`.

### 2.8 Test surface

- `tests/test_batch_worker.py` — fixture-05-style 50-label batch processes; first label returns under NFR-PERF-001 (FR-401); subsequent labels stream out at human pace.
- `tests/test_batch_lookahead.py` — when reviewer is on item N, items N+1 and N+2 are pre-fetched (k=3, default). Asserted by checking `BatchItem.state` transitions: `queued → processing → ready` happens for N+1/N+2 before the reviewer "consumes" item N.
- `tests/test_batch_pull_demand.py` — when the SSE consumer's queue is full, the worker does not enqueue beyond `maxsize=k+1`. Asserted by holding the consumer subscription stationary and verifying the worker's queue saturates at `k+1` in-flight items.
- `tests/test_batch_anomaly.py` — 5 of 10 consecutive labels with the same reason code triggers an advisory event; the advisory is dismissable; processing continues.
- `tests/test_batch_mid_override.py` — submitting `POST /overrides` mid-batch updates the audit trail and emits an SSE event but the worker continues.
- `tests/test_batch_browser_disconnect.py` — simulated `EventSource` disconnect: subscriber is cleaned up; worker continues; reconnecting consumer resumes from `current_index`.
- `tests/test_batch_first_label_individual.py` — fixture-05 first label returns < 5 s (P99) and < 2.7 s (P50) — same AC as NFR-PERF-001 against a batch envelope.
- `tests/test_override_endpoint.py` — happy path; rejects unknown reason codes; rejects override on a non-existent `evaluation_id`; records all FR-801 fields.
- `tests/test_override_audit_trail.py` — original disposition, applied disposition, reason code, justification (optional), reviewer_id, timestamp — all present in the audit-trail's `overrides[]` array.
- `tests/test_sse_stream.py` — events emitted in order; `queue_position` increments; `stream-end` event fires on completion; client disconnect handled.

---

## 3. Wire / data contracts owned by this epoch

E6 owns:

- `POST /batches` request shape (PRD §6.3) and response (`202 Accepted` + `batch_id`).
- `GET /batches/{batch_id}/stream` SSE event shape: per-label dispositions augmented with `queue_position` + `batch_id`; anomaly advisories; `stream-end`.
- `POST /labels/{evaluation_id}/overrides` request and response shapes.
- The `OverrideEntry` Pydantic model (declared in E1 schemas; populated here).
- The session-scoped `reviewer_id` convention (`"session-<uuid>"` string for the prototype; production-trajectory replaces with a real identity claim).

After E6, the entire wire surface is settled. E7 binds UI to it; E8 adds eval-only routes (`/eval`, `/healthz` already in E5).

---

## 4. Exit gate

The epoch lands when **all of these pass**:

1. `POST /batches` against a 50-item envelope returns `202` with a `batch_id`.
2. `GET /batches/{batch_id}/stream` streams per-label PRD §6.2 envelopes; total event count is `50 + N_advisories + 1` (per-label + anomaly + stream-end).
3. **AC-FR-401**: first label of a 50-item batch returns under NFR-PERF-001 (P50 ≤ 2.7 s, P99 ≤ 5.0 s) — same gate as E5 but exercised against the batch envelope.
4. **AC-FR-402**: lookahead k=3 verified by state-machine inspection.
5. **AC-FR-403**: pull-based demand verified — worker's queue saturates at `maxsize=k+1` when consumer holds.
6. **AC-FR-404**: mid-batch override does not stop the worker.
7. **AC-FR-405**: 5-of-10 same-reason advisory fires; advisory dismissable; processing continues.
8. `POST /labels/{eid}/overrides` records all FR-801 fields and surfaces over SSE.
9. Client disconnect mid-batch: subscriber cleaned up within 1 s; worker continues; reconnecting consumer resumes from the last-delivered `queue_position` per ARCH §5.2 / T6 §Q6.6 contract.
10. `LOOKAHEAD_K=2` (override) reduces lookahead to 2 with no other behavior change; `LOOKAHEAD_K=4` increases it to 4.
11. `app.state.batches[batch_id]` is fully evicted on session end (process restart) — no persistence (NFR-DATA-001/002).

---

## 5. TDD strategy

**Mockable** —

- `Evaluator.evaluate()` — replaced with a fake that returns canned `DispositionEnvelope`s with controllable per-call latency. This is the right fake for batch tests because it isolates the queueing/SSE/override logic from the rule engine and the LLMs.
- The clock — for the first-label-latency tests, real time; for state-transition tests, freeze time via `freezegun` or `time-machine` so the asserts are deterministic.

**Real** —

- `asyncio.Queue`, `asyncio.create_task`, `asyncio.wait_for`.
- `sse-starlette`'s `EventSourceResponse`.
- The actual HTTP client behavior of `httpx.AsyncClient` for the SSE consumer side.

**Integration test (the canary).** A single test that submits a 5-item batch with a fake evaluator that takes `0.3s` per label, opens an SSE subscription, drains events, asserts: 5 per-label events, then `stream-end`, then the SSE connection closes. This test is the closest thing to a smoke test for the whole epoch and should be the last-touched test in the L2 plan.

---

## 6. Out of scope for this epoch

- Multi-agent topology (`agent_id` is structurally present per FR-403 but a single value in MVP — T6 §Q6.7 production swap).
- Persistent batch state (process restart loses the session per NFR-DATA-001/002).
- Auto-retry of failed labels (PRD OQ-PRD-2 — reviewer-initiated only in MVP).
- Importer-drop-scale demo (200–300 labels) — **stretch** (parent §8); E6 implements the substrate, E8 demonstrates it if the calendar permits.
- The override drawer keyboard model (the 3-keystroke UX target lives in **E7**); E6 ships the *server* override endpoint that the drawer calls.

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SSE connection state and the worker's queue state diverge under client disconnect / reconnect | Medium | Medium | The worker is decoupled from the SSE bus — disconnection drops the subscriber, the worker continues; reconnection re-attaches the subscriber and replays from `current_index`. Tested in `tests/test_batch_browser_disconnect.py`. |
| Under high reviewer pace (clicking through fast), the lookahead window oscillates | Low | Low | Lookahead is a soft target, not a hard contract — `maxsize=k+1` is the only hard structural cap. |
| The bounded queue blocks the producer indefinitely if the consumer never returns | Medium | Medium | The intake (`POST /batches`) does **not** wait on per-item enqueue beyond `maxsize`; the worker's `queue.put` blocks on the bounded queue when full, which is the correct backpressure. The endpoint returns 202 immediately after the batch is accepted into `app.state.batches`; population of the queue happens lazily as the worker consumes. |
| `EventSource` keepalive timeouts vary across browsers | Medium | Low | `sse-starlette` sends comment heartbeats every 15 s; reviewer-side keepalive is documented in the demo runbook (E8). |
| `OverrideEntry.reviewer_id` is just a stringified UUID — no real identity in MVP | Accepted | Low | OQ-PRD-1 / OQ-ARCH-3: the audit shape supports a real identity claim later; the MVP lift is intentionally trivial. |
| Anomaly detector misfires on a heterogeneous batch | Low | Low | M-of-N=5-of-10 is the conservative starting rule per T6; tunable via constructor; the advisory is non-blocking, so misfires are low-impact. |

---

## 8. L2 hand-off notes

When E6 lands:

1. Decompose into ~9 tasks: `state.py` → `queue.py` → `anomaly.py` → `_sse_bus.py` → `worker.py` (the big one) → `app/api/batches.py` (POST + 2 GET endpoints) → `app/api/overrides.py` → integration tests → first-label-perf test.
2. **Wave structure:** state.py + queue.py + anomaly.py + _sse_bus.py (parallel — small modules, no inter-deps) → worker.py (sequential, depends on state + queue + anomaly + bus) → endpoints (parallel after worker) → integration tests (sequential after endpoints).
3. The L2 plan **must** include a task that exercises a 5-item batch end-to-end with a fake evaluator and asserts the canary integration test from §5.
4. The L2 plan **must** include a task that verifies `app.state.batches[batch_id]` is fully eviction-safe on process exit (`atexit` or shutdown hook).

---

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial epoch-6 L1 doc. |
