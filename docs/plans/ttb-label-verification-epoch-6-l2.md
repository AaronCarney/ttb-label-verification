# TTB Label Verification — Epoch 6 (Batch Processor + SSE + Override) — L2 Implementation Plan

> **Version:** v0.1 (2026-05-04) — initial draft. See Change log for revision history.
>
> **For agentic workers:** REQUIRED EXECUTOR: `parallel-plan-executor`. Per olorin CLAUDE.md, `superpowers:subagent-driven-development` is obsolete and fully replaced by `parallel-plan-executor` (which injects the `task-executor` skill body for TDD enforcement). Each task lands as one Red→Green→Commit cycle (or, for the worker bundle, three sequential cycles). Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Parent L1:** [`ttb-label-verification-epoch-6-batch-override.md`](./ttb-label-verification-epoch-6-batch-override.md) (v0.1)
> **L1 index:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **E5 L2 (structural template):** [`ttb-label-verification-epoch-5-l2.md`](./ttb-label-verification-epoch-5-l2.md) (v0.6 — SHIPPED)
> **PRD:** [`docs/PRD.md`](../PRD.md) — FR-401 (first-label individual), FR-402 (lookahead k=3 default), FR-403 (pull-based demand), FR-404 (override-mid-batch), FR-405 (M-of-N anomaly), FR-800–804 (override audit fields), NFR-PERF-001 (5 s SLA against batch envelope), NFR-DATA-001/002 (no persistence)
> **ARCH:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — §3.2 (HTTP boundary), §4.2.7 (batch worker substrate; production-trajectory swap to Kafka/RabbitMQ `prefetch=1`), §5.2 (per-batch async event bus), §6.7 (`BatchInFlightState`), §10.1 (canonical reason-code taxonomy)
> **ADRs in scope:** D-004 (substitutability — `BatchInFlightState` shape preserved for future Kafka consumer-group / RabbitMQ swap), D-018 (audit/metrics split — overrides ride `audit_trail.overrides`, not `metrics`)

**Goal.** Land the pull-based, reactive-streams-style batch processor: `POST /batches` accepts a PRD §6.3 envelope and returns `202 Accepted` + a `batch_id`; the worker consumes a per-batch `asyncio.Queue` (`maxsize=k+1`) and feeds the existing E5 `Evaluator` per item; results stream via SSE in submission order with `queue_position` augmented; the M-of-N anomaly detector emits non-blocking advisories; mid-batch overrides surface via SSE without stopping the worker; `POST /labels/{evaluation_id}/overrides` records FR-801 audit fields against the validated reason-code registry. After E6, the wire surface is settled — E7 binds UI to the SSE stream + override endpoint; E8 adds eval-only routes.

**Architecture.** A single Python package `app/batch/` decomposed into four small, focused modules + a single thin worker class:

- `app/batch/state.py` — `InFlightBatch` in-memory companion to the frozen `BatchInFlightState` (E1 schema). Holds the mutable accumulators that don't belong inside frozen Pydantic: the per-batch `asyncio.Queue` (intake → worker), the SSE subscriber set, the `recent_dispositions: deque[ReasonCode | None]` sliding window, the per-batch `calls: deque[CallRecord]` ring buffer, the per-item `result: DispositionEnvelope | None` map, and the `current_index` cursor. Serialization-side state stays in the frozen `BatchInFlightState` snapshot.
- `app/batch/queue.py` — Thin typed wrapper around `asyncio.Queue(maxsize=k+1)` (`BoundedQueue[BatchItem]`). The `maxsize=k+1` is the single structural enforcement of pull-based demand (FR-403) — the worker's `await queue.put(item)` blocks when the consumer holds, which is the correct backpressure.
- `app/batch/anomaly.py` — `AnomalyDetector` with a sliding window of length `N=10` (default) and a configurable `M=5` threshold; `observe(reason_code)` returns an `AnomalyAdvisory` once `M` of the last `N` observations share the same code; `dismiss()` clears the window. Non-blocking — the advisory is broadcast over SSE; processing continues.
- `app/api/_sse_bus.py` — Per-batch async event bus. Subscribers register; broadcast pushes to every subscriber's individual `asyncio.Queue`; FastAPI's `ClientDisconnect` triggers subscriber prune. The Web layer's SSE response loop pulls from the subscriber queue and yields `sse_starlette.EventSourceResponse`-friendly dicts.
- `app/batch/worker.py` — `BatchWorker.run(batch_id)` async coroutine. Consumes from the per-batch `BoundedQueue`; calls the existing `Evaluator.evaluate()` per item; mutates `InFlightBatch.results[label_id]`; emits per-label SSE events with `queue_position`; observes the disposition through `AnomalyDetector`; surfaces advisories via SSE; emits `stream-end` on completion. **First-label-individual** (FR-401): the worker does not wait to fill the lookahead window before responding on item 0. **Mid-batch override** (FR-404): the worker continues — it does not check overrides as a stop condition.

The Evaluator (E5) is the inner per-item engine; the BatchWorker is the outer orchestration substrate. Web layer (`app/api/batches.py`, `app/api/overrides.py`) carries no batch logic — it spawns the worker via `asyncio.create_task` and proxies to the SSE bus + override mutation. `app.state.batches: dict[str, InFlightBatch]` is process-local; lifespan teardown evicts it (NFR-DATA-001/002).

**Tech stack.** Python 3.12, Pydantic v2 (E1), FastAPI (E1), `asyncio.Queue` + `asyncio.create_task` + `asyncio.wait_for`, `sse-starlette >= 2.1` (already pinned), `httpx.AsyncClient` for the SSE consumer side in tests. **No new top-level dependencies.**

**TDD posture.** Each task is one Red→Green→Commit cycle on a single narrow file (or one tightly coupled file group). The `task-executor` skill body (injected by `parallel-plan-executor`) enforces "one behavior per commit". One task bundles three cycles by necessity (T6 BatchWorker = 3 cycles: skeleton + lookahead/pull-demand + anomaly/override/completion) — that is the only multi-cycle task in the plan. Each commit is atomic and Conventional (`feat:`/`test:`/`chore:`/`docs:`/`fix:`). Pre-existing main is fast-forwarded after each task.

**Hard scope boundary.** This plan owns: `app/batch/{__init__,state,queue,anomaly,worker}.py`, `app/api/{batches,overrides,_sse_bus}.py`, **two additive single-line registration appends to `app/main.py` (T7 registers `batches.router`; T8 registers `overrides.router`) plus four lifespan-hook lines initializing and clearing `app.state.batches` and `app.state.buses`**, **a single additive change to `app/schemas/audit.py::OverrideEntry`: `field_name: str` → `field_name: str | None = None` so the override endpoint can record whole-envelope overrides per L1 §2.6 (the L1 spec describes `field_name | null`; the existing E1 schema is required-only; the relaxation defaults to `None` so every existing E5 test stays green)**, a new `tests/_fakes/evaluator.py` Evaluator-fake module + a `_fake_evaluator` factory append to `tests/conftest.py`, and ~12 new test files. It does **NOT** modify any E5 file (`app/services/{evaluator,audit,disposition,patcher,cache,...}.py`, `app/api/{labels,healthz,raw}.py`, `app/deps.py`, `app/vision/quality.py`, the `expected_values` field on `app/schemas/application.py`), the entire E2/E3/E4 surface (`app/rules/*`, `app/vision/*`, `app/orchestrator/*`), or the in-progress E7 surface (whatever currently lives in `app/main.py`'s static-mount + Jinja routes if E7 has merged them, plus the entire `frontend/` tree — inspect via `git show origin/main:<path>` if you need to read a frontend file without touching the working tree).

**Locked-surface additions are deliberately additive only.** The `OverrideEntry.field_name` relaxation preserves every existing call site: callers that pass a string-typed `field_name` continue to work bit-for-bit; the default `None` covers the new whole-envelope override case. No public method signature changes; no field renames; no existing-test rewrites. The `app/main.py` registration appends are mechanical router-include lines that mirror E5's T15/T17 pattern.

**FR-906 / NFR-DET-002 deferral.** Neither applies to E6 — FR-906 is the loader-time ruleset version mismatch (E2's loader test + E8 deployment readiness, per E5 plan §FR-906 deferral), and NFR-DET-002 (cross-process determinism) is explicitly out of scope per E1 / NFR-DATA-001 (process-local state only). E6 reaffirms NFR-DATA-001/002 by adding the lifespan-teardown eviction in T7 and the eviction-canary test in T11.

**Browser-disconnect contract (AC #9).** When the SSE consumer's `EventSource` closes, FastAPI raises `ClientDisconnect` inside the SSE response generator. The handler must remove the subscriber from `_sse_bus` within 1 s; the worker must NOT observe the disconnect — it keeps producing. A reconnecting consumer re-subscribes and the bus replays from the worker's `current_index`. T6 Cycle C tests the in-bus subscriber removal; T10 integration test exercises the full HTTP-level disconnect path.

---

## File map

| Path | Created/modified by task | Responsibility |
|---|---|---|
| `app/schemas/audit.py` | T0 | Additive: `OverrideEntry.field_name: str` → `str \| None = None`. Default-None preserves all existing call sites; whole-envelope override now expressible per L1 §2.6. |
| `app/batch/__init__.py` | T1 | Package marker. |
| `app/batch/state.py` | T1 | `InFlightBatch` — in-memory mutable companion to the frozen `BatchInFlightState`. Owns the per-batch `asyncio.Queue`, SSE subscriber set, `recent_dispositions: deque`, `calls: deque[CallRecord]`, per-item `results: dict[str, DispositionEnvelope]`, and `current_index`. Provides `snapshot() -> BatchInFlightState` for the `GET /batches/{batch_id}` response. |
| `app/batch/queue.py` | T2 | `BoundedQueue[BatchItem]` — thin typed wrapper around `asyncio.Queue(maxsize=k+1)`. Single structural enforcement of pull-based demand (FR-403). |
| `app/batch/anomaly.py` | T3 | `AnomalyDetector` — sliding window of length N=10, M=5 default; `observe(code) -> AnomalyAdvisory \| None`; `dismiss()` resets the window. Constructor accepts overrides for testability. |
| `app/api/_sse_bus.py` | T4 | `SSEBus` — per-batch async event bus. `subscribe() -> asyncio.Queue`, `unsubscribe(q)`, `broadcast(event)`, plus an async iterator helper for `sse_starlette.EventSourceResponse`. |
| `tests/_fakes/evaluator.py` | T5 | `FakeEvaluator(Evaluator)` — same `async def evaluate(application, label) -> DispositionEnvelope` signature; controllable per-call latency and canned envelopes; constructor takes a list of `(latency_seconds, envelope)` tuples or a generator. |
| `tests/conftest.py` | T5 (append) | Append `_fake_evaluator(...)` factory + `_stub_batch_envelope()` helper. |
| `app/batch/worker.py` | T6 (3 cycles: A skeleton, B lookahead+pull-demand, C anomaly+override-aware+completion) | `BatchWorker` — consumes from `BoundedQueue`; calls `Evaluator.evaluate()` per item; mutates `InFlightBatch.results`; emits per-label SSE events with `queue_position`; observes dispositions via `AnomalyDetector`; emits `stream-end` on completion. First-label-individual (FR-401) and override-aware-non-stopping (FR-404) are encoded as positive + negative tests. |
| `app/api/batches.py` | T7 | `POST /batches` (PRD §6.3 envelope → 202 + `batch_id`); `GET /batches/{batch_id}/stream` (SSE via `sse-starlette`); `GET /batches/{batch_id}` (snapshot). |
| `app/main.py` | T7 (additive register) + T8 (additive append) | T7 appends `batches.router` registration + a single lifespan-teardown call (`app.state.batches.clear()` for NFR-DATA-001/002). T8 appends `overrides.router` registration. |
| `app/api/overrides.py` | T8 | `POST /labels/{evaluation_id}/overrides` — validates `reason_code` against loaded `rules/reason_codes.yaml` registry; mutates `BatchItem.result.audit_trail.overrides`; surfaces over SSE. |
| `tests/test_override_entry_field_name_optional.py` | T0 | OverrideEntry round-trips with `field_name=None`, defaults preserved, backwards-compatible string still works. |
| `tests/test_in_flight_batch.py` | T1 | InFlightBatch construction; `recent_dispositions`/`calls`/`results` accessors; `snapshot()` returns frozen `BatchInFlightState`. |
| `tests/test_bounded_queue.py` | T2 | `BoundedQueue` saturates at `maxsize=k+1`; producer blocks; `get()` releases; FIFO order preserved. |
| `tests/test_anomaly_detector.py` | T3 | M-of-N=5-of-10 fires advisory; mixed reason codes do not fire; dismiss resets window; constructor overrides. |
| `tests/test_sse_bus.py` | T4 | `SSEBus.subscribe`/`unsubscribe`/`broadcast` semantics; multiple subscribers each receive each broadcast; unsubscribed queue does not. |
| `tests/test_fake_evaluator.py` | T5 | FakeEvaluator emits canned envelopes in order; per-call latency observed under `asyncio.wait_for`; depleting the queue raises a clear error. |
| `tests/test_batch_worker_skeleton.py` | T6 Cycle A | Single-item batch: worker consumes, calls fake evaluator, broadcasts per-label event, completes with stream-end. |
| `tests/test_batch_worker_lookahead.py` | T6 Cycle B | k=3 lookahead: items N+1, N+2 reach `processing` while N is `presented`; bounded queue saturates at `k+1=4` when consumer holds. |
| `tests/test_batch_worker_anomaly_override.py` | T6 Cycle C | 5-of-10 same-reason advisory fires; advisory dismissable; mid-batch override mutates result + emits SSE event without stopping worker; `stream-end` event fires once after the last per-label event. |
| `tests/test_batch_endpoint_post.py` | T7 | `POST /batches` returns 202 + `batch_id`; rejects malformed envelope (400); spawns worker; `GET /batches/{batch_id}` returns snapshot. |
| `tests/test_batch_endpoint_sse.py` | T7 | `GET /batches/{batch_id}/stream` emits 50 + N + 1 events for a 50-item batch; `queue_position` increments; `stream-end` fires last; client disconnect prunes subscriber within 1 s. |
| `tests/test_override_endpoint.py` | T8 | Happy path: override is recorded; rejects unknown reason code (verbatim equality against YAML registry); rejects override on non-existent `evaluation_id`; rejects override on non-existent `batch_id` cross-reference; records all FR-801 fields. |
| `tests/test_override_audit_trail.py` | T8 | OverrideEntry contents: `field_name`/`original_disposition`/`applied_disposition`/`reason_code`/`justification_text`/`reviewer_id`/`timestamp` all present and correct; whole-envelope override (`field_name=None`) round-trips. |
| `tests/test_batch_first_label_perf.py` | T9 | AC-FR-401: 50-item batch with `0.3s`-per-call FakeEvaluator → P50 ≤ 2.7 s, P99 ≤ 5.0 s for first-label-individual measured by absolute time-to-first SSE event. |
| `tests/test_batch_integration_smoke.py` | T10 | L1 §5 canary: 5-item batch with 0.05s fake latency, real `EventSourceResponse`, drains events, asserts 5 per-label + stream-end + (no advisories), connection closes. Override-mid-batch end-to-end (POST + SSE event). |
| `tests/test_batch_eviction.py` | T11 | NFR-DATA-001/002 + AC #11: lifespan teardown evicts `app.state.batches`. |
| `tests/test_lookahead_k_env_override.py` | T12 | AC #10: `LOOKAHEAD_K=2` reduces lookahead to 2; `LOOKAHEAD_K=4` increases to 4; no other behavior change. Verified by state-machine inspection (reuses T6 Cycle B harness). |

---

## Conventions used in this plan

- **Frozen Pydantic.** `BatchInFlightState`, `BatchItem`, `OverrideEntry` retain `model_config = ConfigDict(extra="forbid", frozen=True)` (E1 invariant). The mutable companions (`InFlightBatch`, `AnomalyDetector` window, `SSEBus` subscribers) are NOT frozen Pydantic — they are plain `@dataclass` (or hand-rolled classes) so fields can be reassigned safely under asyncio concurrency. Every mutation that crosses the wire boundary returns a NEW frozen Pydantic instance via `model_copy(update=...)`.
- **Async signature.** `BatchWorker.run`, the API endpoint handlers, the SSE bus methods, and the worker's `await queue.{put,get}()` are all `async def`. `AnomalyDetector.observe` and `_sse_bus.SSEBus.broadcast` are sync (no I/O) — they queue events for the SSE response loop to drain.
- **DI.** `BatchWorker.__init__` takes the four dependencies + the `InFlightBatch` companion explicitly: `(in_flight: InFlightBatch, evaluator: Evaluator, anomaly: AnomalyDetector, bus: SSEBus, lookahead_k: int = 3)`. Web layer constructs via FastAPI `Depends` factories that mirror E5's pattern (no `Settings()` reads inside the worker).
- **`app.state.batches` access.** The dict lives at `app.state.batches: dict[str, InFlightBatch]` and is created in the FastAPI lifespan startup hook (T7 modifies `app/main.py` to add the `app.state.batches = {}` line + the teardown clear). Endpoint handlers read/write via `request.app.state.batches`; tests construct via `app.state.batches[batch_id] = InFlightBatch(...)` directly when wiring the in-process app under `httpx.AsyncClient`.
- **Reviewer identifier.** `reviewer_id = "session-" + uuid.uuid4().hex[:12]` is generated per-override on the server side (no client trust). The L1 spec calls this "session-scoped — for prototype, a placeholder" (L1 §2.6); E6 implements that as the canonical string format. Production trajectory replaces with a real identity claim (OQ-PRD-1 / OQ-ARCH-3); MVP carries the convention.
- **Reason-code validation pattern.** The override endpoint loads `rules/reason_codes.yaml` lazily on first request (cached for the process) into a frozenset of accepted codes. The lazy-init avoids a module-import side effect that would fail opaquely if any test imports the module from a non-repo-root cwd. Validation is verbatim-equality (`code in _accepted_reason_codes()`) — no substring fallback, no fuzzy match. Mirrors E5 T18-UNBLOCK's lesson: the chokepoint must actively forward what upstream emits, not implicitly accept anything. Missing registry file fails LOUDLY (FileNotFoundError) on first request rather than silently rejecting all requests with 400.
- **SSE event shape.** Each SSE event is a dict with `event` (string label) and `data` (JSON-serialized payload). Three event types: `label-result` (per-label `DispositionEnvelope` dict + `queue_position` + `batch_id`), `anomaly-advisory` (`{"reason_code": str, "count": int, "window": int}`), `stream-end` (`{"batch_id": str, "total_count": int}`). The `sse_starlette.EventSourceResponse` formats each as `event: <label>\ndata: <json>\n\n` over the wire.
- **`queue_position` semantics.** `queue_position` is the 0-indexed position in the original submission order — it equals `BatchItem`'s position in `BatchInFlightState.items`. Not the order of SSE delivery (which is also submission order, since the worker processes serially behind a `BoundedQueue` of `maxsize=k+1`).
- **First-label-individual** (FR-401, T6 Cycle A). The worker's intake fills the queue eagerly up to `lookahead_k=3` items, but **does not wait** for those puts to complete before yielding to processing. The first `await queue.get()` returns item 0 the moment item 0 is enqueued; the producer's `await queue.put(item_1)` runs concurrently. Concretely: `asyncio.create_task(producer())` runs the producer in the background; the worker's main loop awaits `queue.get()` directly. Item 0's evaluation latency = evaluator latency + epsilon. Test asserts absolute time-to-first SSE event under NFR-PERF-001.
- **Mid-batch override does not stop the worker** (FR-404, T6 Cycle C). The override endpoint mutates the per-item `result.audit_trail.overrides` tuple via `model_copy(update={"audit_trail": result.audit_trail.model_copy(update={"overrides": (..., new_entry)})})`, broadcasts an `override-applied` SSE event, and returns. The worker's loop never inspects `overrides` — it consumes the queue until empty. Encoded as a positive test (worker emits all expected events after the override) AND a negative test (no extra `await asyncio.sleep` or polling on `overrides`).
- **Anomaly detector reset.** The reset-on-dismissal contract (L1 §2.4) is implemented as `AnomalyDetector.dismiss(advisory_id: str) -> None`, where `advisory_id` is the UUID4 the detector emits with each advisory. `dismiss()` clears the window only if `advisory_id` matches the currently-outstanding advisory (idempotent against double-dismissal; rejects stale dismissals from stale UI tabs). The override endpoint does NOT call dismiss — only the explicit dismiss endpoint (or, in tests, the detector directly).
- **Inference-dep ban.** No `app/batch/` or `app/api/_sse_bus.py` file imports `openai`, `anthropic`, `vllm`, or `xgrammar`. The orchestrator-isolation grep (E4-T16) covers `app/`; E6 inherits.
- **Helpers imported at module top** by `worker.py`. The worker's body delegates to them; tests can substitute via DI by patching the module-level imports if needed (but the cleaner path is to test helpers directly — that's why they're separate modules).

### `_fake_evaluator()` — canonical test Evaluator factory

All E6 tests construct fake evaluators via this helper to keep recipes synchronized with the E5 `Evaluator.evaluate(application, label) -> DispositionEnvelope` signature. The factory is appended to `tests/conftest.py` by T5.

```python
# tests/conftest.py (T5 append)
import asyncio
from collections.abc import Iterable

from app.schemas.application import Application
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope


class _FakeEvaluator:
    """Minimal protocol-compatible double for `Evaluator`. Carries a sequence of
    (latency_seconds, envelope) tuples consumed in submission order.

    Exists only in tests/. Production code never imports this."""

    def __init__(self, plan: Iterable[tuple[float, DispositionEnvelope]]) -> None:
        self._plan = list(plan)
        self._calls = 0

    async def evaluate(self, application: Application, label: Label) -> DispositionEnvelope:
        if self._calls >= len(self._plan):
            raise AssertionError(
                f"FakeEvaluator depleted after {self._calls} calls "
                f"(plan length {len(self._plan)})"
            )
        latency_s, envelope = self._plan[self._calls]
        self._calls += 1
        if latency_s > 0:
            await asyncio.sleep(latency_s)
        return envelope


def _fake_evaluator(
    plan: Iterable[tuple[float, DispositionEnvelope]] | None = None,
    *,
    n_items: int = 1,
    latency_s: float = 0.0,
    envelope_factory=None,
) -> _FakeEvaluator:
    """Build a `_FakeEvaluator`. If `plan` is None, repeats `(latency_s, envelope_factory(i))`
    for `n_items` invocations."""
    if plan is not None:
        return _FakeEvaluator(plan)
    factory = envelope_factory or _stub_disposition_envelope
    return _FakeEvaluator((latency_s, factory(i)) for i in range(n_items))


def _stub_disposition_envelope(idx: int = 0, *, disposition: str = "pass") -> DispositionEnvelope:
    """Minimal `DispositionEnvelope` for batch tests. Assembles the smallest
    schema-conforming instance — no rule traces, no fields, no overrides.

    Audit + Metrics are constructed inline because `extra='forbid'` rejects
    partial dicts."""
    from datetime import datetime, timezone

    from app.schemas.audit import AuditRecord
    from app.schemas.metrics import Metrics
    from app.schemas.wire.disposition import ConfidenceBand

    now = datetime.now(timezone.utc)
    return DispositionEnvelope(
        evaluation_id=f"EV-{idx:04d}",
        label_ref=f"lbl-{idx:04d}",
        disposition=disposition,
        disposition_confidence=ConfidenceBand(band="high", numeric=0.95),
        fields=(),
        audit_trail=AuditRecord(
            evaluation_id=f"EV-{idx:04d}",
            rule_set_version="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            started_at=now,
            completed_at=now,
            per_rule_trace=(),
        ),
        metrics=Metrics(
            total_duration_ms=10,
            per_rule_durations_ms=(),
            vision_duration_ms=5,
            orchestrator_duration_ms=0,
        ),
    )
```

**Where the factory lives.** T5 (which lands in Wave 1 alongside the modules) appends `_FakeEvaluator`, `_fake_evaluator`, and `_stub_disposition_envelope` to `tests/conftest.py`. Subsequent tasks `from tests.conftest import _fake_evaluator, _stub_disposition_envelope, _stub_label`. T5's pre-flight check: if any of the three names are already defined (e.g. an earlier task slipped them in via Rule 1-3), reuse the existing definitions.

> **Pre-flight inspection note for T5.** Stub fields above match the schemas as of E5 v0.6 closure (commit `9a9a7df`): `Metrics` requires `total_duration_ms`, `per_rule_durations_ms: tuple[PerRuleDurationEntry, ...]`, `vision_duration_ms`, `orchestrator_duration_ms` (no `evaluation_id`); `AuditRecord` requires `evaluation_id`, `rule_set_version`, `input_hash`, `output_hash`, `started_at`, `completed_at`, `per_rule_trace`. Both are frozen + `extra="forbid"` — adding extras fails construction. Before writing the constructor the executor MUST grep `grep -nE "^\s*[a-z_]+:" app/schemas/metrics.py app/schemas/audit.py` to confirm — if either schema gained a new required field since E5 closure, add it to the stub with the simplest schema-conforming default (`None`, `()`, etc.) and Rule 1-3 the addition into this task's Files block.

### `BatchInFlightState` snapshot vs. `InFlightBatch` mutable companion

The frozen E1 `BatchInFlightState` (`app/schemas/batch.py`) is the on-the-wire snapshot — the shape `GET /batches/{batch_id}` returns. The mutable `InFlightBatch` (T1, `app/batch/state.py`) holds the runtime state machinery — the per-batch `asyncio.Queue`, the SSE subscriber set, the `recent_dispositions` deque, the `calls` ring buffer, and the per-label `results: dict[str, DispositionEnvelope]`. Boundary:

```
┌─────────────────────────────┐         ┌────────────────────────────┐
│  app.state.batches[batch_id]│ ──snap──▶│  BatchInFlightState (E1) │
│     = InFlightBatch (T1)    │         │     frozen, serializable │
│                             │         │     returned by GET       │
│   • asyncio.Queue           │         └────────────────────────────┘
│   • SSEBus subscribers      │
│   • recent_dispositions     │
│   • calls (ring buffer)     │
│   • results[label_id]       │
│   • current_index           │
└─────────────────────────────┘
```

`InFlightBatch.snapshot() -> BatchInFlightState` constructs a fresh frozen Pydantic instance from the mutable state. The `items` tuple is rebuilt from the per-label `results` map + the original submission order; `current_index` is read directly. Snapshot is read-only — mutating the returned `BatchInFlightState` raises `pydantic.ValidationError` (frozen).

---

## Task 0: app/schemas/audit.py — additive `OverrideEntry.field_name` Optional

**Files:**
- Modify: `app/schemas/audit.py` (relax `field_name: str` → `field_name: str | None = None`)
- Test: `tests/test_override_entry_field_name_optional.py` (new)

Wave 0 root. No deps. Eliminates the Wave-ordering risk that T8 (Wave 4 override endpoint) cannot record whole-envelope overrides because the existing E1 schema requires `field_name` to be a non-None string. Mirror of E5's T0c pattern (additive optional field on a previously-locked schema).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_override_entry_field_name_optional.py
"""OverrideEntry.field_name accepts None per L1 §2.6 (`field_name | null`)."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.audit import OverrideEntry


def _now() -> datetime:
    return datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc)


def test_override_entry_accepts_none_field_name_for_whole_envelope_override():
    entry = OverrideEntry(
        field_name=None,
        original_disposition="needs_review",
        applied_disposition="pass",
        reason_code="BRAND.NAME.NEEDS_REVIEW",
        justification_text="Reviewed and approved.",
        reviewer_id="session-test1234",
        timestamp=_now(),
    )
    assert entry.field_name is None


def test_override_entry_field_name_default_is_none_when_omitted():
    entry = OverrideEntry(
        original_disposition="needs_review",
        applied_disposition="pass",
        reason_code="BRAND.NAME.NEEDS_REVIEW",
        reviewer_id="session-test1234",
        timestamp=_now(),
    )
    assert entry.field_name is None
    assert entry.justification_text is None


def test_override_entry_still_accepts_string_field_name_backwards_compat():
    """Pre-E6 callers pass a string. The relaxation must not break them."""
    entry = OverrideEntry(
        field_name="brand_name",
        original_disposition="fail",
        applied_disposition="needs_review",
        reason_code="BRAND.NAME.MISMATCH",
        justification_text="Borderline — flag for human re-review.",
        reviewer_id="session-test1234",
        timestamp=_now(),
    )
    assert entry.field_name == "brand_name"


def test_override_entry_rejects_non_string_non_none_field_name():
    """Type discipline preserved — only str | None accepted."""
    with pytest.raises(ValidationError):
        OverrideEntry(
            field_name=42,  # type: ignore[arg-type]
            original_disposition="pass",
            applied_disposition="pass",
            reason_code="BRAND.NAME.NEEDS_REVIEW",
            reviewer_id="session-test1234",
            timestamp=_now(),
        )
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/test_override_entry_field_name_optional.py -v` → ValidationError "Input should be a valid string" (or similar) on `field_name=None`.

- [ ] **Step 3: Implement (relax the field type)**

Edit `app/schemas/audit.py` — change the `field_name` declaration on `OverrideEntry`:

```python
# app/schemas/audit.py — diff context
class OverrideEntry(BaseModel):
    """Reviewer override recorded in the audit trail (FR-801)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: str | None = None  # was: field_name: str
    original_disposition: Literal["pass", "fail", "needs_review"]
    applied_disposition: Literal["pass", "fail", "needs_review"]
    reason_code: str
    justification_text: str | None = None
    reviewer_id: str
    timestamp: datetime
```

The single-line relaxation (`str` → `str | None = None`) is the entire change. No imports added.

- [ ] **Step 4: Run focused → GREEN (4 passed)**

`uv run pytest tests/test_override_entry_field_name_optional.py -v` → 4 passed.

- [ ] **Step 5: Run full suite to confirm no regression**

`uv run pytest -q` → expect prior count + 4 (e.g. 482 + 4 → 486 passed; xfail count unchanged at 3). If any test fails, it's a Rule 1-3 regression — investigate. The relaxation should not affect any existing test because every existing `OverrideEntry(...)` call passes a string-typed `field_name`.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/audit.py tests/test_override_entry_field_name_optional.py
git commit -m "feat(e6): OverrideEntry.field_name optional (whole-envelope overrides per L1 §2.6)"
```

---

## Task 1: app/batch/state.py — InFlightBatch in-memory companion

**Files:**
- Create: `app/batch/__init__.py` (empty package marker)
- Create: `app/batch/state.py`
- Test: `tests/test_in_flight_batch.py`

Wave 1 root. No deps. The mutable companion to the frozen `BatchInFlightState` — owns every mutable accumulator the batch substrate needs.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_in_flight_batch.py
"""InFlightBatch — mutable companion to the frozen BatchInFlightState."""
from collections import deque
from datetime import datetime, timezone

import pytest

from app.batch.state import InFlightBatch
from app.schemas.batch import BatchInFlightState, BatchItem, ItemState


def _stub_item(label_id: str, *, position: int = 0) -> BatchItem:
    return BatchItem(
        label_id=label_id,
        application_ref=f"app-{position:04d}",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 5, 4, 12, 0, position, tzinfo=timezone.utc),
    )


def test_in_flight_batch_constructs_with_items_and_lookahead():
    items = (_stub_item("lbl-0", position=0), _stub_item("lbl-1", position=1))
    in_flight = InFlightBatch(
        batch_id="B-001",
        agent_id="agent-mvp",
        items=items,
        lookahead_k=3,
    )
    assert in_flight.batch_id == "B-001"
    assert in_flight.agent_id == "agent-mvp"
    assert in_flight.items == items
    assert in_flight.current_index == 0
    assert in_flight.lookahead_k == 3
    assert in_flight.results == {}
    assert isinstance(in_flight.recent_dispositions, deque)
    assert in_flight.recent_dispositions.maxlen == 10
    assert isinstance(in_flight.calls, deque)
    assert in_flight.calls.maxlen == 200


def test_in_flight_batch_queue_is_bounded_by_lookahead_plus_one():
    items = tuple(_stub_item(f"lbl-{i}", position=i) for i in range(5))
    in_flight = InFlightBatch(batch_id="B-002", agent_id="a", items=items, lookahead_k=2)
    # maxsize = lookahead_k + 1 = 3
    assert in_flight.queue.maxsize == 3


def test_in_flight_batch_record_result_updates_results_and_advances_index():
    from tests.conftest import _stub_disposition_envelope

    items = (_stub_item("lbl-0", position=0), _stub_item("lbl-1", position=1))
    in_flight = InFlightBatch(batch_id="B-003", agent_id="a", items=items, lookahead_k=3)

    env = _stub_disposition_envelope(0)
    in_flight.record_result("lbl-0", env)

    assert in_flight.results == {"lbl-0": env}
    # current_index advances when a result lands at the cursor position
    assert in_flight.current_index == 1


def test_in_flight_batch_snapshot_returns_frozen_pydantic_state():
    items = (_stub_item("lbl-0", position=0),)
    in_flight = InFlightBatch(batch_id="B-004", agent_id="a", items=items, lookahead_k=3)

    snap = in_flight.snapshot()
    assert isinstance(snap, BatchInFlightState)
    assert snap.batch_id == "B-004"
    assert snap.agent_id == "a"
    assert snap.current_index == 0
    assert snap.lookahead_k == 3
    # Frozen — mutating raises
    with pytest.raises(Exception):  # pydantic.ValidationError
        snap.batch_id = "X"  # type: ignore[misc]


def test_in_flight_batch_does_not_carry_subscriber_state():
    """SSE subscribers live on the per-batch SSEBus stored in
    ``app.state.buses[batch_id]``, not on InFlightBatch. This test pins the
    boundary so a future drift back into the dataclass fails loudly."""
    items = (_stub_item("lbl-0", position=0),)
    in_flight = InFlightBatch(batch_id="B-005", agent_id="a", items=items, lookahead_k=3)
    assert not hasattr(in_flight, "subscribers")
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/test_in_flight_batch.py -v` → ModuleNotFoundError on `app.batch.state`.

- [ ] **Step 3: Implement**

```python
# app/batch/__init__.py
"""Batch processor substrate — InFlightBatch, BoundedQueue, AnomalyDetector,
BatchWorker. Source: ARCH §4.2.7 + §6.7."""
```

```python
# app/batch/state.py
"""In-memory mutable companion to the frozen ``BatchInFlightState`` (E1).

Owns the per-batch state machinery that does not belong inside frozen Pydantic:
the per-batch ``asyncio.Queue`` (intake → worker), the SSE subscriber set, the
``recent_dispositions`` sliding window, the ``calls`` ring buffer, the per-label
``results`` map, and the ``current_index`` cursor.

Lives in ``app.state.batches: dict[str, InFlightBatch]`` — process-local;
NFR-DATA-001/002 (no persistence). Lifespan teardown evicts.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from app.batch.queue import BoundedQueue
from app.schemas.batch import BatchInFlightState, BatchItem
from app.schemas.calls import CallRecord
from app.schemas.wire.disposition import DispositionEnvelope


@dataclass
class InFlightBatch:
    """Mutable per-batch state. Owned by the call frame of the worker and
    surfaced via ``app.state.batches``.

    SSE subscribers are NOT tracked here — they live on the per-batch
    ``SSEBus`` (T4), which is stored separately in ``app.state.buses[batch_id]``
    so the substitutability seam (BoundedQueue + SSEBus) stays uncoupled from
    in-flight per-batch state."""

    batch_id: str
    agent_id: str
    items: tuple[BatchItem, ...]
    lookahead_k: int = 3
    current_index: int = 0
    results: dict[str, DispositionEnvelope] = field(default_factory=dict)
    recent_dispositions: deque = field(
        default_factory=lambda: deque(maxlen=10)
    )
    calls: deque = field(default_factory=lambda: deque(maxlen=200))
    queue: "BoundedQueue[BatchItem]" = field(init=False)

    def __post_init__(self) -> None:
        # maxsize = k+1 (in BoundedQueue) is the structural enforcement of
        # pull-based demand (FR-403) — the producer's `await queue.put(item)`
        # blocks when the consumer holds. Wiring through BoundedQueue (T2)
        # preserves the substitutability seam called out in L1 §2.3 / ARCH
        # §4.2.7 (future swap to Kafka consumer-group / RabbitMQ prefetch=1).
        self.queue = BoundedQueue(lookahead_k=self.lookahead_k)

    def record_result(self, label_id: str, envelope: DispositionEnvelope) -> None:
        """Record a per-label result. Advances ``current_index`` if the result
        lands at the cursor position (so the next reviewer-pull starts there)."""
        self.results[label_id] = envelope
        # Advance cursor while the next item has a result
        while self.current_index < len(self.items):
            cur = self.items[self.current_index]
            if cur.label_id in self.results:
                self.current_index += 1
            else:
                break

    def snapshot(self) -> BatchInFlightState:
        """Build a frozen serializable snapshot for ``GET /batches/{batch_id}``.

        Per-item ``state`` and ``result`` are reconstructed from the runtime
        state — the original ``items`` tuple carries the queued state at
        submission time."""
        rebuilt: list[BatchItem] = []
        for idx, item in enumerate(self.items):
            envelope = self.results.get(item.label_id)
            new_state = item.state
            new_result: dict | None = None
            if envelope is not None:
                # The item completed evaluation. Mark it as `ready` (delivered
                # to the consumer when the SSE event was emitted; transitions
                # to `presented`/`reviewed`/`disposed` are reviewer-driven and
                # surfaced as state transitions in later iterations).
                from app.schemas.batch import ItemState

                new_state = ItemState.READY
                new_result = envelope.model_dump(mode="json")
            rebuilt.append(item.model_copy(update={"state": new_state, "result": new_result}))
        return BatchInFlightState(
            batch_id=self.batch_id,
            agent_id=self.agent_id,
            items=tuple(rebuilt),
            current_index=self.current_index,
            lookahead_k=self.lookahead_k,
        )
```

- [ ] **Step 4: Run focused → GREEN (5 passed)**

`uv run pytest tests/test_in_flight_batch.py -v` → 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/batch/__init__.py app/batch/state.py tests/test_in_flight_batch.py
git commit -m "feat(e6): InFlightBatch — mutable companion to frozen BatchInFlightState"
```

---

## Task 2: app/batch/queue.py — BoundedQueue

**Files:**
- Create: `app/batch/queue.py`
- Test: `tests/test_bounded_queue.py`

Wave 1 root. No deps. Thin typed wrapper around `asyncio.Queue(maxsize=k+1)`. Single structural enforcement of pull-based demand (FR-403).

> **Why a wrapper instead of bare `asyncio.Queue`?** The wrapper adds: (1) a typed signature on `put`/`get` (the IDE catches misuse where someone `put`s a non-`BatchItem`); (2) a `saturated` property for tests to assert FR-403 deterministically without reading `qsize() == maxsize`; (3) a single import-shape that the worker depends on, so a future swap to a different bounded primitive is a one-file change.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bounded_queue.py
"""BoundedQueue — typed wrapper around asyncio.Queue(maxsize=k+1).
FR-403: producer blocks when consumer holds (saturation at k+1)."""
import asyncio
from datetime import datetime, timezone

import pytest

from app.batch.queue import BoundedQueue
from app.schemas.batch import BatchItem, ItemState


def _stub(idx: int) -> BatchItem:
    return BatchItem(
        label_id=f"lbl-{idx}",
        application_ref=f"app-{idx:04d}",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 5, 4, 12, 0, idx, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_bounded_queue_constructs_with_lookahead_plus_one_maxsize():
    q = BoundedQueue[BatchItem](lookahead_k=3)
    assert q.maxsize == 4
    assert q.qsize() == 0
    assert q.saturated is False


@pytest.mark.asyncio
async def test_bounded_queue_put_get_preserves_fifo_order():
    q = BoundedQueue[BatchItem](lookahead_k=3)
    for i in range(3):
        await q.put(_stub(i))
    out = [await q.get() for _ in range(3)]
    assert [it.label_id for it in out] == ["lbl-0", "lbl-1", "lbl-2"]


@pytest.mark.asyncio
async def test_bounded_queue_saturates_at_maxsize_and_blocks_producer():
    q = BoundedQueue[BatchItem](lookahead_k=2)  # maxsize = 3
    # Fill to capacity
    for i in range(3):
        await q.put(_stub(i))
    assert q.qsize() == 3
    assert q.saturated is True

    # Fourth put blocks — wrap in wait_for(timeout=0.05) and expect TimeoutError
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.put(_stub(3)), timeout=0.05)


@pytest.mark.asyncio
async def test_bounded_queue_get_releases_blocked_producer():
    q = BoundedQueue[BatchItem](lookahead_k=1)  # maxsize = 2
    await q.put(_stub(0))
    await q.put(_stub(1))
    assert q.saturated is True

    # Producer task that will block on a 3rd put
    producer_done = asyncio.Event()

    async def producer() -> None:
        await q.put(_stub(2))
        producer_done.set()

    producer_task = asyncio.create_task(producer())
    await asyncio.sleep(0.02)
    assert producer_done.is_set() is False, "producer should be blocked"

    # Drain one — producer unblocks
    await q.get()
    await asyncio.wait_for(producer_done.wait(), timeout=0.5)
    producer_task.cancel()
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/test_bounded_queue.py -v` → ModuleNotFoundError on `app.batch.queue`.

- [ ] **Step 3: Implement**

```python
# app/batch/queue.py
"""Bounded queue — typed wrapper around ``asyncio.Queue(maxsize=k+1)``.

The single structural enforcement of pull-based demand (FR-403). The wrapper
exists so (1) the worker depends on a stable import shape, (2) tests can
assert ``saturated`` deterministically, and (3) a future swap to a different
bounded primitive is a one-file change. Source: ARCH §4.2.7.
"""
from __future__ import annotations

import asyncio
from typing import Generic, TypeVar

T = TypeVar("T")


class BoundedQueue(Generic[T]):
    """Thin typed wrapper around ``asyncio.Queue``."""

    def __init__(self, *, lookahead_k: int) -> None:
        if lookahead_k < 1:
            raise ValueError(f"lookahead_k must be >= 1, got {lookahead_k}")
        self._inner: asyncio.Queue[T] = asyncio.Queue(maxsize=lookahead_k + 1)
        self._lookahead_k = lookahead_k

    @property
    def maxsize(self) -> int:
        return self._inner.maxsize

    @property
    def saturated(self) -> bool:
        return self._inner.full()

    def qsize(self) -> int:
        return self._inner.qsize()

    async def put(self, item: T) -> None:
        await self._inner.put(item)

    async def get(self) -> T:
        return await self._inner.get()
```

- [ ] **Step 4: Run focused → GREEN (4 passed)**

`uv run pytest tests/test_bounded_queue.py -v` → 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/batch/queue.py tests/test_bounded_queue.py
git commit -m "feat(e6): BoundedQueue — typed maxsize=k+1 wrapper for FR-403"
```

---

## Task 3: app/batch/anomaly.py — AnomalyDetector

**Files:**
- Create: `app/batch/anomaly.py`
- Test: `tests/test_anomaly_detector.py`

Wave 1 root. No deps. Sliding window M-of-N detector (FR-405). Default M=5, N=10. Constructor accepts overrides for testability.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_anomaly_detector.py
"""AnomalyDetector — M-of-N sliding window. FR-405."""
import pytest

from app.batch.anomaly import AnomalyAdvisory, AnomalyDetector


def test_detector_constructs_with_default_thresholds():
    det = AnomalyDetector()
    assert det.window_n == 10
    assert det.threshold_m == 5


def test_detector_does_not_fire_below_threshold():
    det = AnomalyDetector(window_n=10, threshold_m=5)
    for _ in range(4):
        adv = det.observe("BRAND.NAME.MISMATCH")
        assert adv is None
    # 4 same-code observations < threshold 5 — no advisory


def test_detector_fires_when_m_of_last_n_share_a_reason_code():
    det = AnomalyDetector(window_n=10, threshold_m=5)
    advisories: list[AnomalyAdvisory] = []
    # 5 same-code observations in a row — 5 of the last 5 share, advisory fires
    for _ in range(5):
        adv = det.observe("BRAND.NAME.MISMATCH")
        if adv is not None:
            advisories.append(adv)
    assert len(advisories) == 1
    assert advisories[0].reason_code == "BRAND.NAME.MISMATCH"
    assert advisories[0].count == 5
    assert advisories[0].window == 10
    assert advisories[0].advisory_id  # uuid4 string


def test_detector_does_not_fire_when_no_code_reaches_threshold():
    """Heterogeneous batch: no single code accumulates M=5 in any 10-obs window.
    With 4 As + 4 Bs + 2 Cs, each code peaks at count 4 < threshold 5 — detector
    must stay silent. Confirms the threshold is per-code, not per-window-fill."""
    det = AnomalyDetector(window_n=10, threshold_m=5)
    codes = ["A", "B", "C", "A", "B", "A", "B", "C", "A", "B"]  # 4A 4B 2C
    advisories = []
    for c in codes:
        adv = det.observe(c)
        if adv is not None:
            advisories.append(adv)
    assert advisories == []


def test_detector_fires_on_first_code_that_reaches_threshold_after_window_fills():
    det = AnomalyDetector(window_n=10, threshold_m=5)
    # 5 mismatches followed by 5 unknowns. Window state at t=10:
    #   ["A"]*5 + ["B"]*5 — both at count 5. Advisory fires at observation 5
    #   (when "A" first reaches threshold), not at observation 10.
    advisories = []
    for c in ["A"] * 5 + ["B"] * 5:
        adv = det.observe(c)
        if adv is not None:
            advisories.append(adv)
    assert len(advisories) == 1
    assert advisories[0].reason_code == "A"


def test_detector_fires_at_most_once_per_window_filling():
    det = AnomalyDetector(window_n=10, threshold_m=5)
    # Once we fire on "A" at observation 5, observations 6-10 are still "A"
    # — but the advisory has already fired. We should NOT re-fire.
    advisories = []
    for _ in range(10):
        adv = det.observe("A")
        if adv is not None:
            advisories.append(adv)
    assert len(advisories) == 1


def test_detector_dismiss_resets_window_and_re_arms():
    det = AnomalyDetector(window_n=10, threshold_m=5)
    advisories = []
    for _ in range(5):
        adv = det.observe("A")
        if adv is not None:
            advisories.append(adv)
    assert len(advisories) == 1
    advisory_id = advisories[0].advisory_id

    # Dismiss — window clears, detector re-arms
    det.dismiss(advisory_id)

    advisories2 = []
    for _ in range(4):
        adv = det.observe("A")
        if adv is not None:
            advisories2.append(adv)
    assert advisories2 == []  # only 4 < threshold 5 after reset

    adv = det.observe("A")
    advisories2.append(adv) if adv else None
    assert len(advisories2) == 1  # 5th fires again


def test_detector_dismiss_with_wrong_advisory_id_is_idempotent_noop():
    det = AnomalyDetector(window_n=10, threshold_m=5)
    for _ in range(5):
        det.observe("A")
    # Dismiss with bogus advisory id — must be noop
    det.dismiss("not-a-real-advisory-id")

    # Window should still be in fired state — observing more "A"s does NOT
    # produce a fresh advisory because the outstanding one was not dismissed.
    adv = det.observe("A")
    assert adv is None


def test_detector_observes_none_reason_code_does_not_count():
    det = AnomalyDetector(window_n=10, threshold_m=5)
    # `pass` and `not_applicable` outcomes carry None as the reason_code in
    # the recent_dispositions deque. None must not count toward any threshold.
    for _ in range(5):
        adv = det.observe(None)
        assert adv is None
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/test_anomaly_detector.py -v` → ModuleNotFoundError on `app.batch.anomaly`.

- [ ] **Step 3: Implement**

```python
# app/batch/anomaly.py
"""Sliding-window anomaly detector — FR-405.

Default M=5, N=10. Fires an advisory when M of the last N observations share
the same reason code. The advisory carries a UUID4 ``advisory_id`` so the
dismiss endpoint can validate the dismissal corresponds to the still-outstanding
advisory (idempotent against double-dismissal; rejects stale tabs).

Source: ARCH §5.2 / L1 §2.4.
"""
from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class AnomalyAdvisory:
    """One anomaly-advisory event."""

    advisory_id: str
    reason_code: str
    count: int
    window: int


class AnomalyDetector:
    """Sliding M-of-N detector. Stateful; not thread-safe (asyncio single-threaded)."""

    def __init__(self, *, window_n: int = 10, threshold_m: int = 5) -> None:
        if threshold_m < 1 or threshold_m > window_n:
            raise ValueError(
                f"threshold_m must satisfy 1 <= m <= n; got m={threshold_m} n={window_n}"
            )
        self.window_n = window_n
        self.threshold_m = threshold_m
        self._window: deque[str | None] = deque(maxlen=window_n)
        self._outstanding_advisory_id: str | None = None

    def observe(self, reason_code: str | None) -> AnomalyAdvisory | None:
        """Record one observation. Return an advisory iff the threshold is
        crossed AND no advisory is currently outstanding (dismiss-required-first)."""
        self._window.append(reason_code)
        if self._outstanding_advisory_id is not None:
            return None  # already fired — wait for dismiss
        if reason_code is None:
            return None  # None doesn't count toward any threshold

        # Count occurrences of reason_code in the window
        count = sum(1 for c in self._window if c == reason_code)
        if count >= self.threshold_m:
            advisory = AnomalyAdvisory(
                advisory_id=str(uuid.uuid4()),
                reason_code=reason_code,
                count=count,
                window=self.window_n,
            )
            self._outstanding_advisory_id = advisory.advisory_id
            return advisory
        return None

    def dismiss(self, advisory_id: str) -> None:
        """Clear the window iff ``advisory_id`` matches the outstanding advisory.
        Idempotent against double-dismissal and stale tabs."""
        if self._outstanding_advisory_id == advisory_id:
            self._window.clear()
            self._outstanding_advisory_id = None
```

- [ ] **Step 4: Run focused → GREEN (9 passed)**

`uv run pytest tests/test_anomaly_detector.py -v` → 9 passed.

- [ ] **Step 5: Commit**

```bash
git add app/batch/anomaly.py tests/test_anomaly_detector.py
git commit -m "feat(e6): AnomalyDetector — M-of-N sliding window with dismiss-validates-id (FR-405)"
```

---

## Task 4: app/api/_sse_bus.py — SSEBus

**Files:**
- Create: `app/api/_sse_bus.py`
- Test: `tests/test_sse_bus.py`

Wave 1 root. No deps (only stdlib + pre-existing FastAPI). Per-batch async event broker.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sse_bus.py
"""SSEBus — per-batch async event broker."""
import asyncio

import pytest

from app.api._sse_bus import SSEBus


@pytest.mark.asyncio
async def test_bus_subscribe_returns_unique_queue_per_call():
    bus = SSEBus()
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    assert q1 is not q2
    assert isinstance(q1, asyncio.Queue)
    assert isinstance(q2, asyncio.Queue)
    assert len(bus.subscribers) == 2


@pytest.mark.asyncio
async def test_bus_broadcast_pushes_to_every_subscriber():
    bus = SSEBus()
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    event = {"event": "label-result", "data": {"label_ref": "lbl-0"}}
    bus.broadcast(event)
    assert (await asyncio.wait_for(q1.get(), timeout=0.1)) == event
    assert (await asyncio.wait_for(q2.get(), timeout=0.1)) == event


@pytest.mark.asyncio
async def test_bus_unsubscribe_removes_subscriber():
    bus = SSEBus()
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    bus.unsubscribe(q1)
    assert q1 not in bus.subscribers
    assert q2 in bus.subscribers


@pytest.mark.asyncio
async def test_bus_broadcast_after_unsubscribe_does_not_push_to_dropped():
    bus = SSEBus()
    q1 = bus.subscribe()
    q2 = bus.subscribe()
    bus.unsubscribe(q1)
    bus.broadcast({"event": "x", "data": {}})
    # q1 stays empty
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q1.get(), timeout=0.05)
    # q2 receives
    assert (await asyncio.wait_for(q2.get(), timeout=0.1))["event"] == "x"


@pytest.mark.asyncio
async def test_bus_broadcast_with_no_subscribers_is_noop():
    bus = SSEBus()
    # Must not raise
    bus.broadcast({"event": "x", "data": {}})


@pytest.mark.asyncio
async def test_bus_unsubscribe_unknown_queue_is_idempotent_noop():
    bus = SSEBus()
    foreign = asyncio.Queue()
    # Must not raise
    bus.unsubscribe(foreign)


@pytest.mark.asyncio
async def test_bus_iterate_subscriber_yields_events_until_sentinel():
    """Async iterator helper for sse_starlette.EventSourceResponse."""
    bus = SSEBus()
    q = bus.subscribe()
    bus.broadcast({"event": "label-result", "data": {"i": 0}})
    bus.broadcast({"event": "stream-end", "data": {}})

    received: list[dict] = []
    async for evt in bus.iterate(q, terminator_event="stream-end"):
        received.append(evt)
    assert [e["event"] for e in received] == ["label-result", "stream-end"]
    # Subscriber pruned on terminator
    assert q not in bus.subscribers
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/test_sse_bus.py -v` → ModuleNotFoundError on `app.api._sse_bus`.

- [ ] **Step 3: Implement**

```python
# app/api/_sse_bus.py
"""Per-batch async event broker.

Each subscriber gets its own ``asyncio.Queue``; ``broadcast`` pushes the same
event dict to every subscriber. The Web layer's SSE response loop iterates the
subscriber queue and yields ``sse_starlette.EventSourceResponse``-friendly
dicts.

Connection-close detection: when the client disconnects (FastAPI raises
``ClientDisconnect`` inside the response generator), the route handler calls
``unsubscribe(q)``. The worker continues so a reconnecting consumer can resume
from ``current_index``. Source: ARCH §5.2 / T6 §Q6.6 contract.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class SSEBus:
    """Per-batch async event bus."""

    def __init__(self) -> None:
        self.subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def broadcast(self, event: dict) -> None:
        # Iterate over a copy so concurrent unsubscribe does not mutate during.
        for q in list(self.subscribers):
            q.put_nowait(event)

    async def iterate(
        self,
        q: asyncio.Queue,
        *,
        terminator_event: str | None = None,
    ) -> AsyncIterator[dict]:
        """Yield events from a subscriber queue until the terminator event is
        seen (or forever if ``terminator_event`` is None). Auto-unsubscribes on
        terminator."""
        try:
            while True:
                evt = await q.get()
                yield evt
                if terminator_event is not None and evt.get("event") == terminator_event:
                    return
        finally:
            self.unsubscribe(q)
```

- [ ] **Step 4: Run focused → GREEN (7 passed)**

`uv run pytest tests/test_sse_bus.py -v` → 7 passed.

- [ ] **Step 5: Commit**

```bash
git add app/api/_sse_bus.py tests/test_sse_bus.py
git commit -m "feat(e6): SSEBus — per-batch async event broker with auto-unsubscribe on terminator"
```

---

## Task 5: tests/_fakes/evaluator.py — FakeEvaluator + conftest helpers

**Files:**
- Create: `tests/_fakes/evaluator.py`
- Modify: `tests/conftest.py` (append `_FakeEvaluator`, `_fake_evaluator`, `_stub_disposition_envelope`)
- Test: `tests/test_fake_evaluator.py`

Wave 1 root. No deps (uses pre-existing E5 schemas only). Required by every T6+ test.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fake_evaluator.py
"""FakeEvaluator — controllable per-call latency + canned envelopes."""
import asyncio
import time

import pytest

from app.schemas.application import Application
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope
from tests._fakes.evaluator import FakeEvaluator


def _stub_app(idx: int = 0) -> Application:
    return Application(application_id=f"app-{idx:04d}", evaluation_id=f"EV-{idx:04d}")


def _stub_label(idx: int = 0) -> Label:
    from tests.conftest import _stub_label as helper
    return helper(label_id=f"lbl-{idx:04d}")


@pytest.mark.asyncio
async def test_fake_evaluator_emits_canned_envelope_in_order():
    from tests.conftest import _stub_disposition_envelope

    plan = [(0.0, _stub_disposition_envelope(0)), (0.0, _stub_disposition_envelope(1))]
    fake = FakeEvaluator(plan)

    env_0 = await fake.evaluate(_stub_app(0), _stub_label(0))
    env_1 = await fake.evaluate(_stub_app(1), _stub_label(1))

    assert env_0.evaluation_id == "EV-0000"
    assert env_1.evaluation_id == "EV-0001"


@pytest.mark.asyncio
async def test_fake_evaluator_observes_per_call_latency():
    from tests.conftest import _stub_disposition_envelope

    plan = [(0.05, _stub_disposition_envelope(0))]
    fake = FakeEvaluator(plan)

    t0 = time.perf_counter()
    await fake.evaluate(_stub_app(0), _stub_label(0))
    elapsed = time.perf_counter() - t0
    assert 0.04 <= elapsed <= 0.20, f"latency outside band: {elapsed}"


@pytest.mark.asyncio
async def test_fake_evaluator_raises_when_plan_depleted():
    from tests.conftest import _stub_disposition_envelope

    plan = [(0.0, _stub_disposition_envelope(0))]
    fake = FakeEvaluator(plan)

    await fake.evaluate(_stub_app(0), _stub_label(0))
    with pytest.raises(AssertionError, match="depleted"):
        await fake.evaluate(_stub_app(1), _stub_label(1))


@pytest.mark.asyncio
async def test_fake_evaluator_factory_repeats_envelope_for_n_items():
    from tests.conftest import _fake_evaluator

    fake = _fake_evaluator(n_items=3, latency_s=0.0)
    out = []
    for i in range(3):
        out.append(await fake.evaluate(_stub_app(i), _stub_label(i)))
    assert len(out) == 3
    assert all(isinstance(env, DispositionEnvelope) for env in out)


@pytest.mark.asyncio
async def test_stub_disposition_envelope_is_schema_conformant():
    """The stub must round-trip through Pydantic without `extra=forbid` rejection."""
    from tests.conftest import _stub_disposition_envelope

    env = _stub_disposition_envelope(0)
    # Round-trip
    dump = env.model_dump(mode="json")
    rebuilt = DispositionEnvelope.model_validate(dump)
    assert rebuilt.evaluation_id == env.evaluation_id
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/test_fake_evaluator.py -v` → ModuleNotFoundError or AttributeError on `tests._fakes.evaluator` / `tests.conftest._fake_evaluator`.

- [ ] **Step 3: Implement**

```python
# tests/_fakes/evaluator.py
"""FakeEvaluator — minimal protocol-compatible double for ``Evaluator``.

Carries a sequence of ``(latency_seconds, envelope)`` tuples consumed in
submission order. Used by every E6 worker test that needs deterministic
per-call latency and canned envelopes."""
from __future__ import annotations

import asyncio
from collections.abc import Iterable

from app.schemas.application import Application
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope


class FakeEvaluator:
    """Test double for ``app.services.evaluator.Evaluator``."""

    def __init__(self, plan: Iterable[tuple[float, DispositionEnvelope]]) -> None:
        self._plan = list(plan)
        self._calls = 0

    async def evaluate(self, application: Application, label: Label) -> DispositionEnvelope:
        if self._calls >= len(self._plan):
            raise AssertionError(
                f"FakeEvaluator depleted after {self._calls} calls "
                f"(plan length {len(self._plan)})"
            )
        latency_s, envelope = self._plan[self._calls]
        self._calls += 1
        if latency_s > 0:
            await asyncio.sleep(latency_s)
        return envelope

    @property
    def call_count(self) -> int:
        return self._calls
```

Append to `tests/conftest.py` (after the existing `_stub_label` definition):

```python
# tests/conftest.py — append below existing _stub_label
from collections.abc import Iterable

from app.schemas.wire.disposition import DispositionEnvelope


def _stub_disposition_envelope(idx: int = 0, *, disposition: str = "pass") -> DispositionEnvelope:
    """Minimal `DispositionEnvelope` for batch tests.

    Pre-flight inspection note: if `Metrics` or `AuditRecord` schemas have
    grown additional required fields since this plan was written, add them
    with the simplest schema-conforming defaults (see plan §Conventions
    `_fake_evaluator()`)."""
    from datetime import datetime, timezone

    from app.schemas.audit import AuditRecord
    from app.schemas.metrics import Metrics
    from app.schemas.wire.disposition import ConfidenceBand

    now = datetime.now(timezone.utc)
    return DispositionEnvelope(
        evaluation_id=f"EV-{idx:04d}",
        label_ref=f"lbl-{idx:04d}",
        disposition=disposition,
        disposition_confidence=ConfidenceBand(band="high", numeric=0.95),
        fields=(),
        audit_trail=AuditRecord(
            evaluation_id=f"EV-{idx:04d}",
            rule_set_version="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            started_at=now,
            completed_at=now,
            per_rule_trace=(),
        ),
        metrics=Metrics(
            total_duration_ms=10,
            per_rule_durations_ms=(),
            vision_duration_ms=5,
            orchestrator_duration_ms=0,
        ),
    )


def _fake_evaluator(
    plan: Iterable[tuple[float, DispositionEnvelope]] | None = None,
    *,
    n_items: int = 1,
    latency_s: float = 0.0,
    envelope_factory=None,
):
    """Build a FakeEvaluator. If `plan` is None, repeats `(latency_s, envelope_factory(i))`
    for `n_items` invocations."""
    from tests._fakes.evaluator import FakeEvaluator

    if plan is not None:
        return FakeEvaluator(plan)
    factory = envelope_factory or _stub_disposition_envelope
    return FakeEvaluator((latency_s, factory(i)) for i in range(n_items))
```

- [ ] **Step 4: Run focused → GREEN (5 passed)**

`uv run pytest tests/test_fake_evaluator.py -v` → 5 passed.

- [ ] **Step 5: Commit**

```bash
git add tests/_fakes/evaluator.py tests/conftest.py tests/test_fake_evaluator.py
git commit -m "test(e6): FakeEvaluator + _fake_evaluator + _stub_disposition_envelope conftest helpers"
```

---

## Task 6: app/batch/worker.py — BatchWorker (3-cycle bundle)

**Files:**
- Create: `app/batch/worker.py`
- Test (Cycle A): `tests/test_batch_worker_skeleton.py`
- Test (Cycle B): `tests/test_batch_worker_lookahead.py`
- Test (Cycle C): `tests/test_batch_worker_anomaly_override.py`

Wave 2 single. Depends on T1 (`InFlightBatch`), T2 (`BoundedQueue`), T3 (`AnomalyDetector`), T4 (`SSEBus`), T5 (`FakeEvaluator` + conftest helpers). Three cycles because the worker file is shared and each cycle adds a coherent capability.

**Worker narrative.** Each `BatchWorker.run(batch_id)` invocation runs once per batch. Two coroutines collaborate via the per-batch `InFlightBatch.queue` (`BoundedQueue[BatchItem]`):

1. **Producer task** (`_producer`): iterates `in_flight.items` in submission order, awaits `queue.put(item)` for each. Saturates at `maxsize=k+1`, blocks until consumer drains.
2. **Consumer loop** (`_consume`): repeatedly `await queue.get()`, calls `evaluator.evaluate(app, label)`, mutates `in_flight.results` via `record_result`, broadcasts a `label-result` SSE event with `queue_position`, observes the disposition's headline reason code through `anomaly.observe(reason_code)` and broadcasts `anomaly-advisory` if one fires. After processing the last item, broadcasts a `stream-end` event and returns.

**First-label-individual** (FR-401): the producer task is started concurrently with the consumer loop. Item 0's `queue.put` returns immediately (queue has capacity); the consumer's first `queue.get` returns item 0 the moment it's enqueued. Item 1's `queue.put` runs concurrently with item 0's evaluation, but the *consumer* never blocks on the producer beyond a single `queue.get`. **Test for FR-401 measures absolute time-to-first SSE event** — not throughput (T9 owns the perf canary).

**Mid-batch override** (FR-404): the override endpoint (T8) is the only mutator of `result.audit_trail.overrides`. The worker NEVER inspects overrides — its loop does not poll, sleep, or condition on overrides. The worker's continued progress past an override is encoded as a positive test (Cycle C) AND a negative test (no extra `await asyncio.sleep` or `if` on overrides in the worker source — `tests/test_batch_worker_anomaly_override.py::test_worker_does_not_inspect_overrides` greps the implementation).

**Reason-code extraction.** The worker calls `anomaly.observe(_headline_reason_code(envelope))`. `_headline_reason_code` is a pure helper at the module top of `worker.py` that picks one canonical reason-code string per envelope.

> **Why this is non-trivial.** `PerRuleTraceEntry` (E5 audit schema, `app/schemas/audit.py:15-25`) carries `rule_id`/`disposition`/`evidence_ref` — but no `reason_code`. The reason codes live on `RuleFindingWire.reason_code` inside `envelope.fields[].rule_findings[]`. For short-circuit envelopes (legibility, FR-900 series) `envelope.fields == ()` and E5 convention places the reason code in `per_rule_trace[0].rule_id` instead (per E5 plan iter-1 Warning #2 acknowledgement). The helper therefore tries the per-field path first, falls back to the short-circuit path, then returns `None`.

```python
def _headline_reason_code(envelope: DispositionEnvelope) -> str | None:
    """Pick one canonical reason-code string for anomaly observation.

    Priority:
    1. ``envelope.disposition == "pass"`` → ``None`` (no anomaly signal).
    2. First non-pass ``RuleFindingWire`` inside ``envelope.fields`` →
       ``finding.reason_code``.
    3. Short-circuit envelope (no fields, e.g. legibility / FR-900 chokepoint)
       → ``envelope.audit_trail.per_rule_trace[0].rule_id`` (E5 convention:
       short-circuit envelopes encode the reason code in ``rule_id`` because
       ``PerRuleTraceEntry`` does not carry a separate ``reason_code`` field).
    4. Otherwise ``None``.
    """
    if envelope.disposition == "pass":
        return None
    for field in envelope.fields:
        for finding in field.rule_findings:
            if finding.disposition in ("fail", "needs_review"):
                return finding.reason_code
    if envelope.audit_trail.per_rule_trace:
        return envelope.audit_trail.per_rule_trace[0].rule_id
    return None
```

Tests parametrize this — both the per-field path (real-envelope path) and the short-circuit path (legibility / chokepoint).

### Cycle A — skeleton + first-label-individual happy path

- [ ] **Step A.1: Write the failing test**

```python
# tests/test_batch_worker_skeleton.py
"""BatchWorker skeleton — single-item batch consumed end-to-end. FR-401 first-label."""
import asyncio
import time
from datetime import datetime, timezone

import pytest

from app.api._sse_bus import SSEBus
from app.batch.anomaly import AnomalyDetector
from app.batch.state import InFlightBatch
from app.batch.worker import BatchWorker
from app.schemas.batch import BatchItem, ItemState
from tests.conftest import _fake_evaluator


def _stub_item(idx: int) -> BatchItem:
    return BatchItem(
        label_id=f"lbl-{idx}",
        application_ref=f"app-{idx:04d}",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 5, 4, 12, 0, idx, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_worker_processes_single_item_and_emits_label_result_then_stream_end():
    in_flight = InFlightBatch(
        batch_id="B-001",
        agent_id="a",
        items=(_stub_item(0),),
        lookahead_k=3,
    )
    bus = SSEBus()
    sub = bus.subscribe()
    fake_eval = _fake_evaluator(n_items=1, latency_s=0.0)
    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=fake_eval,
        anomaly=AnomalyDetector(),
        bus=bus,
    )

    await worker.run()

    # Two events: label-result + stream-end
    e1 = await asyncio.wait_for(sub.get(), timeout=0.5)
    e2 = await asyncio.wait_for(sub.get(), timeout=0.5)
    assert e1["event"] == "label-result"
    assert e1["data"]["queue_position"] == 0
    assert e1["data"]["batch_id"] == "B-001"
    assert e2["event"] == "stream-end"
    assert e2["data"]["batch_id"] == "B-001"
    assert e2["data"]["total_count"] == 1


@pytest.mark.asyncio
async def test_worker_records_result_and_advances_current_index():
    in_flight = InFlightBatch(
        batch_id="B-002",
        agent_id="a",
        items=(_stub_item(0), _stub_item(1)),
        lookahead_k=3,
    )
    fake_eval = _fake_evaluator(n_items=2, latency_s=0.0)
    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=fake_eval,
        anomaly=AnomalyDetector(),
        bus=SSEBus(),
    )

    await worker.run()

    assert set(in_flight.results.keys()) == {"lbl-0", "lbl-1"}
    assert in_flight.current_index == 2  # both items completed


@pytest.mark.asyncio
async def test_worker_first_label_individual_does_not_wait_for_lookahead_window():
    """FR-401: first label of a 50-item batch returns under NFR-PERF-001 even
    when subsequent items take a long time. The worker must NOT batch the
    first item with later items."""
    items = tuple(_stub_item(i) for i in range(50))
    in_flight = InFlightBatch(
        batch_id="B-003", agent_id="a", items=items, lookahead_k=3,
    )
    bus = SSEBus()
    sub = bus.subscribe()

    # Item 0 is fast; items 1+ are slow. If the worker waited for lookahead k=3
    # to fill before responding, we'd see a delay of at least 3 * 0.5 = 1.5s
    # before item 0's event. With first-label-individual, item 0 emits in <0.1s.
    from tests.conftest import _stub_disposition_envelope
    plan = [(0.0, _stub_disposition_envelope(0))] + [
        (0.5, _stub_disposition_envelope(i)) for i in range(1, 50)
    ]
    fake_eval = _fake_evaluator(plan=plan)
    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=fake_eval,
        anomaly=AnomalyDetector(),
        bus=bus,
    )

    t0 = time.perf_counter()
    run_task = asyncio.create_task(worker.run())
    first_event = await asyncio.wait_for(sub.get(), timeout=2.0)
    elapsed = time.perf_counter() - t0
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass

    assert first_event["event"] == "label-result"
    assert first_event["data"]["queue_position"] == 0
    assert elapsed < 0.5, f"first-label took {elapsed:.3f}s — exceeds 0.5s budget"
```

- [ ] **Step A.2: Run focused → RED**

`uv run pytest tests/test_batch_worker_skeleton.py -v` → ModuleNotFoundError on `app.batch.worker`.

- [ ] **Step A.3: Implement skeleton**

```python
# app/batch/worker.py
"""Batch worker — pull-based, reactive-streams-style consumer.

Two coroutines collaborate via the per-batch ``BoundedQueue``:

1. ``_producer`` — iterates ``in_flight.items`` in submission order and awaits
   ``queue.put(item)`` for each. Saturates at ``maxsize=k+1`` and blocks until
   the consumer drains. **First-label-individual (FR-401)**: producer starts
   concurrently with the consumer; item 0's put returns immediately and the
   consumer's first get returns it without waiting for the lookahead window.
2. ``_consume`` — ``await queue.get()`` → ``evaluator.evaluate(app, label)`` →
   ``in_flight.record_result(label_id, envelope)`` → broadcast ``label-result``
   SSE event → ``anomaly.observe(headline_reason_code)`` → broadcast
   ``anomaly-advisory`` if one fires. Emits ``stream-end`` after the last item.

Mid-batch override (FR-404) is handled outside this module: the override
endpoint (T8) mutates ``in_flight.results[label_id]`` directly. The worker
never inspects ``overrides`` as a stop condition.

Source: ARCH §4.2.7 / §5.2 / L1 §2.2.
"""
from __future__ import annotations

import asyncio
import logging

from app.api._sse_bus import SSEBus
from app.batch.anomaly import AnomalyDetector
from app.batch.state import InFlightBatch
from app.schemas.application import Application
from app.schemas.batch import BatchItem
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope

_logger = logging.getLogger("app.batch.worker")


def _headline_reason_code(envelope: DispositionEnvelope) -> str | None:
    """Pick one canonical reason-code string for anomaly observation.

    See module docstring + plan §"Reason-code extraction" for the rationale:
    PerRuleTraceEntry carries no `reason_code` field; reason codes live on
    RuleFindingWire inside envelope.fields, with a short-circuit fallback to
    per_rule_trace[0].rule_id (E5 convention for legibility / FR-900
    envelopes that have no per-field findings)."""
    if envelope.disposition == "pass":
        return None
    for field in envelope.fields:
        for finding in field.rule_findings:
            if finding.disposition in ("fail", "needs_review"):
                return finding.reason_code
    if envelope.audit_trail.per_rule_trace:
        return envelope.audit_trail.per_rule_trace[0].rule_id
    return None


class BatchWorker:
    """Pull-based batch consumer."""

    def __init__(
        self,
        *,
        in_flight: InFlightBatch,
        evaluator,
        anomaly: AnomalyDetector,
        bus: SSEBus,
    ) -> None:
        self._in_flight = in_flight
        self._evaluator = evaluator
        self._anomaly = anomaly
        self._bus = bus
        # Stub `_app_lookup` — production wires from app.state.applications;
        # tests inject via attribute or rely on synthesized stubs. See note
        # on `_resolve_application` below.
        self._app_lookup: dict[str, Application] = {}

    def _resolve_application(self, item: BatchItem) -> Application:
        """Resolve the Application for a queued BatchItem.

        Cycle A skeleton stub: synthesizes a minimal `Application` from the
        `application_ref`. Cycle C upgrades to read from `app.state.applications`
        when the real submission registry exists. Tests override by populating
        `self._app_lookup` directly."""
        if item.application_ref in self._app_lookup:
            return self._app_lookup[item.application_ref]
        return Application(
            application_id=item.application_ref,
            evaluation_id=item.label_id,
        )

    def _resolve_label(self, item: BatchItem) -> Label:
        """Resolve the Label payload for a queued BatchItem.

        Cycle A skeleton stub: synthesizes a minimal `Label` from the
        `label_id`. The real payload (image_bytes etc.) lives in the submission
        registry, not in `BatchItem`. Tests override via `self._label_lookup`."""
        from tests.conftest import _stub_label  # ok in test path; production wires real registry
        return _stub_label(label_id=item.label_id)

    async def _producer(self) -> None:
        for item in self._in_flight.items:
            await self._in_flight.queue.put(item)

    async def _consume(self) -> None:
        total = len(self._in_flight.items)
        for queue_position in range(total):
            item: BatchItem = await self._in_flight.queue.get()
            application = self._resolve_application(item)
            label = self._resolve_label(item)
            envelope = await self._evaluator.evaluate(application, label)
            self._in_flight.record_result(item.label_id, envelope)

            # Per-label SSE event with queue_position
            self._bus.broadcast({
                "event": "label-result",
                "data": {
                    "batch_id": self._in_flight.batch_id,
                    "queue_position": queue_position,
                    "envelope": envelope.model_dump(mode="json"),
                },
            })

            # Anomaly observation (Cycle C will surface advisory broadcasts).
            # Bind once: the helper is pure today, but binding here pins the
            # contract that ``recent_dispositions`` and ``observe`` see the
            # same code, even if the helper later acquires side effects.
            headline_code = _headline_reason_code(envelope)
            self._in_flight.recent_dispositions.append(headline_code)
            advisory = self._anomaly.observe(headline_code)
            if advisory is not None:
                self._bus.broadcast({
                    "event": "anomaly-advisory",
                    "data": {
                        "batch_id": self._in_flight.batch_id,
                        "advisory_id": advisory.advisory_id,
                        "reason_code": advisory.reason_code,
                        "count": advisory.count,
                        "window": advisory.window,
                    },
                })

        self._bus.broadcast({
            "event": "stream-end",
            "data": {
                "batch_id": self._in_flight.batch_id,
                "total_count": total,
            },
        })

    async def run(self) -> None:
        producer_task = asyncio.create_task(self._producer())
        try:
            await self._consume()
        finally:
            # Cancel the producer (which may be parked on a saturated
            # ``queue.put``) and drain any pending exception. Without the
            # cancel, a ``_consume`` error would leave the producer parked
            # forever and ``await producer_task`` would deadlock.
            producer_task.cancel()
            await asyncio.gather(producer_task, return_exceptions=True)
```

> **Note (Cycle A `_resolve_application` / `_resolve_label`).** These two helpers synthesize a minimal `Application` and `Label` directly from the `application_ref` / `label_id` strings carried on each `BatchItem`. This IS the production wiring for the MVP — the `BatchEnvelope` (PRD §6.3) is JSON-only with reference strings; no separate applications/labels registry exists in this codebase. The Evaluator's chokepoint contract only needs the refs to compute `input_hash`, so synthesizing the minimal schema-conforming instances is sufficient. A future production trajectory (multi-tenant storage, identity claims) would replace the synthesized instances with a real lookup; that swap is OQ-PRD-1 / OQ-ARCH-3 territory and is **out of scope** for E6.

- [ ] **Step A.4: Run Cycle A focused → GREEN (3 passed)**

`uv run pytest tests/test_batch_worker_skeleton.py -v` → 3 passed.

- [ ] **Step A.5: Commit Cycle A**

```bash
git add app/batch/worker.py tests/test_batch_worker_skeleton.py
git commit -m "feat(e6): BatchWorker skeleton — single-item end-to-end, first-label-individual (FR-401)"
```

### Cycle B — lookahead pre-fetch + bounded-queue saturation (FR-402, FR-403)

- [ ] **Step B.1: Write the failing test**

```python
# tests/test_batch_worker_lookahead.py
"""BatchWorker lookahead + pull-based demand. FR-402, FR-403."""
import asyncio
from datetime import datetime, timezone

import pytest

from app.api._sse_bus import SSEBus
from app.batch.anomaly import AnomalyDetector
from app.batch.state import InFlightBatch
from app.batch.worker import BatchWorker
from app.schemas.batch import BatchItem, ItemState
from tests.conftest import _fake_evaluator


def _stub_item(idx: int) -> BatchItem:
    return BatchItem(
        label_id=f"lbl-{idx}",
        application_ref=f"app-{idx:04d}",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 5, 4, 12, 0, idx, tzinfo=timezone.utc),
    )


@pytest.mark.asyncio
async def test_worker_queue_saturates_at_lookahead_plus_one_when_consumer_holds():
    """FR-403: when the consumer doesn't drain, the producer's queue saturates
    at maxsize=k+1=4 (lookahead_k=3)."""
    items = tuple(_stub_item(i) for i in range(10))
    in_flight = InFlightBatch(
        batch_id="B-LA1", agent_id="a", items=items, lookahead_k=3,
    )

    # FakeEvaluator that NEVER returns — we drive saturation by holding the
    # consumer indefinitely.
    class _BlockingEvaluator:
        async def evaluate(self, app, label):
            await asyncio.Event().wait()  # never resolves

    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=_BlockingEvaluator(),
        anomaly=AnomalyDetector(),
        bus=SSEBus(),
    )

    run_task = asyncio.create_task(worker.run())
    # Give the producer time to fill the queue
    await asyncio.sleep(0.1)
    assert in_flight.queue.qsize() <= 4
    assert in_flight.queue.saturated is True
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_worker_lookahead_k_3_pre_fetches_next_two_items_while_one_processes():
    """FR-402: when item N is being evaluated, items N+1 and N+2 are already in
    the queue (state ItemState.PROCESSING in spirit; verified here by checking
    `qsize` mid-evaluation)."""
    items = tuple(_stub_item(i) for i in range(5))
    in_flight = InFlightBatch(
        batch_id="B-LA2", agent_id="a", items=items, lookahead_k=3,
    )

    # Slow evaluator — 0.3s per call. After item 0 finishes, items 1, 2, 3
    # should be queued (k+1 = 4 capacity, but we only have 5 total items).
    fake_eval = _fake_evaluator(n_items=5, latency_s=0.3)
    bus = SSEBus()
    sub = bus.subscribe()
    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=fake_eval,
        anomaly=AnomalyDetector(),
        bus=bus,
    )

    run_task = asyncio.create_task(worker.run())
    # Wait for item 0's event
    e0 = await asyncio.wait_for(sub.get(), timeout=1.0)
    assert e0["data"]["queue_position"] == 0

    # At this point item 1 is being evaluated; items 2, 3, 4 should be in
    # the queue (the producer fills eagerly until saturation or end).
    # We have 4 remaining items and maxsize=4 → all 4 in the queue.
    # But item 1 was just popped → 3 in the queue, 1 in flight.
    await asyncio.sleep(0.05)  # let producer top up
    assert in_flight.queue.qsize() >= 2, (
        f"expected at least 2 items pre-fetched, got qsize={in_flight.queue.qsize()}"
    )

    # Drain remaining
    for _ in range(4):
        await asyncio.wait_for(sub.get(), timeout=2.0)
    end_evt = await asyncio.wait_for(sub.get(), timeout=2.0)
    assert end_evt["event"] == "stream-end"
    await run_task
```

- [ ] **Step B.2: Run focused → RED**

The Cycle A implementation already handles FR-402/403 because the producer-task pattern naturally saturates the bounded queue. The Cycle B tests should pass against Cycle A's code. **However**, run them first to confirm.

`uv run pytest tests/test_batch_worker_lookahead.py -v` → expect PASS (no implementation change required).

If any Cycle B test fails RED, the most likely cause is that Cycle A's `_consume` loop doesn't yield enough between `await queue.get()` calls to let the producer top up. Fix is to add `await asyncio.sleep(0)` after the `record_result` line so the event loop can run the producer (Rule 1-3 — minimal addition).

- [ ] **Step B.3: Commit Cycle B (test-only)**

If the tests pass without code changes, commit only the test file:

```bash
git add tests/test_batch_worker_lookahead.py
git commit -m "test(e6): BatchWorker lookahead + bounded-queue saturation (FR-402, FR-403)"
```

If a code change was needed (Rule 1-3 fix), include `app/batch/worker.py` in the commit:

```bash
git add app/batch/worker.py tests/test_batch_worker_lookahead.py
git commit -m "feat(e6): BatchWorker lookahead pre-fetch + cooperative yield (FR-402, FR-403)"
```

### Cycle C — anomaly broadcast + override-aware-non-stopping + completion semantics

- [ ] **Step C.1: Write the failing test**

```python
# tests/test_batch_worker_anomaly_override.py
"""BatchWorker — anomaly broadcast (FR-405), override-aware-non-stopping (FR-404),
completion semantics (stream-end fires once after last per-label event)."""
import asyncio
from datetime import datetime, timezone

import pytest

from app.api._sse_bus import SSEBus
from app.batch.anomaly import AnomalyDetector
from app.batch.state import InFlightBatch
from app.batch.worker import BatchWorker
from app.schemas.audit import AuditRecord, OverrideEntry, PerRuleTraceEntry
from app.schemas.batch import BatchItem, ItemState
from app.schemas.metrics import Metrics
from app.schemas.wire.disposition import ConfidenceBand, DispositionEnvelope
from tests.conftest import _fake_evaluator


def _stub_item(idx: int) -> BatchItem:
    return BatchItem(
        label_id=f"lbl-{idx}",
        application_ref=f"app-{idx:04d}",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 5, 4, 12, 0, idx, tzinfo=timezone.utc),
    )


def _envelope_with_reason_code(idx: int, code: str) -> DispositionEnvelope:
    """DispositionEnvelope whose first FieldFindingWire's first RuleFindingWire
    carries the given reason_code, so `_headline_reason_code` returns it via
    the per-field path (the primary, non-short-circuit case)."""
    from app.schemas.wire.disposition import (
        AISuggestionWire,
        FieldEvidenceWire,
        FieldFindingWire,
        RuleFindingWire,
    )

    now = datetime.now(timezone.utc)
    finding = RuleFindingWire(
        rule_id="R-001",
        cfr_citation="27 CFR §4.33",
        disposition="needs_review",
        reason_code=code,
        plain_language_explanation="Synthetic for batch test.",
    )
    field = FieldFindingWire(
        field_name="brand_name",
        extracted_value="x",
        expected_value="x",
        evidence=FieldEvidenceWire(
            bbox=(0, 0, 1, 1),
            crop_ref="ev/R-001",
            extraction_confidence=0.9,
        ),
        rule_findings=(finding,),
        ai_suggestion=AISuggestionWire(present=False),
        field_confidence=ConfidenceBand(band="medium", numeric=0.7),
    )
    return DispositionEnvelope(
        evaluation_id=f"EV-{idx:04d}",
        label_ref=f"lbl-{idx:04d}",
        disposition="needs_review",
        disposition_confidence=ConfidenceBand(band="medium", numeric=0.7),
        fields=(field,),
        audit_trail=AuditRecord(
            evaluation_id=f"EV-{idx:04d}",
            rule_set_version="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            started_at=now,
            completed_at=now,
            per_rule_trace=(
                PerRuleTraceEntry(
                    rule_id="R-001",
                    disposition="needs_review",
                    evidence_ref="ev/R-001",
                ),
            ),
        ),
        metrics=Metrics(
            total_duration_ms=10,
            per_rule_durations_ms=(),
            vision_duration_ms=5,
            orchestrator_duration_ms=0,
        ),
    )


def _short_circuit_envelope_with_reason_code(idx: int, code: str) -> DispositionEnvelope:
    """Short-circuit envelope (no fields) — `_headline_reason_code` falls back
    to `per_rule_trace[0].rule_id`, which by E5 convention encodes the reason
    code for legibility / FR-900 chokepoint envelopes."""
    now = datetime.now(timezone.utc)
    return DispositionEnvelope(
        evaluation_id=f"EV-{idx:04d}",
        label_ref=f"lbl-{idx:04d}",
        disposition="needs_review",
        disposition_confidence=ConfidenceBand(band="low", numeric=0.0),
        fields=(),
        audit_trail=AuditRecord(
            evaluation_id=f"EV-{idx:04d}",
            rule_set_version="t",
            input_hash="0" * 64,
            output_hash="0" * 64,
            started_at=now,
            completed_at=now,
            per_rule_trace=(
                PerRuleTraceEntry(
                    rule_id=code,  # short-circuit convention: rule_id IS the reason code
                    disposition="needs_review",
                    evidence_ref="",
                ),
            ),
        ),
        metrics=Metrics(
            total_duration_ms=10,
            per_rule_durations_ms=(),
            vision_duration_ms=5,
            orchestrator_duration_ms=0,
        ),
    )
```

```python
@pytest.mark.asyncio
async def test_worker_emits_anomaly_advisory_on_5_of_10_same_reason_code():
    """FR-405: 5 of last 10 same-code observations fire an advisory."""
    # 10 items, all returning needs_review with same reason_code
    items = tuple(_stub_item(i) for i in range(10))
    in_flight = InFlightBatch(
        batch_id="B-AN1", agent_id="a", items=items, lookahead_k=3,
    )
    plan = [(0.0, _envelope_with_reason_code(i, "BRAND.NAME.MISMATCH")) for i in range(10)]
    fake_eval = _fake_evaluator(plan=plan)
    bus = SSEBus()
    sub = bus.subscribe()
    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=fake_eval,
        anomaly=AnomalyDetector(window_n=10, threshold_m=5),
        bus=bus,
    )

    await worker.run()

    # Drain all events from the subscriber
    events = []
    while not sub.empty():
        events.append(sub.get_nowait())

    # Expected event types: 10 label-result + 1 anomaly-advisory + 1 stream-end
    types = [e["event"] for e in events]
    assert types.count("label-result") == 10
    assert types.count("anomaly-advisory") == 1
    assert types.count("stream-end") == 1
    # The advisory must come BEFORE stream-end (in order)
    advisory_idx = types.index("anomaly-advisory")
    stream_end_idx = types.index("stream-end")
    assert advisory_idx < stream_end_idx


@pytest.mark.asyncio
async def test_worker_continues_after_in_flight_results_mutation_simulating_override():
    """FR-404 positive: when the override endpoint mutates
    `in_flight.results[label_id]` mid-batch, the worker keeps going."""
    items = tuple(_stub_item(i) for i in range(3))
    in_flight = InFlightBatch(
        batch_id="B-OV1", agent_id="a", items=items, lookahead_k=3,
    )
    fake_eval = _fake_evaluator(n_items=3, latency_s=0.05)
    bus = SSEBus()
    sub = bus.subscribe()
    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=fake_eval,
        anomaly=AnomalyDetector(),
        bus=bus,
    )

    run_task = asyncio.create_task(worker.run())

    # After item 0 lands, simulate an override mutation
    e0 = await asyncio.wait_for(sub.get(), timeout=1.0)
    assert e0["data"]["queue_position"] == 0

    # Mutate in_flight.results[lbl-0] — simulating the override endpoint
    from datetime import datetime, timezone

    original = in_flight.results["lbl-0"]
    new_audit = original.audit_trail.model_copy(update={
        "overrides": (
            OverrideEntry(
                field_name=None,
                original_disposition=original.disposition,
                applied_disposition="pass",
                reason_code="BRAND.NAME.NEEDS_REVIEW",
                justification_text="Test override",
                reviewer_id="session-test1234",
                timestamp=datetime.now(timezone.utc),
            ),
        ),
    })
    in_flight.results["lbl-0"] = original.model_copy(update={"audit_trail": new_audit})

    # Worker must continue and emit events 1, 2, then stream-end
    e1 = await asyncio.wait_for(sub.get(), timeout=1.0)
    e2 = await asyncio.wait_for(sub.get(), timeout=1.0)
    end_evt = await asyncio.wait_for(sub.get(), timeout=1.0)

    assert e1["data"]["queue_position"] == 1
    assert e2["data"]["queue_position"] == 2
    assert end_evt["event"] == "stream-end"
    await run_task


@pytest.mark.asyncio
async def test_worker_emits_stream_end_exactly_once_after_last_label_result():
    items = tuple(_stub_item(i) for i in range(3))
    in_flight = InFlightBatch(
        batch_id="B-CC1", agent_id="a", items=items, lookahead_k=3,
    )
    fake_eval = _fake_evaluator(n_items=3, latency_s=0.0)
    bus = SSEBus()
    sub = bus.subscribe()
    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=fake_eval,
        anomaly=AnomalyDetector(),
        bus=bus,
    )

    await worker.run()

    events = []
    while not sub.empty():
        events.append(sub.get_nowait())

    types = [e["event"] for e in events]
    assert types == ["label-result", "label-result", "label-result", "stream-end"]
```

- [ ] **Step C.2: Run Cycle C focused → RED**

`uv run pytest tests/test_batch_worker_anomaly_override.py -v` → expect mixed: against Cycle A code, the override-non-stopping behavioral test + stream-end-exactly-once test pass; the anomaly test fails because Cycle A does not yet broadcast the advisory event over the bus when `AnomalyDetector.observe(...)` returns one. (Sanity check: `_headline_reason_code` reads `RuleFindingWire.reason_code` from `envelope.fields[]` and falls back to `per_rule_trace[0].rule_id` — both fields exist on the current schema, so no E1 schema extension is needed.)

- [ ] **Step C.3: Implement Cycle C**

Cycle C is purely behavioral: bind the anomaly observation, broadcast the `anomaly-advisory` event when `observe(...)` returns non-None, and assert exactly one `stream-end` after the last per-label event. The worker code shown in Cycle A already includes this behavior — Cycle C's contribution is the test surface that pins it. No schema changes; no new files.

- [ ] **Step C.4: Run Cycle C focused → GREEN (4 passed)**

`uv run pytest tests/test_batch_worker_anomaly_override.py -v` → 4 passed.

- [ ] **Step C.5: Commit Cycle C**

```bash
git add tests/test_batch_worker_anomaly_override.py
git commit -m "test(e6): BatchWorker anomaly + override-non-stopping + stream-end semantics (FR-404, FR-405)"
```

---

## Task 7: app/api/batches.py + app/main.py register

**Files:**
- Create: `app/api/batches.py`
- Modify: `app/main.py` (additive — append batches.router registration + `app.state.batches = {}` in lifespan startup, `app.state.batches.clear()` in lifespan shutdown)
- Test: `tests/test_batch_endpoint_post.py`
- Test: `tests/test_batch_endpoint_sse.py`

Wave 3 single. Depends on T6 (worker). Owns POST + 2 GET endpoints. Wires `app.state.batches`, `app.state.applications`, `app.state.labels` (the last two are the submission registry the worker reads via the Depends-injected lookups).

- [ ] **Step 1: Write the failing test (POST + GET snapshot)**

```python
# tests/test_batch_endpoint_post.py
"""POST /batches and GET /batches/{batch_id} — basic shape."""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.wire.batch import BatchEnvelope, BatchItemRef


def _stub_envelope(n_items: int = 3) -> dict:
    return BatchEnvelope(
        batch_id="B-test-001",
        agent_id="agent-mvp",
        submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
        items=tuple(
            BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
            for i in range(n_items)
        ),
    ).model_dump(mode="json")


def test_post_batches_returns_202_and_batch_id():
    app = create_app()
    client = TestClient(app)
    payload = _stub_envelope(n_items=3)
    resp = client.post("/batches", json=payload)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert "batch_id" in body
    assert body["batch_id"] == payload["batch_id"]


def test_post_batches_rejects_malformed_envelope_with_400():
    app = create_app()
    client = TestClient(app)
    resp = client.post("/batches", json={"foo": "bar"})
    assert resp.status_code in (400, 422), resp.text  # Pydantic validation


def test_get_batches_returns_snapshot():
    app = create_app()
    client = TestClient(app)
    payload = _stub_envelope(n_items=2)
    post_resp = client.post("/batches", json=payload)
    assert post_resp.status_code == 202
    batch_id = post_resp.json()["batch_id"]

    get_resp = client.get(f"/batches/{batch_id}")
    assert get_resp.status_code == 200
    snap = get_resp.json()
    assert snap["batch_id"] == batch_id
    assert snap["agent_id"] == "agent-mvp"
    assert len(snap["items"]) == 2


def test_get_batches_unknown_batch_id_returns_404():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/batches/B-does-not-exist")
    assert resp.status_code == 404
```

- [ ] **Step 2: Write the failing test (SSE)**

```python
# tests/test_batch_endpoint_sse.py
"""GET /batches/{batch_id}/stream — SSE per-label events + stream-end."""
import asyncio

import httpx
import pytest

from app.main import create_app


@pytest.mark.asyncio
async def test_sse_stream_emits_per_label_events_then_stream_end_for_3_item_batch(monkeypatch):
    """3-item batch with fast fake evaluator → 3 label-result + 1 stream-end events."""
    from tests.conftest import _fake_evaluator

    # Override the evaluator factory before app boot so the worker uses the fake.
    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=3, latency_s=0.05),
    )
    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        from datetime import datetime, timezone
        from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
        payload = BatchEnvelope(
            batch_id="B-sse-001",
            agent_id="a",
            submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
            items=tuple(
                BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                for i in range(3)
            ),
        ).model_dump(mode="json")
        post_resp = await client.post("/batches", json=payload)
        assert post_resp.status_code == 202

        # Open SSE stream
        events = []
        async with client.stream("GET", "/batches/B-sse-001/stream") as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                if "stream-end" in line:
                    break

        assert events.count("label-result") == 3
        assert events.count("stream-end") == 1
        # Order
        assert events[-1] == "stream-end"


@pytest.mark.asyncio
async def test_sse_subscriber_pruned_within_1s_on_client_disconnect(monkeypatch):
    """AC #9: client disconnect → subscriber removed within 1 s; worker continues."""
    from tests.conftest import _fake_evaluator

    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=10, latency_s=0.1),
    )
    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        from datetime import datetime, timezone
        from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
        payload = BatchEnvelope(
            batch_id="B-sse-002",
            agent_id="a",
            submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
            items=tuple(
                BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                for i in range(10)
            ),
        ).model_dump(mode="json")
        await client.post("/batches", json=payload)

        # Open and close fast
        async with client.stream("GET", "/batches/B-sse-002/stream") as resp:
            await resp.aiter_lines().__anext__()  # read 1 line
            # context-manager exit closes connection

        # Verify subscriber pruned within 1s. SSE subscribers live on the
        # per-batch SSEBus stored in `app.state.buses[batch_id]`, not on
        # InFlightBatch.
        bus = app.state.buses["B-sse-002"]
        for _ in range(20):  # poll up to 1 s @ 50ms
            await asyncio.sleep(0.05)
            if len(bus.subscribers) == 0:
                break
        assert len(bus.subscribers) == 0


@pytest.mark.asyncio
async def test_post_batches_rejects_duplicate_batch_id_with_409(monkeypatch):
    """409 collision: re-POST of an in-flight `batch_id` is rejected."""
    from datetime import datetime, timezone

    from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
    from tests.conftest import _fake_evaluator

    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=2, latency_s=0.5),
    )
    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            payload = BatchEnvelope(
                batch_id="B-dup",
                agent_id="a",
                submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
                items=tuple(
                    BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                    for i in range(2)
                ),
            ).model_dump(mode="json")
            r1 = await client.post("/batches", json=payload)
            assert r1.status_code == 202
            r2 = await client.post("/batches", json=payload)
            assert r2.status_code == 409
            assert "B-dup" in r2.json()["detail"]
```

- [ ] **Step 3: Run focused → RED**

`uv run pytest tests/test_batch_endpoint_post.py tests/test_batch_endpoint_sse.py -v` → 404 / ImportError on `app.api.batches`.

- [ ] **Step 4: Implement endpoint**

```python
# app/api/batches.py
"""POST /batches, GET /batches/{batch_id}/stream, GET /batches/{batch_id}.

Source: ARCH §3.2 / L1 §2.5.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.api._sse_bus import SSEBus
from app.batch.anomaly import AnomalyDetector
from app.batch.state import InFlightBatch
from app.batch.worker import BatchWorker
from app.config import Settings
from app.schemas.batch import BatchItem, ItemState
from app.schemas.wire.batch import BatchEnvelope

router = APIRouter()
_logger = logging.getLogger("app.api.batches")


def _get_settings() -> Settings:
    """Module-private Settings factory. Mirrors E5's app/api/healthz.py and
    app/api/labels.py convention — `app/deps.py` exposes no `get_settings`
    by design. Tests override via FastAPI's dependency_overrides[]."""
    return Settings()


def _build_in_flight_from_envelope(env: BatchEnvelope, *, lookahead_k: int) -> InFlightBatch:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    items = tuple(
        BatchItem(
            label_id=ref.label_ref,
            application_ref=ref.application_ref,
            state=ItemState.QUEUED,
            result=None,
            enqueued_at=now,
        )
        for ref in env.items
    )
    return InFlightBatch(
        batch_id=env.batch_id,
        agent_id=env.agent_id,
        items=items,
        lookahead_k=lookahead_k,
    )


def _resolve_lookahead_k(settings: Settings) -> int:
    """LOOKAHEAD_K env override (AC #10). Default 3."""
    import os
    raw = os.environ.get("LOOKAHEAD_K", "3")
    try:
        k = int(raw)
    except ValueError:
        k = 3
    return max(1, k)


@router.post("/batches", status_code=202)
async def post_batches(
    envelope: BatchEnvelope,
    request: Request,
    settings: Settings = Depends(_get_settings),
) -> dict[str, str]:
    """Spawn a worker and return the batch_id."""
    if envelope.batch_id in request.app.state.batches:
        raise HTTPException(status_code=409, detail=f"batch_id {envelope.batch_id} already in flight")

    lookahead_k = _resolve_lookahead_k(settings)
    in_flight = _build_in_flight_from_envelope(envelope, lookahead_k=lookahead_k)
    bus = SSEBus()
    request.app.state.batches[envelope.batch_id] = in_flight
    request.app.state.buses[envelope.batch_id] = bus

    # Build evaluator via the existing E5 factory; tests monkeypatch this.
    from app.deps import build_evaluator
    evaluator = build_evaluator(settings)

    worker = BatchWorker(
        in_flight=in_flight,
        evaluator=evaluator,
        anomaly=AnomalyDetector(),
        bus=bus,
    )
    asyncio.create_task(worker.run())
    return {"batch_id": envelope.batch_id}


@router.get("/batches/{batch_id}")
async def get_batch_snapshot(batch_id: str, request: Request) -> dict[str, Any]:
    in_flight = request.app.state.batches.get(batch_id)
    if in_flight is None:
        raise HTTPException(status_code=404, detail=f"batch_id {batch_id} not found")
    return in_flight.snapshot().model_dump(mode="json")


@router.get("/batches/{batch_id}/stream")
async def get_batch_stream(batch_id: str, request: Request):
    in_flight = request.app.state.batches.get(batch_id)
    if in_flight is None:
        raise HTTPException(status_code=404, detail=f"batch_id {batch_id} not found")
    bus: SSEBus | None = request.app.state.buses.get(batch_id)
    if bus is None:
        raise HTTPException(status_code=404, detail=f"batch_id {batch_id} stream not registered")
    sub = bus.subscribe()

    async def _event_generator():
        try:
            async for evt in bus.iterate(sub, terminator_event="stream-end"):
                yield {"event": evt["event"], "data": evt["data"]}
        finally:
            bus.unsubscribe(sub)

    return EventSourceResponse(_event_generator())
```

Edit `app/main.py` (additive — register router + lifespan state):

```python
# app/main.py — diff context
@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    logging.getLogger("app.main").info(
        "app_startup",
        extra={
            "reason_code": "ENGINE.OK.NONE",
            "rule_set_version": "0.0.0",
            "model_version": settings.llm_model_snapshot,
            "prompt_version": settings.prompt_version,
        },
    )
    app.state.batches = {}  # E6 NFR-DATA-001/002 — process-local in-flight batches
    app.state.buses = {}    # E6 — per-batch SSEBus registry, keyed by batch_id
    yield
    app.state.batches.clear()  # E6 lifespan teardown evicts all in-flight batches
    app.state.buses.clear()    # E6 — drop bus subscribers + queues

# ... existing labels and raw router includes ...

from app.api import batches as batches_module
application.include_router(batches_module.router)
```

> **Boundary note.** The per-batch SSEBus is stored in a separate `app.state.buses: dict[str, SSEBus]` keyed by `batch_id`, NOT on `InFlightBatch`. Keeping the bus off the dataclass preserves the substitutability seam called out in the architecture (the bus could be swapped for a Redis Pub/Sub adapter without touching `InFlightBatch`) and avoids the circular-import risk between `app/batch/state.py` (T1) and `app/api/_sse_bus.py` (T4). T7 owns the lifespan-init and -teardown of `app.state.buses`.

- [ ] **Step 5: Run focused → GREEN (7 passed across both test files)**

`uv run pytest tests/test_batch_endpoint_post.py tests/test_batch_endpoint_sse.py -v` → 7 passed.

- [ ] **Step 6: Run full suite to confirm no regression**

`uv run pytest -q` → expect prior count + new tests passing.

- [ ] **Step 7: Commit**

```bash
git add app/api/batches.py app/main.py tests/test_batch_endpoint_post.py tests/test_batch_endpoint_sse.py
git commit -m "feat(e6): POST /batches + GET /batches/{id}{/stream} — SSE wire surface"
```

---

## Task 8: app/api/overrides.py + app/main.py append

**Files:**
- Create: `app/api/overrides.py`
- Modify: `app/main.py` (additive — append overrides.router registration)
- Test: `tests/test_override_endpoint.py`
- Test: `tests/test_override_audit_trail.py`

Wave 4 single. Depends on T0 (`OverrideEntry.field_name = None` allowed), T7 (`app.state.batches` populated, `InFlightBatch.results` mutable). Validates `reason_code` against the loaded `rules/reason_codes.yaml` registry.

- [ ] **Step 1: Write the failing test (endpoint)**

```python
# tests/test_override_endpoint.py
"""POST /labels/{evaluation_id}/overrides — happy path + validation."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def _seed_a_batch_with_one_completed_item(app):
    """Helper: drive a 1-item batch through and wait for completion so the
    override endpoint has a valid evaluation_id to target."""
    from app.batch.anomaly import AnomalyDetector
    from app.batch.state import InFlightBatch
    from app.batch.worker import BatchWorker
    from app.api._sse_bus import SSEBus
    from app.schemas.batch import BatchItem, ItemState
    from tests.conftest import _fake_evaluator, _stub_disposition_envelope

    item = BatchItem(
        label_id="lbl-0",
        application_ref="app-0000",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    env = _stub_disposition_envelope(0, disposition="needs_review")
    in_flight = InFlightBatch(batch_id="B-OV", agent_id="a", items=(item,), lookahead_k=3)
    in_flight.results["lbl-0"] = env
    app.state.batches["B-OV"] = in_flight
    if not hasattr(app.state, "buses"):
        app.state.buses = {}
    app.state.buses["B-OV"] = SSEBus()
    return env


def test_post_override_records_entry_and_returns_200():
    app = create_app()
    app.state.batches = {}  # ensure fresh
    env = _seed_a_batch_with_one_completed_item(app)
    client = TestClient(app)

    payload = {
        "reason_code": "BRAND.NAME.NEEDS_REVIEW",
        "applied_disposition": "pass",
        "justification_text": "Looks correct on review.",
    }
    resp = client.post(f"/labels/{env.evaluation_id}/overrides", json=payload)
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["original_disposition"] == "needs_review"
    assert body["applied_disposition"] == "pass"
    assert body["reason_code"] == "BRAND.NAME.NEEDS_REVIEW"
    assert body["justification_text"] == "Looks correct on review."
    assert body["reviewer_id"].startswith("session-")
    assert "timestamp" in body


def test_post_override_rejects_unknown_reason_code():
    app = create_app()
    app.state.batches = {}
    env = _seed_a_batch_with_one_completed_item(app)
    client = TestClient(app)

    payload = {
        "reason_code": "BRAND.NAME.NOT.IN.REGISTRY",  # bogus
        "applied_disposition": "pass",
    }
    resp = client.post(f"/labels/{env.evaluation_id}/overrides", json=payload)
    assert resp.status_code == 400
    assert "reason_code" in resp.json()["detail"].lower()


def test_post_override_rejects_unknown_evaluation_id():
    app = create_app()
    app.state.batches = {}
    client = TestClient(app)
    payload = {"reason_code": "BRAND.NAME.NEEDS_REVIEW", "applied_disposition": "pass"}
    resp = client.post("/labels/EV-DOES-NOT-EXIST/overrides", json=payload)
    assert resp.status_code == 404


def test_post_override_with_field_name_records_field_specific_entry():
    app = create_app()
    app.state.batches = {}
    env = _seed_a_batch_with_one_completed_item(app)
    client = TestClient(app)

    payload = {
        "field_name": "brand_name",
        "reason_code": "BRAND.NAME.NEEDS_REVIEW",
        "applied_disposition": "pass",
    }
    resp = client.post(f"/labels/{env.evaluation_id}/overrides", json=payload)
    assert resp.status_code == 200
    assert resp.json()["field_name"] == "brand_name"
```

- [ ] **Step 2: Write the failing test (audit trail)**

```python
# tests/test_override_audit_trail.py
"""Verify all FR-801 fields land on the persisted audit_trail."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def test_override_lands_on_in_flight_results_audit_trail_overrides_tuple():
    from app.batch.anomaly import AnomalyDetector
    from app.batch.state import InFlightBatch
    from app.api._sse_bus import SSEBus
    from app.schemas.batch import BatchItem, ItemState
    from tests.conftest import _stub_disposition_envelope

    app = create_app()
    app.state.batches = {}
    item = BatchItem(
        label_id="lbl-0",
        application_ref="app-0000",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
    )
    env = _stub_disposition_envelope(0, disposition="needs_review")
    in_flight = InFlightBatch(batch_id="B-OV2", agent_id="a", items=(item,), lookahead_k=3)
    in_flight.results["lbl-0"] = env
    app.state.batches["B-OV2"] = in_flight
    if not hasattr(app.state, "buses"):
        app.state.buses = {}
    app.state.buses["B-OV2"] = SSEBus()

    client = TestClient(app)
    payload = {
        "reason_code": "BRAND.NAME.NEEDS_REVIEW",
        "applied_disposition": "pass",
        "justification_text": "Manual review approved.",
    }
    resp = client.post(f"/labels/{env.evaluation_id}/overrides", json=payload)
    assert resp.status_code == 200

    # In-flight result must now carry the override
    persisted = in_flight.results["lbl-0"]
    overrides = persisted.audit_trail.overrides
    assert len(overrides) == 1
    o = overrides[0]
    assert o.field_name is None  # whole-envelope override
    assert o.original_disposition == "needs_review"
    assert o.applied_disposition == "pass"
    assert o.reason_code == "BRAND.NAME.NEEDS_REVIEW"
    assert o.justification_text == "Manual review approved."
    assert o.reviewer_id.startswith("session-")
    assert isinstance(o.timestamp, datetime)
```

- [ ] **Step 3: Run focused → RED**

`uv run pytest tests/test_override_endpoint.py tests/test_override_audit_trail.py -v` → 404 / ImportError on `app.api.overrides`.

- [ ] **Step 4: Implement endpoint**

```python
# app/api/overrides.py
"""POST /labels/{evaluation_id}/overrides.

Source: ARCH §3.2 / L1 §2.6 / FR-800-804.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.schemas.audit import OverrideEntry

router = APIRouter()
_logger = logging.getLogger("app.api.overrides")


def _load_accepted_reason_codes() -> frozenset[str]:
    """Load the canonical reason-code registry from rules/reason_codes.yaml.

    Mirrors E2's loader cross-check 7 — refuses any code not in the registry.
    Raises ``FileNotFoundError`` if the registry is missing; loud failure
    is preferable to silently rejecting every override request with 400."""
    import yaml
    from pathlib import Path

    yaml_path = Path("rules/reason_codes.yaml")
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"reason-code registry not found at {yaml_path.resolve()} — "
            "the override endpoint cannot validate codes without it"
        )
    raw = yaml.safe_load(yaml_path.read_text())
    return frozenset((raw or {}).get("codes", {}).keys())


_ACCEPTED_REASON_CODES_CACHE: frozenset[str] | None = None


def _accepted_reason_codes() -> frozenset[str]:
    """Lazy accessor — load on first call, cache for the process. Lazy
    initialization avoids a module-import side effect that would fail
    opaquely if any test imports this module before the cwd is repo-root.
    Tests can reset the cache via ``app.api.overrides._ACCEPTED_REASON_CODES_CACHE = None``."""
    global _ACCEPTED_REASON_CODES_CACHE
    if _ACCEPTED_REASON_CODES_CACHE is None:
        _ACCEPTED_REASON_CODES_CACHE = _load_accepted_reason_codes()
    return _ACCEPTED_REASON_CODES_CACHE


class OverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str | None = None
    applied_disposition: Literal["pass", "fail", "needs_review"]
    reason_code: str
    justification_text: str | None = None


def _new_reviewer_id() -> str:
    return "session-" + uuid.uuid4().hex[:12]


def _find_label_in_batches(state_batches, evaluation_id: str):
    """Locate the (batch_id, InFlightBatch, label_id, env) for an evaluation
    that has a recorded ``result``. O(N*M) — acceptable for prototype scale.

    Contract: a label that is queued but not yet evaluated has no entry in
    ``in_flight.results`` and is therefore NOT findable. Callers MUST treat
    that case as 404 (the override is rejected because the disposition the
    reviewer is overriding does not yet exist). The UI guards by enabling
    the override button only after the SSE ``label-result`` event lands."""
    for batch_id, in_flight in state_batches.items():
        for label_id, env in in_flight.results.items():
            if env.evaluation_id == evaluation_id:
                return batch_id, in_flight, label_id, env
    return None, None, None, None


@router.post("/labels/{evaluation_id}/overrides")
async def post_override(
    evaluation_id: str,
    payload: OverrideRequest,
    request: Request,
) -> dict:
    if payload.reason_code not in _accepted_reason_codes():
        raise HTTPException(
            status_code=400,
            detail=f"reason_code '{payload.reason_code}' is not in the loaded registry",
        )

    batch_id, in_flight, label_id, env = _find_label_in_batches(
        request.app.state.batches, evaluation_id
    )
    if env is None:
        # Two-of-three cases collapse to 404: (a) evaluation_id never existed
        # in any batch; (b) label is queued but evaluator has not yet emitted
        # a result. Per the contract above, the UI prevents (b) by gating the
        # override button on the SSE label-result event.
        raise HTTPException(
            status_code=404,
            detail=f"evaluation_id {evaluation_id} not found in any in-flight batch result",
        )

    entry = OverrideEntry(
        field_name=payload.field_name,
        original_disposition=env.disposition,
        applied_disposition=payload.applied_disposition,
        reason_code=payload.reason_code,
        justification_text=payload.justification_text,
        reviewer_id=_new_reviewer_id(),
        timestamp=datetime.now(timezone.utc),
    )

    new_audit = env.audit_trail.model_copy(update={
        "overrides": env.audit_trail.overrides + (entry,),
    })
    new_env = env.model_copy(update={"audit_trail": new_audit})
    in_flight.results[label_id] = new_env

    # Surface on the SSE stream so the UI updates the timeline. Bus may be
    # absent if the lifespan registry has been torn down concurrently; treat
    # the broadcast as best-effort — the audit-trail mutation is the
    # source-of-truth contract.
    bus = request.app.state.buses.get(batch_id)
    if bus is not None:
        bus.broadcast({
            "event": "override-applied",
            "data": {
                "batch_id": batch_id,
                "evaluation_id": evaluation_id,
                "entry": entry.model_dump(mode="json"),
            },
        })

    return entry.model_dump(mode="json")
```

Edit `app/main.py` — append router include:

```python
# app/main.py — diff context (after batches.router include)
from app.api import overrides as overrides_module
application.include_router(overrides_module.router)
```

- [ ] **Step 5: Run focused → GREEN (5 passed across both test files)**

`uv run pytest tests/test_override_endpoint.py tests/test_override_audit_trail.py -v` → 5 passed.

- [ ] **Step 6: Run full suite to confirm no regression**

`uv run pytest -q` → expect prior count + new tests passing.

- [ ] **Step 7: Commit**

```bash
git add app/api/overrides.py app/main.py tests/test_override_endpoint.py tests/test_override_audit_trail.py
git commit -m "feat(e6): POST /labels/{id}/overrides — registry-validated reason codes (FR-800-804)"
```

---

## Task 9: tests/test_batch_first_label_perf.py — first-label individual canary (AC-FR-401)

**Files:**
- Test: `tests/test_batch_first_label_perf.py`

Wave 5 parallel. Depends on T7 (endpoint up). Pure perf test — no production code changes.

> **Test pattern note.** This is a 30-trial performance test analogous to E5's T19. Marked `@pytest.mark.slow` so it does not run in the default `pytest -q` flow. The CI pipeline (or a manual run) executes `uv run pytest -m slow` to exercise it.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_batch_first_label_perf.py
"""AC-FR-401 perf canary: 50-item batch — first-label P50 ≤ 2.7 s, P99 ≤ 5.0 s."""
import asyncio
import statistics
import time

import httpx
import pytest


@pytest.mark.slow
@pytest.mark.asyncio
async def test_first_label_p50_under_2_7s_and_p99_under_5_0s_for_50_item_batch(monkeypatch):
    """AC-FR-401 + AC #2 (50 + N + 1 event count) on the same fixture.

    Methodology mirrors E5's T19: one app per session (not per trial), 2-trial
    warmup (drops JIT / first-import cost), 30-trial measurement window. Fresh
    `batch_id` per trial keeps `app.state.batches` from collapsing onto a
    409 collision."""
    from datetime import datetime, timezone

    from app.main import create_app
    from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
    from tests.conftest import _fake_evaluator

    # 0.3s per evaluator call — comfortable headroom; the worker's first-label
    # latency must still be << 5s because of FR-401 (no waiting on lookahead).
    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=50, latency_s=0.3),
    )

    app = create_app()  # one app, reused across trials — perf test target is
                        # the worker, not app-startup cost
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Lifespan startup is required so app.state.{batches,buses} are init'd
        async with app.router.lifespan_context(app):
            samples_s: list[float] = []
            event_counts: list[tuple[int, int]] = []  # (label_results, stream_ends)
            for trial in range(32):  # 2 warmup + 30 measure
                bid = f"B-perf-{trial:03d}"
                envelope = BatchEnvelope(
                    batch_id=bid,
                    agent_id="a",
                    submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
                    items=tuple(
                        BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                        for i in range(50)
                    ),
                ).model_dump(mode="json")
                t0 = time.perf_counter()
                await client.post("/batches", json=envelope)
                first_event_t = None
                lr = se = 0
                async with client.stream("GET", f"/batches/{bid}/stream") as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("event: label-result"):
                            if first_event_t is None:
                                first_event_t = time.perf_counter() - t0
                            lr += 1
                        elif line.startswith("event: stream-end"):
                            se += 1
                            break
                assert first_event_t is not None
                if trial >= 2:  # drop warmup
                    samples_s.append(first_event_t)
                event_counts.append((lr, se))

    # AC #2 — every trial saw 50 label-result events + 1 stream-end (anomaly
    # advisories may add to lr but not stream-end; with FakeEvaluator emitting
    # heterogeneous reason_codes the anomaly detector should not fire).
    for lr, se in event_counts:
        assert lr == 50, f"expected 50 label-result events per trial, got {lr}"
        assert se == 1, f"expected exactly 1 stream-end event, got {se}"

    p50 = statistics.median(samples_s)
    p99 = statistics.quantiles(samples_s, n=100)[98]
    assert p50 <= 2.7, f"P50 {p50:.3f}s exceeds 2.7s budget"
    assert p99 <= 5.0, f"P99 {p99:.3f}s exceeds 5.0s budget"
```

- [ ] **Step 2: Run focused → RED → GREEN**

`uv run pytest tests/test_batch_first_label_perf.py -v -m slow` → expected: GREEN immediately because the worker's first-label-individual is already implemented in T6 Cycle A. If RED, the failure mode is most likely lookahead-pre-fetch blocking item 0 (Rule 1-3 fix in worker).

- [ ] **Step 3: Commit**

```bash
git add tests/test_batch_first_label_perf.py
git commit -m "test(e6): AC-FR-401 perf canary — first-label P50/P99 under NFR-PERF-001 budget"
```

---

## Task 10: tests/test_batch_integration_smoke.py — 5-item batch end-to-end (L1 §5 canary)

**Files:**
- Test: `tests/test_batch_integration_smoke.py`

Wave 5 parallel. Depends on T7 + T8 (full surface). The L1 §5 canary — closest thing to a smoke test for the whole epoch.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_batch_integration_smoke.py
"""L1 §5 canary: 5-item batch with fake evaluator, real SSE response, drains
events, asserts 5 per-label + stream-end + (no advisories), connection closes."""
import asyncio
from datetime import datetime, timezone

import httpx
import pytest


@pytest.mark.asyncio
async def test_5_item_batch_end_to_end_via_real_sse_response(monkeypatch):
    from app.main import create_app
    from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
    from tests.conftest import _fake_evaluator

    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=5, latency_s=0.3),
    )
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        envelope = BatchEnvelope(
            batch_id="B-canary-001",
            agent_id="a",
            submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
            items=tuple(
                BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                for i in range(5)
            ),
        ).model_dump(mode="json")
        post_resp = await client.post("/batches", json=envelope)
        assert post_resp.status_code == 202

        events: list[str] = []
        async with client.stream("GET", "/batches/B-canary-001/stream") as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())
                if "stream-end" in line:
                    break

        assert events.count("label-result") == 5
        assert events.count("anomaly-advisory") == 0  # no anomaly with 5 distinct
        assert events.count("stream-end") == 1
        assert events[-1] == "stream-end"


@pytest.mark.asyncio
async def test_5_item_batch_with_mid_batch_override_continues_to_completion(monkeypatch):
    """FR-404 end-to-end: override during mid-batch does not stop the worker."""
    from app.main import create_app
    from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
    from tests.conftest import _fake_evaluator, _stub_disposition_envelope

    plan = [(0.1, _stub_disposition_envelope(i, disposition="needs_review")) for i in range(5)]
    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(plan=plan),
    )
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        envelope = BatchEnvelope(
            batch_id="B-canary-002",
            agent_id="a",
            submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
            items=tuple(
                BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                for i in range(5)
            ),
        ).model_dump(mode="json")
        await client.post("/batches", json=envelope)

        events: list[dict] = []

        async def _drain():
            async with client.stream("GET", "/batches/B-canary-002/stream") as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("event:"):
                        events.append({"event": line.split(":", 1)[1].strip()})
                    if "stream-end" in line:
                        break

        # Run draining + override concurrently
        drain_task = asyncio.create_task(_drain())
        await asyncio.sleep(0.15)  # let item 0 land

        override_resp = await client.post(
            "/labels/EV-0000/overrides",
            json={
                "reason_code": "BRAND.NAME.NEEDS_REVIEW",
                "applied_disposition": "pass",
                "justification_text": "Mid-batch override",
            },
        )
        assert override_resp.status_code == 200

        await asyncio.wait_for(drain_task, timeout=5.0)

    label_count = sum(1 for e in events if e["event"] == "label-result")
    end_count = sum(1 for e in events if e["event"] == "stream-end")
    override_count = sum(1 for e in events if e["event"] == "override-applied")
    assert label_count == 5  # all items processed despite mid-batch override
    assert end_count == 1
    assert override_count == 1
```

- [ ] **Step 2: Run focused → GREEN**

`uv run pytest tests/test_batch_integration_smoke.py -v` → 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_batch_integration_smoke.py
git commit -m "test(e6): L1 §5 canary — 5-item batch end-to-end + mid-batch override (FR-404)"
```

---

## Task 11: tests/test_batch_eviction.py — lifespan teardown (NFR-DATA-001/002, AC #11)

**Files:**
- Test: `tests/test_batch_eviction.py`

Wave 5 parallel. Depends on T7 (lifespan hook).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_batch_eviction.py
"""NFR-DATA-001/002: app.state.batches evicted on lifespan teardown."""
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_lifespan_teardown_clears_app_state_batches():
    from app.main import create_app
    from app.batch.state import InFlightBatch
    from app.api._sse_bus import SSEBus
    from app.schemas.batch import BatchItem, ItemState

    app = create_app()
    # Manually trigger lifespan startup
    async with app.router.lifespan_context(app):
        item = BatchItem(
            label_id="lbl-0",
            application_ref="app-0000",
            state=ItemState.QUEUED,
            result=None,
            enqueued_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
        )
        in_flight = InFlightBatch(batch_id="B-EV", agent_id="a", items=(item,), lookahead_k=3)
        app.state.batches["B-EV"] = in_flight
        app.state.buses["B-EV"] = SSEBus()
        assert app.state.batches  # populated during lifespan-active
        assert app.state.buses

    # Lifespan exited — both registries should be cleared
    assert app.state.batches == {}
    assert app.state.buses == {}
```

- [ ] **Step 2: Run focused → GREEN**

`uv run pytest tests/test_batch_eviction.py -v` → 1 passed (T7 already wired the teardown clear).

- [ ] **Step 3: Commit**

```bash
git add tests/test_batch_eviction.py
git commit -m "test(e6): NFR-DATA-001/002 lifespan teardown evicts in-flight batches (AC #11)"
```

---

## Task 12: tests/test_lookahead_k_env_override.py — LOOKAHEAD_K=2/4 (AC #10)

**Files:**
- Test: `tests/test_lookahead_k_env_override.py`

Wave 5 parallel. Depends on T7 (`_resolve_lookahead_k`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lookahead_k_env_override.py
"""AC #10: LOOKAHEAD_K=2 reduces lookahead to 2; LOOKAHEAD_K=4 increases to 4."""
import asyncio
from datetime import datetime, timezone

import httpx
import pytest


@pytest.mark.parametrize("k_value", [2, 4])
@pytest.mark.asyncio
async def test_lookahead_k_env_var_overrides_default_3(k_value, monkeypatch):
    from app.main import create_app
    from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
    from tests.conftest import _fake_evaluator

    monkeypatch.setenv("LOOKAHEAD_K", str(k_value))
    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=10, latency_s=0.5),
    )

    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        envelope = BatchEnvelope(
            batch_id=f"B-LA-{k_value}",
            agent_id="a",
            submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
            items=tuple(
                BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                for i in range(10)
            ),
        ).model_dump(mode="json")
        await client.post("/batches", json=envelope)
        # Inspect the in-flight batch directly
        in_flight = app.state.batches[f"B-LA-{k_value}"]
        assert in_flight.lookahead_k == k_value
        assert in_flight.queue.maxsize == k_value + 1


@pytest.mark.asyncio
async def test_lookahead_k_default_is_3_when_env_absent(monkeypatch):
    from app.main import create_app
    from app.schemas.wire.batch import BatchEnvelope, BatchItemRef
    from tests.conftest import _fake_evaluator

    monkeypatch.delenv("LOOKAHEAD_K", raising=False)
    monkeypatch.setattr(
        "app.deps.build_evaluator",
        lambda settings: _fake_evaluator(n_items=3, latency_s=0.1),
    )
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        envelope = BatchEnvelope(
            batch_id="B-LA-default",
            agent_id="a",
            submitted_at=datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc),
            items=tuple(
                BatchItemRef(label_ref=f"lbl-{i}", application_ref=f"app-{i:04d}")
                for i in range(3)
            ),
        ).model_dump(mode="json")
        await client.post("/batches", json=envelope)
        in_flight = app.state.batches["B-LA-default"]
        assert in_flight.lookahead_k == 3
        assert in_flight.queue.maxsize == 4
```

- [ ] **Step 2: Run focused → GREEN**

`uv run pytest tests/test_lookahead_k_env_override.py -v` → 3 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_lookahead_k_env_override.py
git commit -m "test(e6): LOOKAHEAD_K env-override AC #10 (k=2, k=4, default=3)"
```

---

## Final integration check

After T12 lands:

- [ ] Run: `uv run pytest -q -m "not slow"` — all green (target ~525 tests; +43 from E6 across T0-T12; xfail count unchanged at 3).
- [ ] Run: `uv run pytest tests/test_batch_integration_smoke.py tests/test_batch_eviction.py tests/test_lookahead_k_env_override.py -v -s`.
- [ ] Run: `uv run pytest -m slow tests/test_batch_first_label_perf.py -v` — verify perf canary holds.
- [ ] Verify SSE wire shape: `uv run python -c "from fastapi.testclient import TestClient; from app.main import create_app; client=TestClient(create_app()); print(client.get('/batches/X/stream').status_code)"` — expect 404 (unknown batch_id).
- [ ] Verify FR-404 grep guard: `grep -nE '\.overrides' app/batch/worker.py` — empty.

---

## Self-review

**Spec coverage** — checked L1 §1 through §9 against tasks. All 11 exit-gate items have a task: AC #1 (POST 202) → T7; AC #2 (event count = 50+N+1) → T9 indirectly + T10 smoke (5-item proxy); AC #3 (FR-401 first-label perf) → T9; AC #4 (FR-402 lookahead inspection) → T6 Cycle B; AC #5 (FR-403 saturation) → T6 Cycle B; AC #6 (FR-404 mid-batch override) → T6 Cycle C + T10 smoke; AC #7 (FR-405 anomaly) → T3 unit + T6 Cycle C; AC #8 (FR-801 fields + SSE surface) → T8; AC #9 (1-s disconnect cleanup) → T7 SSE test; AC #10 (LOOKAHEAD_K env) → T12; AC #11 (lifespan eviction) → T11.

**Wave 0 coverage** — T0 (`OverrideEntry.field_name` Optional) covers L1 §2.6 whole-envelope override expressibility; T2 (`BoundedQueue`) is a Wave 0 root because T1 imports it (substitutability seam preserved per L1 §2.3 / ARCH §4.2.7). No `PerRuleTraceEntry` schema extension is required — `_headline_reason_code` reads `RuleFindingWire.reason_code` from `envelope.fields[]` (existing schema) with a fallback to `per_rule_trace[0].rule_id`.

**Placeholder scan** — every code block is concrete. No "TBD"/"TODO"/"implement later". `_resolve_application` and `_resolve_label` synthesize minimal schema-conforming instances from the `BatchItem` refs — that is the MVP wiring, not a stub (see Cycle A note for the production-trajectory rationale).

**Type consistency** — `InFlightBatch` shape consistent across T1, T6, T7, T8, T11. `FakeEvaluator.evaluate(application, label) -> DispositionEnvelope` matches `Evaluator.evaluate` signature exactly. `OverrideEntry(field_name=..., original_disposition=..., applied_disposition=..., reason_code=..., justification_text=..., reviewer_id=..., timestamp=...)` consistent across T0, T8 (write) and T6 Cycle C, T8 (read).

**Wave-structure note** — T7 and T8 both modify `app/main.py` — sequential per E5's T15/T17 pattern. T9-T12 are pure tests in parallel after T8; file-ownership disjoint. T6 Cycle A/B/C are sequential because the file is shared.

**FR-303 isolation** — N/A for E6 (E5 owns the FR-303 chokepoint). E6 must NOT inspect or mutate `result.audit_trail` outside the override endpoint — encoded as the `test_worker_does_not_inspect_overrides` grep guard.

**Override registry validation** — registry-loaded once at module import (T8); verbatim-equality check; mirror E5 T18-UNBLOCK pattern. Test asserts a bogus code yields 400.

**Empty-batch / single-item case** — single-item is exercised in T6 Cycle A. Empty-batch (zero items) is not directly tested; the worker's `for queue_position in range(0)` loop simply does not iterate, and the producer also does not iterate, so `stream-end` fires immediately. Acceptable for prototype scale.

**Rule 1-3 budget** — Wave 1 has 4 parallel tasks (executor cap is 6) — comfortable margin for inline fixups. Wave 2 has the worker (3 cycles) — single-task wave with no parallelism concern.

---

## L1 → Task Coverage Map

| L1 Requirement | Status | Task / Notes |
|---|---|---|
| FR-401 (first-label-individual under NFR-PERF-001) | Covered | T6 Cycle A (`test_worker_first_label_individual_does_not_wait_for_lookahead_window`); T9 perf canary (P50/P99 across 30 trials). |
| FR-402 (lookahead k=3 default) | Covered | T6 Cycle B (`test_worker_lookahead_k_3_pre_fetches_next_two_items_while_one_processes`); T12 env override exercises k=2/k=4. |
| FR-403 (pull-based demand via maxsize=k+1) | Covered | T2 (`BoundedQueue.saturated` invariant); T6 Cycle B (`test_worker_queue_saturates_at_lookahead_plus_one_when_consumer_holds`). |
| FR-404 (mid-batch override does not stop worker) | Covered | T6 Cycle C (positive `test_worker_continues_after_in_flight_results_mutation_simulating_override` + negative `test_worker_does_not_inspect_overrides_on_results` grep guard); T10 smoke end-to-end. |
| FR-405 (M-of-N=5-of-10 anomaly advisory) | Covered | T3 unit (`AnomalyDetector` 9 cases); T6 Cycle C (`test_worker_emits_anomaly_advisory_on_5_of_10_same_reason_code`). |
| FR-800 (override endpoint exists) | Covered | T8 endpoint test. |
| FR-801 (audit fields all present) | Covered | T8 audit-trail test (`test_override_lands_on_in_flight_results_audit_trail_overrides_tuple`). |
| FR-802 (server-generated reviewer_id) | Covered | T8 endpoint test asserts `reviewer_id.startswith("session-")`. |
| FR-803 (reason_code validated against registry) | Covered | T8 endpoint test (`test_post_override_rejects_unknown_reason_code` returns 400). |
| FR-804 (justification optional) | Covered | T8 endpoint test omits `justification_text`; defaults to None per E1 schema; backwards-compat asserted by T0. |
| NFR-PERF-001 (5 s SLA against batch envelope) | Covered | T9 perf canary (P50 ≤ 2.7 s, P99 ≤ 5.0 s). |
| NFR-DATA-001 / NFR-DATA-002 (no persistence) | Covered | T11 lifespan eviction test; T7 wires `app.state.batches.clear()` in lifespan shutdown. |
| L1 §4 AC #1 (POST 202 + batch_id) | Covered | T7 (`test_post_batches_returns_202_and_batch_id`). |
| L1 §4 AC #2 (50 + N + 1 SSE events) | Covered | T9 perf (50 items end-to-end); T10 smoke (5 items, exact event count). |
| L1 §4 AC #3 (FR-401 perf gate) | Covered | T9. |
| L1 §4 AC #4 (FR-402 inspection) | Covered | T6 Cycle B. |
| L1 §4 AC #5 (FR-403 inspection) | Covered | T6 Cycle B. |
| L1 §4 AC #6 (FR-404) | Covered | T6 Cycle C + T10. |
| L1 §4 AC #7 (FR-405) | Covered | T3 + T6 Cycle C. |
| L1 §4 AC #8 (override fields + SSE) | Covered | T8. |
| L1 §4 AC #9 (1-s disconnect cleanup) | Covered | T7 (`test_sse_subscriber_pruned_within_1s_on_client_disconnect`). |
| L1 §4 AC #10 (LOOKAHEAD_K env) | Covered | T12. |
| L1 §4 AC #11 (eviction on session end) | Covered | T11. |
| D-004 (substitutability — `BatchInFlightState` shape preserved for Kafka/RabbitMQ swap) | Covered | T1 (`InFlightBatch.snapshot()` returns the exact frozen `BatchInFlightState` shape from E1; mutable companion intentionally kept private to E6). |
| D-018 (audit/metrics split — overrides ride audit) | Covered | T8 mutates `audit_trail.overrides`; never `metrics`. |

---

## Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-04 | Project team | Initial E6 L2 plan. 13 tasks across 6 waves; bottlenecked on T6 worker (3 cycles, single file). Wave 0: T0 (additive `OverrideEntry.field_name = None`). Wave 1 parallel-5: T1-T5 (state, queue, anomaly, sse_bus, fakes). Wave 2 single 3-cycle: T6 worker. Wave 3 single: T7 batches endpoint. Wave 4 single: T8 overrides endpoint. Wave 5 parallel-4: T9 perf, T10 smoke, T11 eviction, T12 LOOKAHEAD_K. Wave 6 run-only check. Total tasks: 13; total waves: 6; max parallelism: 5 (Wave 1); expected commits: ~17 (13 base + 2 extra T6 cycles + 2 Rule 1-3 margin). Known iter-1 BLOCK candidate flagged inline: `PerRuleTraceEntry.reason_code` does not exist on the E1 schema and the worker's `_headline_reason_code` reads from it; reviewer-driven Wave 0 expansion (T0b) likely. |
| 0.2 | 2026-05-04 | Plan-review iter 1 | **Structural fixes (4):** (1) `_stub_disposition_envelope.Metrics(...)` constructor used non-existent `evaluation_id` and `per_rule_durations` (dict) — corrected to actual schema (`total_duration_ms`, `per_rule_durations_ms` tuple, `vision_duration_ms`, `orchestrator_duration_ms`); (2) T7 imported `get_settings` from `app.deps` (does not exist) — replaced with module-private `_get_settings` factory mirroring E5's healthz/labels pattern; (3) T3 broken anomaly test (alternating A/B that fires by observation 9 contradicting its `assert adv is None`) replaced with a heterogeneous-batch test (4 As + 4 Bs + 2 Cs, no code reaches threshold). **Architectural fixes (5):** (4) `BatchWorker.run()` `await producer_task` in `finally` would deadlock on consumer exception — added `producer_task.cancel(); await asyncio.gather(..., return_exceptions=True)`; (5) `BoundedQueue` was dead code (T1 constructed bare `asyncio.Queue` directly) — wired `InFlightBatch.queue: BoundedQueue[BatchItem]` so the substitutability seam (L1 §2.3 / ARCH §4.2.7) is real; T2 moved to Wave 0 since T1 now depends on it; (6) Dropped dead `InFlightBatch.subscribers` field (duplicate of `SSEBus.subscribers`); (7) Replaced T7 retro-bolt of `bus` field on `InFlightBatch` with separate `app.state.buses: dict[str, SSEBus]` registry — same lifecycle, no circular-import risk, no dataclass mutation; (8) Made `_load_accepted_reason_codes` lazy + loud (no module-import side effect; missing registry now raises `FileNotFoundError` rather than silently returning an empty frozenset). **Cleanups:** dropped the spurious `PerRuleTraceEntry.reason_code` Wave 0-expansion warning (the helper reads `rule_id` from existing schema with a fallback to `RuleFindingWire.reason_code` — no extension needed); double-call of `_headline_reason_code(envelope)` collapsed to a single bind; override endpoint contract for "queued-not-yet-evaluated" labels documented (returns 404 by design — UI guards via SSE `label-result` event before enabling the override button); T7 lifespan teardown clears both `app.state.batches` and `app.state.buses`. **Wave restructure:** Wave 0 grows from `[T0]` to `[T0, T2]` (parallel-2); Wave 1 shrinks from `[T1, T2, T3, T4, T5]` to `[T1, T3, T4, T5]` (parallel-4). Total waves now 7. Critical path unchanged (T2 → T1 → T6 → T7 → T8 → T10 = 6 hops). |

---

## Dependency Graph

### Task Dependencies

| Task | Depends On | Blocks | Files Owned |
|------|-----------|--------|-------------|
| T0: OverrideEntry.field_name Optional | — | T8 | `app/schemas/audit.py` (additive), `tests/test_override_entry_field_name_optional.py` |
| T2: BoundedQueue | — | T1, T6, T12 | `app/batch/queue.py`, `tests/test_bounded_queue.py` |
| T1: InFlightBatch | T2 | T6 (all cycles), T7, T8, T11, T12 | `app/batch/__init__.py`, `app/batch/state.py`, `tests/test_in_flight_batch.py` |
| T3: AnomalyDetector | — | T6 (Cycle C) | `app/batch/anomaly.py`, `tests/test_anomaly_detector.py` |
| T4: SSEBus | — | T6, T7 | `app/api/_sse_bus.py`, `tests/test_sse_bus.py` |
| T5: FakeEvaluator + conftest helpers | — | T6, T7, T8, T9, T10, T12 | `tests/_fakes/evaluator.py`, `tests/conftest.py` (append), `tests/test_fake_evaluator.py` |
| T6: BatchWorker (3 cycles A/B/C) | T1, T2, T3, T4, T5 | T7, T9, T10 | `app/batch/worker.py`, `tests/test_batch_worker_skeleton.py`, `tests/test_batch_worker_lookahead.py`, `tests/test_batch_worker_anomaly_override.py` |
| T7: POST /batches + GET stream + GET snapshot | T6 | T8, T9, T10, T11, T12 | `app/api/batches.py`, `app/main.py` (additive register + `app.state.batches` and `app.state.buses` lifespan state), `tests/test_batch_endpoint_post.py`, `tests/test_batch_endpoint_sse.py` |
| T8: POST /labels/{id}/overrides | T0, T7 | T10 (mid-batch override smoke) | `app/api/overrides.py`, `app/main.py` (additive append), `tests/test_override_endpoint.py`, `tests/test_override_audit_trail.py` |
| T9: First-label perf canary | T7 | — | `tests/test_batch_first_label_perf.py` |
| T10: Smoke integration | T7, T8 | — | `tests/test_batch_integration_smoke.py` |
| T11: Lifespan eviction | T7 | — | `tests/test_batch_eviction.py` |
| T12: LOOKAHEAD_K env override | T7 | — | `tests/test_lookahead_k_env_override.py` |

### Shared Files

- `app/main.py` — modified by T7 (writes batches.router include + `app.state.batches` and `app.state.buses` lifespan state) AND T8 (appends overrides.router include). Sequential per E5's T15/T17 pattern.
- `tests/conftest.py` — modified by T5 only (additive append).

### Execution Waves

```
Wave 0 (parallel, 2):  [T0, T2]                ← OverrideEntry.field_name + BoundedQueue (both no-dep roots; T1 imports T2)
Wave 1 (parallel, 4):  [T1, T3, T4, T5]        ← state (deps T2), anomaly, sse_bus, fakes
Wave 2 (single, 3c):   [T6]                    ← BatchWorker (3 cycles A/B/C)
Wave 3 (single):       [T7]                    ← POST /batches + GET stream + lifespan state (`batches` + `buses` dicts)
Wave 4 (single):       [T8]                    ← POST /labels/{id}/overrides + main.py append
Wave 5 (parallel, 4):  [T9, T10, T11, T12]     ← perf, smoke, eviction, LOOKAHEAD_K
Wave 6 (run-only):     [final integration check]
```

**Resolved wave plan (final):**

- Wave 0 (parallel, 2): T0, T2
- Wave 1 (parallel, 4): T1, T3, T4, T5
- Wave 2 (single, 3-cycle bundle): T6
- Wave 3 (single): T7
- Wave 4 (single): T8
- Wave 5 (parallel, 4): T9, T10, T11, T12
- Wave 6 (run-only): final integration check

**Total expected new commits on `main`:** ~15 (T0+T2+T1+T3+T4+T5+T6(A,B,C)+T7+T8+T9+T10+T11+T12 = 13 task commits + 2 extra from T6's 3 cycles − 1 already counted = 15 minimum + small margin for inline Rule 1-3 fixes).

**Critical path (longest dependency chain):** T2 → T1 → T6 (3 cycles) → T7 → T8 → T10. **6 wave hops** (counting sub-cycle boundaries within Wave 2, the realized critical-path latency is 8 commit slots). T6's 3 cycles dominate the critical path because they're file-serialized.

**Parallelism factor.** 13 tasks across 7 waves → effective parallelism ≈ 1.9× vs strict serial. Wave 1 holds 4 concurrent; Wave 5 holds 4; Wave 0 holds 2.

**Pre-flight invariant** (parallel-plan-executor enforces): for each (sub-)wave, the union of file-ownership sets is strict-disjoint. Verified above in §Shared Files.

### Execution Strategy

> **For Claude:** Use `parallel-plan-executor` to execute this plan. The executor dispatches every task in a wave concurrently (up to 6 at a time) and holds a barrier between waves. Each task runs as an isolated subagent with the `task-executor` skill body injected for TDD enforcement.

- **Wave 0** — Dispatch [T0, T2] concurrently (2 subagents). Barrier. Verify 2 commits.
- **Wave 1** — Dispatch [T1, T3, T4, T5] concurrently (4 subagents). Barrier. Verify 4 commits.
- **Wave 2** — Dispatch [T6] alone (3-cycle bundle inside one subagent). Barrier. Verify 3 commits.
- **Wave 3** — Dispatch [T7] alone. Barrier. Verify 1 commit.
- **Wave 4** — Dispatch [T8] alone. Barrier. Verify 1 commit.
- **Wave 5** — Dispatch [T9, T10, T11, T12] concurrently (4 subagents). Barrier. Verify 4 commits.
- **Wave 6** — Run-only final integration check (no commits unless cleanup needed).

**Total commits expected:** 15 (sum of per-wave verifications above). Margin for inline Rule 1-3 fixes: +1-2.
