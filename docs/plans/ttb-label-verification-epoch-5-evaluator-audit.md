# Epoch 5 — Application Service + Audit + Single-Label Flow

> **Parent:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **Tier:** L1 (epoch-level).
> **Substitutability seam owned:** none — but this is where the three E2/E3/E4 seams **compose**, and where P4 (honest failure modes) is **structurally enforced**.
> **Depends on:** **E2** (rule engine + reason-code registry), **E3** (vision seam), **E4** (orchestrator seam).

---

## 1. Goal

Wire the Application Service that orchestrates a single end-to-end evaluation: vision → rule engine → conditional orchestrator → audit assembly → wire envelope. After E5, `POST /labels` accepts a PRD §6.1 application + multipart label, returns a wire-conforming PRD §6.2 disposition envelope within the 5-second SLA, and the FR-900 series engine-failure taxonomy is comprehensively emitted by the right components in the right circumstances.

This is the **chokepoint epoch**. Every architecture principle (P1–P5) is enforced here:

- **P1 / FR-303** — orchestrator results are tagged to specific `ValidationResult`s and never override `fail` to `pass`.
- **P4** — engine failures route to `needs_review` with structured reason codes; no silent default-pass anywhere.
- **D-017** — disposition-level confidence is `min` over per-field confidences.
- **D-018** — audit and metrics blocks are split; assembled from one `EngineMeta` source.

After E5, single-label review works end-to-end against fixture-01 with cloud vision and orchestrator and lands inside the time budget.

---

## 2. Components delivered

### 2.1 Application Service (`app/services/evaluator.py`)

Per ARCH §4.2.2:

- `Evaluator.evaluate(application: Application, label: Label) -> DispositionEnvelope` — async; orchestrates the full flow.
- Inside the evaluator's call frame:
  1. Asks the Vision Extractor for `list[FieldObservation]`.
  2. If the vision layer returned `disposition=needs_better_photo`, short-circuits to a `needs_review` envelope with the legibility reason code.
  3. Constructs `list[ExpectedValue]` from `application` (per-field constructors per ARCH §6.3).
  4. Calls the Rule Engine — gets `list[ValidationResult]`.
  5. Inspects results for orchestrator triggers (FR-300/301/302 conditions); if any trigger fires, calls the Orchestrator with the trigger context. **Else skips the orchestrator entirely** (the design target per ARCH §11.1: most happy-path evaluations don't invoke it).
  6. Patches `ValidationResult`s with orchestrator outputs **without changing dispositions** (FR-303 invariant — patches are limited to `message`, `aggregated_confidence`, `evidence` annotations).
  7. Computes disposition (`pass` iff all `ValidationResult.outcome == pass`; `fail` iff any is `fail`; `needs_review` otherwise — the §10.3 honest-failure-mode invariant).
  8. Aggregates confidence per D-017: `disposition_confidence.numeric = min(field.field_confidence.numeric for field in fields)`.
  9. Calls the Audit Recorder.
  10. Assembles the PRD §6.2 envelope (with sibling `metrics` block per D-018).
- Per-rule timeout (250 ms, S5 §13) wraps each validator call.
- Whole-evaluation timeout (5 s SLA, NFR-PERF-001) is enforced via `asyncio.wait_for` on the whole `evaluate()` call; on exhaustion emits `ENGINE.SLA.TIMEOUT` (FR-909) and returns whatever partial `ValidationResult`s have been computed (Dean & Barroso tail-tolerant pattern, ARCH §11.4).
- Catches every downstream exception and routes to the right FR-900-series reason code; **never re-raises to the Web layer** except for genuine programmer-error bugs.
- Holds no per-evaluation state beyond the call frame.

### 2.2 Audit Recorder (`app/services/audit.py`)

Per ARCH §4.2.8:

- `AuditRecorder.assemble(...) -> AuditRecord` — pure assembly; no I/O.
- Builds `AuditRecord` per ARCH §6.8: `evaluation_id`, `rule_set_version`, `model_version`, `prompt_version`, `input_hash`, `output_hash`, `started_at`, `completed_at`, `per_rule_trace=[{rule_id, disposition, evidence_ref}]`, `overrides=[]` (populated later by E6 override endpoint).
- Computes `input_hash = sha256(canonicalized application JSON + image bytes)` per ARCH §6.7 / §6.8.
- Computes `output_hash = sha256(canonicalized disposition envelope)` after assembly.
- Per D-018 — does **not** populate `per_rule_trace[].duration_ms`; that lives on `Metrics`.

### 2.3 Metrics builder (`app/services/metrics.py`)

Per D-018:

- `MetricsBuilder.build(engine_meta: EngineMeta) -> Metrics` with `total_duration_ms`, `per_rule_durations_ms[]`, `vision_duration_ms`, `orchestrator_duration_ms`.
- The Web layer (and the disposition envelope) carries both `audit_trail` and sibling `metrics` blocks; both come from the same `EngineMeta` source.

### 2.4 Single-label endpoint (`app/api/labels.py`)

- `POST /labels` per ARCH §3.2 — accepts multipart with a JSON envelope part (PRD §6.1) plus the label image part.
- Validates the JSON via Pydantic v2 strict-mode (NFR-SEC-003); validates the image via content-type sniff + magic-byte check (FR-101 / FR-102 / FR-600 / FR-601).
- Calls `Evaluator.evaluate()`; returns the disposition envelope as JSON 200.
- On invalid input: returns PRD §6.4 `rejected_input` 400 with structured reason code.
- On `Evaluator` returning a `needs_review` envelope from any FR-900-series cause: returns 200 with the envelope (the disposition is `needs_review`, not an HTTP error — engine failures are handled inside the envelope, not as HTTP failures).

### 2.5 Full `/healthz` warm-up (`app/api/healthz.py` upgraded from E1 stub)

Per `PRD-deferred-content.md` §3.1 / ARCH §5.3:

- On first invocation, runs `VisionExtractor.ensure_loaded()`, `RuleLoader.load()` (already done at startup; this is a no-op verification), `Orchestrator.ensure_client()`.
- Then runs the **full extraction → rule-engine → orchestrator pipeline against fixture-01** as a sentinel.
- Returns 200 within 2 seconds on a warm system; cold-start latency on the GPU profile is ~30–45 s (acceptable per D-016 consequences) — the demo runbook calls `/healthz` at T-5 minutes.

### 2.6 Raw-JSON ring-buffer endpoint (`app/api/raw.py` — DEV_MODE-gated)

Per ARCH §3.2 / D-019:

- `GET /batches/{batch_id}/labels/{label_id}/calls` — returns the per-batch `CallRecord` ring-buffer entries; gated by `DEV_MODE` (per ADR D-019).
- For E5, the endpoint is implemented but only reachable through a single-label batch envelope that the test infrastructure constructs; the full batch routing comes in E6.
- Recommend: introduce `app.state.calls: dict[str, deque[CallRecord]]` keyed by `evaluation_id` for E5; E6 reuses the same shape under `app.state.batches[batch_id].calls`.

### 2.7 Test surface

- `tests/test_evaluator_single_label.py` — end-to-end test: fixture-01 application + label → wire-conforming PRD §6.2 envelope; disposition `pass`; all 7 fields present; min-aggregated confidence is correct; metrics block populated; audit-trail block populated.
- `tests/test_evaluator_orchestrator_trigger.py` — fixture-02 STONE'S THROW: rule engine emits `pass` at Stage A normalization → orchestrator is **not** invoked → ring buffer has no orchestrator records (the design target).
- `tests/test_evaluator_orchestrator_invoked.py` — synthetic borderline brand-match case where Stage B emits `needs_review` → orchestrator is invoked exactly once for `brand_disambig`; ring buffer has 1 orchestrator record with the expected `prompt_version`.
- `tests/test_evaluator_failure_modes.py` — **full FR-900 series coverage**:
  - FR-900 missing application → `rejected_input` 400 (Web layer).
  - FR-901 missing label image → `rejected_input` 400 (Web layer).
  - FR-902 conflicting rules at runtime → `needs_review` per affected fields, others continue.
  - FR-903 ambiguous OCR → `needs_review` for that field.
  - FR-904 unknown class → `fail` on class field, `needs_review` whole eval.
  - FR-905 class disagreement → `needs_review`.
  - FR-906 ruleset version mismatch → loader-time failure; refusal to start (asserted via subprocess).
  - FR-907 validator exception → `needs_review` for that rule, others continue.
  - FR-908 per-rule timeout → `needs_review` for that rule, others continue.
  - FR-909 whole-eval timeout → `needs_review` whole eval; partial results returned.
  - FR-910 missing DPI → `needs_review` for affected rules; non-DPI rules unaffected.
  - FR-911 reference data unavailable → `needs_review`.
  - FR-912 model unavailable → `needs_review` for orchestrator-borderline rules, deterministic rules unaffected.
- `tests/test_audit_trail.py` — every audit-trail field per ARCH §6.8 / FR-703 / NFR-AUDIT-001 is present; `per_rule_trace[].duration_ms` is **absent** (D-018); `metrics.per_rule_durations_ms[]` is present.
- `tests/test_confidence_aggregation.py` — min-aggregation per D-017; downward-only; the disposition-level `numeric` equals `min(per-field numeric)`; the `band` is mapped from the numeric per published thresholds.
- `tests/test_audit_metrics_split.py` — the disposition envelope contains both `audit_trail` and `metrics`; both blocks build from the same `EngineMeta` source (no double-bookkeeping).
- `tests/test_evaluator_timeouts.py` — per-rule and whole-eval timeout paths; partial-results return on whole-eval exhaustion.
- `tests/test_healthz_warmup.py` — `/healthz` runs the full pipeline against fixture-01 and returns 200 within the documented budget on a warm system.
- `tests/test_post_labels_endpoint.py` — `POST /labels` happy path + 400 on malformed JSON + 400 on TIFF/PDF (FR-102 / FR-601).
- `tests/test_post_labels_perf.py` — fixture-01 P50 ≤ 2.7 s, P99 ≤ 5.0 s with mocked vision + cached orchestrator; 30+ trial median + 99-percentile reporting.

---

## 3. Wire / data contracts owned by this epoch

E5 owns:

- The single-label HTTP boundary (`POST /labels`) and the multipart parsing rules.
- The pre-warm contract on `/healthz` (request → 200 within 2 s on warm; the warm-up itself runs the full pipeline against fixture-01).
- The `error_kind` discrimination at the boundary: `rejected_input` is HTTP 400 (Web layer); `engine_failure` is HTTP 200 with a `needs_review` envelope (because the engine handled it honestly); `partial_completion` is HTTP 200 with partial results (FR-909).

After E5, the wire layer for single-label review is settled. E6 only **adds** batch endpoints; it does not modify `POST /labels`.

---

## 4. Exit gate

The epoch lands when **all of these pass**:

1. `POST /labels` against `fixtures/01-spirits-clean/` returns `disposition=pass` with all 7 PRD §5.1 fields populated and a wire-conforming PRD §6.2 envelope.
2. `POST /labels` against `fixtures/03-warning-title-case/` returns `disposition=fail` with `WARNING.STYLE.HEADING_NOT_BOLD_CAPS` reason code and `27 CFR §16.22(a)(2)` citation.
3. `POST /labels` against `fixtures/04-low-res-blurry/` returns `disposition=needs_review` with a `WARNING.LEGIBILITY.*` reason code (FR-603 / FR-505).
4. `POST /labels` against `fixtures/06-abv-out-of-tolerance/` returns `disposition=fail` with `ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND` reason code and `27 CFR §5.65(c)` citation.
5. **Full FR-900 series coverage** — `tests/test_evaluator_failure_modes.py` passes for all 13 failure modes.
6. AC-FR-704 / D-017 min-aggregation passes; AC-D-018 audit/metrics split passes.
7. AC-FR-703 / NFR-AUDIT-001/002 — every audit-trail field is present; `input_hash` and `output_hash` populated; `per_rule_trace` populated.
8. **AC-NFR-PERF-001 / NFR-PERF-003** — fixture-01 P50 ≤ 2.7 s, P99 ≤ 5.0 s under demo conditions (mocked vision recordings + cached orchestrator). The L2 plan settles the exact methodology (30+ trials, deterministic warmup); this AC must hold before E5 closes.
9. `/healthz` runs the full sentinel pipeline against fixture-01 and returns 200 within 2 s on a warm system (cold-start ~30–45 s on GPU profile is acceptable). **The demo runbook's T-5-minute pre-warm contract (per `PRD-deferred-content.md` §3.1, owned by E8 `DEMO-RUNBOOK.md`) depends on this exit gate; if E5 closes without satisfying it, E8's recorded walkthrough is at risk.**
10. FR-303 invariant **at runtime**: a synthetic test where the orchestrator's `Refined` "disagrees" with a rule-engine `fail` → the disposition stays `fail`; the disagreement is recorded in audit; the disposition is unchanged.
11. `grep -rn 'raise' app/services/evaluator.py | grep -v 'NotImplementedError\|programmer'` returns no hits — the chokepoint catches everything (P4 enforcement).
12. The request → `evaluate()` → response path uses `evaluation_id` consistently (input hash, output hash, audit, metrics, log lines all share the same UUID).

---

## 5. TDD strategy

**Mockable** —

- **Vision Extractor** — via Protocol fakes that return canned `FieldObservation`s for each fixture. Avoids the entire vision stack in evaluator unit tests.
- **Orchestrator** — via ABC fakes that return canned `Refined` outputs.
- **Rule Engine** — optionally fake (for fast tests) or real (for end-to-end fixture tests). Both modes exercised.

**Real** —

- Full E2 rule engine + the actual `rules/*.yaml` for end-to-end fixture tests.
- `asyncio.wait_for` for whole-eval timeout.
- `time.monotonic` (with optional fake injection for per-rule timeout tests).

**Test layering.**

- *Pure unit tests* exercise `Evaluator.evaluate()` with all three downstream components mocked (fast; ≥ 50 cases for FR-900 series + happy paths).
- *Integration tests* exercise the full stack with vision and orchestrator returning recorded responses (a few dozen cases per demo fixture).
- *Performance tests* exercise the timing budget against pinned recordings (handful of cases, but reported with statistics).

**Performance methodology.** `tests/test_post_labels_perf.py` runs the same fixture 30 times with statistics; reports P50, P95, P99; CI threshold is the NFR-PERF-003 demo-fixture target. Recordings keep the test deterministic; the variance in numbers is dominated by Python overhead and asyncio scheduling, not LLM jitter.

---

## 6. Out of scope for this epoch

- Batch processing — **E6**.
- Override endpoint — **E6** (the audit-trail data shape supports it; the endpoint lands with batch).
- UI rendering — **E7**.
- Eval harness — **E8**.
- Cross-session caching (cache key + persistence) — out of MVP per NFR-DET-002.
- The session-only canonicalized cache (NFR-DET-001) — recommend the L2 plan implements it inside the Application Service for within-session repeat-submission idempotency, but the cache itself is small enough that whether it lands in E5 or E8 is a per-decision call. Default: lands in E5 inside `Evaluator` since it's per-evaluation state.

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The 5 s SLA is missed because of cumulative tail latencies | Medium | High | ARCH §11.1 budget breakdown: vision 1.5–2.8 s, rules 0.15–0.3 s, orchestrator 0.8–1.5 s (when invoked), web 0.17–0.45 s, ~0.5 s buffer. Per-rule + whole-eval timeouts cap the tails. AC-NFR-PERF-003 is asserted with statistics, not a single-trial worst case. |
| The orchestrator is invoked when it shouldn't be (FR-300 trigger over-fires) | Medium | Medium | Trigger condition is exactly `(rule_id == 'X.brand.present' && outcome == 'needs_review' && reason_code == 'BRAND.NAME.NEEDS_REVIEW')`; not heuristic; tested in `tests/test_evaluator_orchestrator_trigger.py` |
| The `evaluate()` chokepoint swallows a programmer-error exception that should crash | Medium | Medium | `evaluate()` distinguishes `RuleEngineError` / `VisionError` / `OrchestratorError` (caught) from generic `Exception` (not caught for programmer errors, e.g., `AttributeError`); structured assertion in `tests/test_evaluator_chokepoint.py` |
| `output_hash` instability across Python versions or JSON encoding | Low | Medium | Canonical JSON encoding via `json.dumps(..., sort_keys=True, ensure_ascii=True, separators=(',',':'))`; tested for byte-equality across two Python interpreter sessions |
| Whole-eval timeout cancellation leaves partial state | Medium | Medium | `asyncio.wait_for` raises `TimeoutError` which is caught and converted to `ENGINE.SLA.TIMEOUT`; the partial `ValidationResult`s already in hand are returned; assert the audit trail completed-at reflects the timeout, not the SLA |
| Confidence-band thresholds disagree between Application Service and per-field cards | Low | Low | The mapping `numeric → band` lives in **one** function (`app/services/confidence.py`) and is called everywhere a band is needed; tested for monotonicity and edge values (0.0, 0.5, 0.85, 0.92, 1.0) |

---

## 8. L2 hand-off notes

When E5 lands:

1. Decompose into ~10 tasks: `MetricsBuilder` → `AuditRecorder.assemble` → `Evaluator.evaluate` (the big one — split into the 10 sub-steps in §2.1 across 4–5 sub-tasks) → `app/api/labels.py` endpoint → `app/api/healthz.py` warm-up upgrade → `app/api/raw.py` (DEV_MODE-gated) → confidence.py band mapping → FR-900 series tests (parallel across the 13 failure modes).
2. **Wave structure:** confidence.py + AuditRecorder + MetricsBuilder (parallel) → Evaluator (sequential after them) → API endpoints (parallel after Evaluator) → integration + perf tests (sequential after endpoints).
3. The L2 plan **must** include a task that runs the AC-NFR-PERF-003 statistics under CI to lock the budget.
4. The L2 plan **must** include a task that runs the FR-303 runtime invariant (orchestrator disagrees with rule-engine fail; disposition stays fail).
5. The session-only canonicalized cache (NFR-DET-001) lands inside `Evaluator` as an `app.state.cache: LruCache[hash, DispositionEnvelope]` keyed by canonicalized input hash, evicted at session end.

---

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial epoch-5 L1 doc. |
