# TTB Label Verification — L1 Epoch Plan

> **Plan tier:** L1 (epoch-level slicing). Strategic, not file-level.
> Each epoch ships one independently TDD-testable slice.
> **Per-epoch L2 plans (file-level + bite-sized TDD steps) are written separately**, one at a time, *immediately before* that epoch's implementation, using `superpowers:writing-plans` + `superpowers:parallel-planning`, then dispatched via `parallel-plan-executor`. This document does NOT contain L2 task decomposition.

**Goal.** Build the TTB AI-Powered Alcohol Label Verification prototype against `docs/PRD.md` v0.4 and `docs/ARCHITECTURE.md` v0.2 — a standalone, web-deployable proof-of-concept that returns a draft disposition for a single COLA label in ≤5 s with citation-grounded reasoning, plus batch handling, override, and an audit trail. No persistence; no COLAs Online integration; no production ATO claim.

**Architecture posture.** Single-process FastAPI app with three substitutability seams (D-004): `VisionExtractor` (Protocol), `Orchestrator` (ABC), `RuleLoader` (data-shape boundary). Deterministic rule core in YAML+Pydantic; AI orchestrates but never decides pass/fail (D-002, FR-303). Session-scoped state only (NFR-DATA-001/002). Cloud mode (GPT-4o-on-crop strict:true) is the default validated path; local mode (PaddleOCR + GPT-4o tiebreaker per D-021) is the on-prem-trajectory companion gated by `--extra gpu`. Florence-2, Qwen2.5-VL, and vLLM are scoped out of MVP per D-021 — the seams remain so future re-introduction is a new module without architectural change.

**Tech stack (fixed by D-013–D-016).** Python 3.12 / FastAPI / Pydantic v2 / uv / asyncio / PyYAML / RapidFuzz / OpenAI Structured Outputs (`strict:true`) / sse-starlette / Jinja2 / React 18 + TypeScript + Vite + shadcn/ui (Radix + Tailwind) + USWDS color tokens / pnpm / pytest / axe-core (CI a11y) / HF Spaces (Docker SDK, `cpu-basic`).

**Time budgets (three distinct quantities — do not conflate).**

| Budget | What it is | Target | Owning epoch |
|---|---|---|---|
| `uv sync` time | One-time dependency installation on a fresh checkout | ≤ 90 s on cloud profile (CPU); ~2–3 min on `--extra gpu` profile | E1 |
| App boot time | `uv run task demo` → uvicorn ready to accept connections | ≤ 30 s on cloud profile; rule-pack load + Pydantic validation only | E1 |
| First `/healthz` (cold-start) | First successful sentinel pipeline run after boot — vision model load + LLM client warm | ~1 s in cloud mode; ~30–45 s on GPU profile (model resident) | E5 |
| Subsequent `/healthz` (warm) | Sentinel pipeline against fixture-01 with models resident | ≤ 2 s | E5 |
| Single-label evaluation (warm) | `POST /labels` against fixture-01 | P50 ≤ 2.7 s, P99 ≤ 5.0 s (NFR-PERF-001/003) | E5, E6, E8 |

The 30–45 s GPU cold-start is *not* the boot time — it's the first `/healthz` after boot. The demo runbook's T-5-minute pre-warm absorbs this.

---

## 1. L1 ↔ L2 ↔ L3 boundary

| Tier | Owns | Lives in |
|---|---|---|
| **L0 — Strategic** | Why we're building it; scope envelope; success metrics | `docs/BRD.md`, `docs/PRD.md` (PRD §3.4 BO→FR map) |
| **L1 — Epoch slicing** *(this doc)* | Per-epoch goals, components delivered, seam ownership, exit gates, dependencies, TDD strategy at the slice level | `docs/plans/ttb-label-verification-epochs.md` + per-epoch sub-files |
| **L2 — Tactical** | File-level task list with bite-sized TDD steps, exact code, exact paths, parallel waves | `docs/plans/2026-MM-DD-ttb-epoch-N-<name>.md` (written per-epoch right before implementation) |
| **L3 — Implementation** | In-context decisions made while coding (variable names, helper extraction, etc.) | The code; commit messages; `docs/03-decisions.md` if it raises to ADR |

**Backtracking rule** (per CLAUDE.md): if an L2 decision changes module boundaries, interfaces, or the wire contract, it raises to L1 — this document is updated and the affected per-epoch L2 is regenerated.

---

## 2. Architecture posture summary (lift, not re-derive)

The architecture is **settled** — see `docs/ARCHITECTURE.md` and `docs/03-decisions.md` D-001 through D-020. This plan does not reopen those decisions; epochs simply build against them.

Five governing principles (ARCH §2):

| # | Principle | Forbids | Enforced in epochs |
|---|---|---|---|
| **P1** | Deterministic core, AI orchestrates | LLM deciding pass/fail; AI flipping fail→pass; AI generating citations | E2 (rule core), E4 (orchestrator output schema has no `disposition` field) |
| **P2** | Substitutability at the inference seam | Hard imports of `openai`/`anthropic` outside the seam | E3, E4 (one Protocol/ABC per seam, ≥2 implementations) |
| **P3** | Rules as data | Rule logic in component code; CFR strings in Python | E2 (YAML rule pack + validator registry) |
| **P4** | Honest failure modes | Silent default-pass; swallowed exceptions; unstructured errors | E5 (full FR-900 taxonomy chokepoint in evaluator) |
| **P5** | State is session-scoped | DB connections; Redis/Celery; durable workflow primitives | E1 (no persistence libs in `pyproject.toml`); E5/E6 (in-memory state only) |

Three D-004 substitutability seams (one or more L1 epochs own each):

| Seam | Interface | Implementations shipped | Owning epoch |
|---|---|---|---|
| **Vision** (#1) | `app/vision/base.py` `VisionExtractor` Protocol | `CloudVisionExtractor` (validated default), `LocalVisionExtractor` (on-prem-trajectory companion: PaddleOCR + GPT-4o tiebreaker per D-021) | **E3** |
| **Orchestrator** (#2) | `app/orchestrator/base.py` `Orchestrator` ABC | `OpenAIStrictOrchestrator` (validated default), `AnthropicStrictOrchestrator` (skeleton) — per D-021; vLLM scoped out of MVP | **E4** |
| **Rule loader** (data-shape, MVP-substitutable) | `app/rules/loader.py` `YamlRuleLoader` | `YamlRuleLoader` (only one in MVP); RuleEngine ABC consumes the frozen `RuleSet` data shape | **E2** |

---

## 3. Epochs at a glance

| # | Name | Primary owns | Substitutability seam | Depends on | Exit gate (epoch-level AC) |
|---|---|---|---|---|---|
| **E1** | Foundation & boot | `pyproject.toml`, `app/main.py`, `app/config.py`, `app/deps.py`, `app/schemas/*`, `app/logging/*`, `/healthz` stub, base test infra | — (DI shape only) | — | `uv run task demo` boots; `/healthz` returns 200; PRD §6.1/§6.2/§6.3/§6.4 schemas round-trip; structured-log JSON line emits with required cross-cutting fields |
| **E2** | Rule Engine + rule pack | `app/rules/*` (loader, engine, models, brand_match, _validators/), `rules/*.yaml`, `assets/warnings/govt_warning_16_21.txt`, `rules/reason_codes.yaml`, `rules/tables/cpi_16_22_a_4.yaml` | RuleLoader (data-shape) | E1 schemas | RuleLoader fail-closes on every S5 §d violation; every PRD FR-200/210/220/230 series rule passes its positive AC and fails its canonical negative AC with the correct `reason_code` + CFR citation; brand-match Stage A normalizes STONE'S THROW; per-rule timeout and whole-evaluation timeout enforce |
| **E3** | Vision Extractor seam | `app/vision/*` (base, cloud, local + helpers) | **D-004 #1** | E1 schemas (FieldObservation, Evidence) | `VisionExtractor` Protocol declared in `app/vision/base.py`; both concrete impls implement it; `tests/test_vision_substitutability.py` asserts both satisfy the Protocol; cloud impl extracts FR-001–008 fields against canned multipart JPEG/PNG fixtures; BRISQUE/NIQE quality gates emit `WARNING.LEGIBILITY.*` reason codes; local impl is import-clean under `--extra gpu` and protocol-conformant under mock |
| **E4** | AI Orchestrator seam | `app/orchestrator/*` (base, openai_strict, anthropic_strict, tasks/) | **D-004 #2** | E1 schemas | `Orchestrator` ABC + 2 concrete impls (per D-021: OpenAI default + Anthropic skeleton); substitutability test passes for both; FR-303 invariant: structured output schema contains no `pass | fail` field (asserted by introspection); FR-304 fallback: simulated LLM outage returns `needs_review` with `ENGINE.MODEL.UNAVAILABLE`; ring-buffer `CallRecord` populated per call |
| **E5** | Application Service + Audit + single-label flow | `app/services/evaluator.py`, `app/services/audit.py`, `app/api/labels.py`, `app/api/healthz.py` (full), `app/api/raw.py` | — | E2, E3, E4 | `POST /labels` produces wire-conforming PRD §6.2 envelope; D-017 min-aggregation confidence; D-018 audit/metrics split (`audit_trail` + sibling `metrics` block); FR-900 through FR-912 taxonomy emits the right reason code per failure path; `/healthz` warm runs fixture-01 sentinel and returns 200 within 2 s on warm system; AC-NFR-PERF-001 holds against fixture-01 (P50 ≤ 2.7 s, P99 ≤ 5.0 s with mocked LLM cache) |
| **E6** | Batch Processor + SSE + Override | `app/batch/*` (state, worker, queue, anomaly), `app/api/batches.py`, `app/api/overrides.py` | — | E5 | `POST /batches` accepts PRD §6.3 envelope; SSE stream delivers per-label results; `LOOKAHEAD_K=3` default; `request(n)` pull-based demand respected; FR-401 first-label-individual; FR-404 mid-batch override does not stop queue; FR-405 M-of-N anomaly advisory fires; `POST /labels/{eid}/overrides` records FR-801 audit fields |
| **E7** | UI — Jinja2 shell + React island | `app/ui/templates/*`, `frontend/src/components/*`, `frontend/src/tokens/uswds-tokens.css`, `frontend/vite.config.ts`, built bundle in `app/ui/static/island/` | — | E5 (single-label disposition envelope), E6 (batch envelope) | All 17 T8 components (PRD §5.6) implemented; AC-NFR-A11Y-001 zero axe-core WCAG 2.0 AA violations on demo fixtures; FR-503 visible-separation between rule verdict & AI suggestion; FR-511 disposition pill uses color + shape + text; AC-FR-803 three-keystroke override (`O → reason → ENTER`); reflow at 320 CSS px; `prefers-reduced-motion` honored; built island committed; reviewer profiles A/B/C boot the demo without Node |
| **E8** | Demo + eval harness + deploy | `fixtures/01-07/*`, `demo/cached/*`, `scripts/regenerate_fixtures.py`, `eval/manifest.jsonl`, `eval/datasheet.md`, `eval/harness.py`, `eval/dashboard.py`, `app/api/eval.py` (DEV_MODE), `Dockerfile`, `Dockerfile.gpu`, `docker-compose*.yml`, `DEMO-RUNBOOK.md`, README updates, HF Spaces config | — | E1–E7 | All 7 demo fixtures pass their PRD §8.1 ACs (fixture-07 borderline-confidence in particular exercises FR-704); eval harness runs `eval-smoke` (~20 labels) and `eval-full` (~50 labels, right-sized per PRD v0.5 §9.1); §8.4 macro-F1 ≥ 0.70 on full eval; per-rule recall ≥ 0.80 on warning rules; `/eval` dashboard renders under `DEV_MODE=1`; HF Spaces deployment reachable on a public URL with TLS; `DEMO-RUNBOOK.md` complete; 5-minute recorded walkthrough delivered; deployed `/healthz` returns 200 |

---

## 4. Dependency graph

```
                    ┌───── E1 Foundation ────┐
                    │                        │
        ┌───────────┼───────────┬────────────┘
        │           │           │
        ▼           ▼           ▼
       E2          E3          E4
   Rule Engine  Vision Seam  Orchestrator Seam
        │           │           │
        └───────────┼───────────┘
                    ▼
                   E5
            Evaluator + Audit + Single-Label
                    │
                    ├──────────────────────┐
                    ▼                      ▼
                   E6                     E7
            Batch + SSE + Override        UI
                    │                      │
                    └───────────┬──────────┘
                                ▼
                               E8
                  Demo + Eval Harness + Deploy
```

**Parallelism opportunity.** E2, E3, E4 are independent given E1's schemas — they can be planned and implemented in parallel sessions if calendar pressure justifies the coordination cost. E6 and E7 are independent given E5 and can also parallelize. Default plan-of-record is sequential E1→E2→E3→E4→E5→E6→E7→E8 because (a) there's only one engineer, (b) downstream epochs reference upstream commits, (c) sequential discovery may surface ARCH revisions that ripple. Any parallel run is a per-decision optimization, not the default.

---

## 5. TDD strategy at the L1 level

Each epoch carries an explicit TDD posture so the L2 plan can land its `tests/` files purposefully.

| # | Test surface | Mockable | Real | Notes |
|---|---|---|---|---|
| **E1** | `tests/test_schemas_round_trip.py`, `tests/test_config_load.py`, `tests/test_logging_emission.py`, `tests/test_healthz_stub.py` | All upstream — there are no upstream deps yet | — | Golden-file round-trip for every PRD §6 wire schema; env-var-driven config asserts are the foundation |
| **E2** | `tests/test_rule_loader_failclose.py`, `tests/test_rules_yaml_round_trip.py`, `tests/test_brand_match_policies.py`, `tests/test_validator_registry.py`, per-rule pos/neg fixtures under `tests/rules/` | Validators are pure Python; no I/O at evaluation time | YAML parse + Pydantic validate | RuleLoader fail-closed cases (S5 §d cross-checks 1–8); per-rule timeout asserted via injected `time.monotonic` fake |
| **E3** | `tests/test_vision_substitutability.py`, `tests/test_vision_cloud_extraction.py`, `tests/test_vision_quality_gates.py`, `tests/test_vision_local_protocol.py` | OpenAI client (recorded responses or stub-mode); PaddleOCR/Florence/Qwen runners (interface-mocked) | BRISQUE/NIQE math on fixture images | Both impls share the same fixture-driven contract test; recorded responses pinned to `LLM_MODEL_SNAPSHOT` and `PROMPT_VERSION` (D-020) |
| **E4** | `tests/test_orchestrator_substitutability.py`, `tests/test_orchestrator_strict_schema.py`, `tests/test_orchestrator_fr303_invariant.py`, `tests/test_orchestrator_fr304_fallback.py`, `tests/test_orchestrator_ring_buffer.py` | Both LLM SDKs (OpenAI, Anthropic) per D-021 | Schema introspection on Pydantic v2 models | FR-303 enforced by introspecting the Pydantic schema — `assert "pass" not in disposition_field_choices` |
| **E5** | `tests/test_evaluator_single_label.py`, `tests/test_audit_trail.py`, `tests/test_failure_modes.py` (FR-900 series), `tests/test_confidence_aggregation.py`, `tests/test_audit_metrics_split.py`, `tests/test_evaluator_timeouts.py` | Vision (E3) and Orchestrator (E4) via Protocol fakes; Rule Engine (E2) optionally fake or real | Real E2 rule engine + canned observations | The single chokepoint where P4 is enforced; full FR-900 row coverage is the gate |
| **E6** | `tests/test_batch_worker.py`, `tests/test_batch_lookahead.py`, `tests/test_batch_anomaly.py`, `tests/test_override_endpoint.py`, `tests/test_sse_stream.py` | LLM via E3/E4 fakes; rule engine real | asyncio.Queue + SSE over `httpx.AsyncClient` | Pull-based demand asserted via consumer-controlled `request(n)` simulation; mid-batch override asserted by injecting an override mid-stream |
| **E7** | `tests/test_ui_components.py` (Vitest, in `frontend/`), `tests/test_a11y_axe.py` (Playwright + axe-core CI), `tests/test_keyboard_model.py`, `tests/test_reflow_320px.py`, `tests/test_disposition_pill_wcag_141.py` | Server returns canned PRD §6.2 envelopes | Real DOM render; real axe-core | NVDA + VoiceOver smoke is manual and documented in `tests/manual/a11y-smoke.md` |
| **E8** | `tests/test_demo_fixture_acs.py` (fixtures 01–07), `tests/test_eval_harness.py`, `tests/test_eval_dashboard_route.py`, deploy smoke `tests/test_deploy_healthz.py` | Cached LLM responses for the 6+1 demo fixtures (D-020) | Live `/healthz` against deployed URL | Eval-corpus run is offline and deterministic against pinned snapshot; deploy smoke is a single curl against the public URL |

---

## 6. Cross-cutting risks & mitigations

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| **R-1** Five-second SLA misses on fixture-01 happy path | Medium | High (RR-01) | Time-budget breakdown locked in ARCH §11.1; per-rule timeout 250 ms (S5 §13); whole-eval timeout enforced in E5; pre-warm via `/healthz` (D-011 §3); cached LLM responses for 6 demo fixtures (D-020) | E5, E8 |
| **R-2** Substitutability seam holds in tests but breaks in real cloud→local swap | Medium | High | The substitutability test in E3/E4 is contract-driven — both impls run against the *same* fixture set and produce the *same* `FieldObservation`/`Refined` shape; not just protocol-conformance | E3, E4 |
| **R-3** Rule pack drifts from CFR text mid-build | Low (T1 manifest is stable) | Medium (RR-04) | Hash-pinned `assets/warnings/govt_warning_16_21.txt`; `verbatim_hash` validator fail-closed; `rule_pack_version` semver-pinned; rule changes go through `rules/*.yaml` edit, not code | E2 |
| **R-4** `OpenAI Structured Outputs strict:true` schema rejects on edge inputs | Medium | Medium | Pin `LLM_MODEL_SNAPSHOT` (D-020); test against recorded responses; `LLM_OUTPUT_INVALID` qualifier on the per-task reason code (T5 fallback); manual review path (FR-802) is preserved | E4 |
| **R-5** Built React island bundle drifts from sources | Medium | Medium | CI check that `pnpm build && git diff --exit-code app/ui/static/island/` is clean on every PR | E7 |
| **R-6** HF Spaces `cpu-basic` cold-start exceeds the demo budget | Medium | Medium | Demo runbook calls `/healthz` at T-5 minutes (D-011 §3); cached LLM responses cover 7 fixtures so the recorded walkthrough is reproducible; A10G-small upgrade documented as one-click escape hatch (ARCH §9.3) | E8 |
| **R-7** Local-mode (`--extra gpu`) only protocol-tested, not validated against demo fixtures | Accepted | Low (cloud is the validated default for the deployed URL) | Documented in ARCH §4.2.6 and §8.2; local impl exists to prove the seam holds, not to ship as the demo's primary path | E3 |
| **R-8** Audit-record retention not designed for production | Accepted | Low (MVP scope only) | OQ-ARCH-4 in ARCH §16; in-memory only by structural choice; persistence-backed `AuditRecorder` is a swappable seam if/when production lands | — |
| **R-9** Override drawer's three-keystroke target depends on reason-code prefix uniqueness | Medium | Low | E2 reason-code registry includes a startup invariant: prefix-3 letters of every code's `BIN.SUB` is unique within a class; if not, picker resolves on second keystroke (graceful, not a hard fail) | E2, E7 |
| **R-10** Eval-corpus class balance drifts from S4 spec | Low | Medium | `eval/datasheet.md` (Gebru et al. 2021) makes class balance auditable; `eval-smoke` and `eval-full` both compute and emit class-balance stats | E8 |

---

## 7. Out of MVP

Lifted from `docs/PRD.md` §3.3 — out of every L1 epoch:

- COLAs Online integration (any direction).
- Allowable-revisions / post-approval surveillance.
- Conditional fields: sulfite, organic, FD&C Yellow #5, cochineal/carmine, major-allergen.
- Beverages outside Parts 4/5/7 (cider <7% ABV, certain saké).
- Production ATO claim, FedRAMP package, PIV/SAML.
- Rule changes via UI (rule pack is config; D-014).
- Internationalization / non-English labels.
- Multi-image label aggregation algorithm beyond single front-label (PRD OQ-PRD-4 deferred to stretch).

---

## 8. Stretch (PRD §3.2)

Stretch items are owned by their natural epoch — not separate epochs — and may slip per calendar:

| Stretch item | Owning epoch | Dependency |
|---|---|---|
| Wine depth (vintage / AVA / appellation / sulfite) | E2 | After common-fields rule pack lands |
| Malt depth (SoC + formula matching) | E2 | Same |
| Batch demo at importer-drop scale (200–300 labels) | E6, E8 | After E6 batch pipeline |
| Calibrated needs-review routing on held-out sample | E8 | After E8 eval corpus |
| Automated threshold re-calibration (brand-match cutoffs, confidence-band edges, BRISQUE/NIQE gates) | E8 | After eval corpus is built |
| Network-failure recovery demo | E8 | After E5/E6 |
| Supervisor calibration view | E7, E8 | After E7 UI shell |
| Templated applicant-message send | E7 | After needs-better-photo card lands |

---

## 9. L2 hand-off process

For each epoch, when it's the next epoch to land:

1. Use `superpowers:writing-plans` to author `docs/plans/2026-MM-DD-ttb-epoch-N-<name>.md` — file-level tasks with bite-sized TDD steps, exact paths, exact code, exact commands. The L1 epoch doc names the components, exit gates, and TDD strategy that the L2 plan must hit.
2. Use `superpowers:parallel-planning` to add a dependency graph + execution waves to the L2 plan.
3. Use `superpowers:plan-review` to review the L2 plan; address findings inline.
4. `/clear` and dispatch via `parallel-plan-executor`.
5. After the L2 lands, the per-epoch L1 sub-doc is updated with: completion date, commit range, deviations from L1 plan (if any), and any ARCH revisions that surfaced.

`parallel-plan-executor` is the **only** L2 executor (per CLAUDE.md). `superpowers:subagent-driven-development` is forbidden.

---

## 10. Per-epoch sub-files

Each linked file owns its epoch's L1 detail (goal, components delivered, seam ownership, exit-gate AC, TDD strategy, deferred items, risks, L2 hand-off notes).

| # | File |
|---|---|
| **E1** | [`ttb-label-verification-epoch-1-foundation.md`](./ttb-label-verification-epoch-1-foundation.md) |
| **E2** | [`ttb-label-verification-epoch-2-rule-engine.md`](./ttb-label-verification-epoch-2-rule-engine.md) |
| **E3** | [`ttb-label-verification-epoch-3-vision-seam.md`](./ttb-label-verification-epoch-3-vision-seam.md) |
| **E4** | [`ttb-label-verification-epoch-4-orchestrator-seam.md`](./ttb-label-verification-epoch-4-orchestrator-seam.md) |
| **E5** | [`ttb-label-verification-epoch-5-evaluator-audit.md`](./ttb-label-verification-epoch-5-evaluator-audit.md) |
| **E6** | [`ttb-label-verification-epoch-6-batch-override.md`](./ttb-label-verification-epoch-6-batch-override.md) |
| **E7** | [`ttb-label-verification-epoch-7-ui.md`](./ttb-label-verification-epoch-7-ui.md) |
| **E8** | [`ttb-label-verification-epoch-8-demo-eval-deploy.md`](./ttb-label-verification-epoch-8-demo-eval-deploy.md) |

---

## 11. FR / NFR coverage matrix

Every PRD FR and NFR maps to at least one epoch's exit gate. Where coverage is **implicit** (handled by an epoch's structural choice rather than cited by ID), the cell notes the mechanism.

### 11.1 FR coverage

| FR series | Owning epoch(s) | Mechanism |
|---|---|---|
| **FR-001 – FR-008** Field extraction | E3 | `VisionExtractor` per-field manifest; both impls satisfy contract |
| **FR-100 – FR-106** Application-data ingest | E1 (schema), E5 (boundary) | PRD §6.1 wire schema in E1; multipart parsing + magic-byte sniff in E5 (`POST /labels`) |
| **FR-200 – FR-206** Common warning rules | E2 | Rule pack `rules/common/health_warning.yaml`; per-rule pos/neg ACs |
| **FR-210 – FR-217** Wine rules | E2 | Rule pack `rules/wine/wine.yaml`; per-rule pos/neg ACs |
| **FR-220 – FR-229** Spirits rules | E2 | Rule pack `rules/spirits/spirits.yaml` + `rules/spirits-deep.yaml`; per-rule pos/neg ACs |
| **FR-230 – FR-237** Malt rules | E2 | Rule pack `rules/malt/malt.yaml`; per-rule pos/neg ACs |
| **FR-240** Brand-name match policy | E2 | `app/rules/brand_match.py` Stage A normalize + Stage B Jaro-Winkler |
| **FR-300 – FR-302** AI orchestration tasks | E4 | `app/orchestrator/tasks/{brand_disambig,reasoning_enrich,ocr_reconcile}.py` |
| **FR-303** AI never decides pass/fail | E4 (type-level), E5 (runtime) | `Refined` schema has no `disposition` field (E4); evaluator never patches dispositions from Refined (E5) |
| **FR-304** AI fallback to needs_review | E4 (orchestrator), E5 (composition) | Fallback returned by orchestrator on outage; evaluator passes through |
| **FR-400 – FR-406** Batch processing | E6 | `app/batch/*` + `app/api/batches.py` SSE stream |
| **FR-500 – FR-511** UX surfaces | E7 | 17 React components + Jinja2 shell |
| **FR-600 – FR-604** Image handling | E1 (allowlist), E3 (DPI + quality), E5 (no-persist enforcement) | Pydantic strict + magic-byte (E1/E5); BRISQUE/NIQE + DPI extraction (E3) |
| **FR-700 – FR-704** Disposition output | E1 (envelope schema), E5 (assembly) | PRD §6.2 envelope in E1 schemas; Application Service assembly in E5 |
| **FR-800 – FR-804** Override + manual review | E6 (server endpoint), E7 (drawer UX) | `POST /labels/{eid}/overrides` (E6) + `OverrideDrawer` keyboard model (E7) |
| **FR-900 – FR-912** Engine failure taxonomy | E5 | Full 13-row coverage in `tests/test_evaluator_failure_modes.py` |

### 11.2 NFR coverage

| NFR | Owning epoch(s) | Mechanism |
|---|---|---|
| **NFR-PERF-001** Single-label ≤5 s | E5, E6, E8 | Three gates: E5 single-label, E6 first-label-of-batch, E8 deployed `/healthz` |
| **NFR-PERF-002** Pull-based demand | E6 | `BatchInFlightState` bounded asyncio.Queue + SSE consumer cadence |
| **NFR-PERF-003** P50 ≤ 2.7s, P99 ≤ 5.0s | E5 | 30+ trials with statistics in `tests/test_post_labels_perf.py` |
| **NFR-UX-001** Senior-friendly UI | E7 | 73-year-old benchmark — high contrast, predictable layout, explicit affordances |
| **NFR-UX-002** Keyboard-operable end-to-end | E7 | `useKeyboardShortcuts` hook + Playwright keyboard-model tests |
| **NFR-UX-003** 3-keystroke override | E2 (registry prefix uniqueness), E7 (picker resolves on first keystroke) | Joint contract |
| **NFR-UX-004** Browser support + 320px viewport | E7 | Playwright reflow test at 320 CSS px |
| **NFR-A11Y-001** WCAG 2.0 AA / Section 508 | E7 | axe-core CI; zero AA violations on demo fixtures |
| **NFR-A11Y-002** VPAT/ACR authoring | **Deferred to production phase** | See §7 "Out of MVP" — VPAT is production-trajectory paperwork; prototype tier per BRD §8.2 |
| **NFR-A11Y-003** WCAG 2.1/2.2 design targets | E7 | Implemented as design targets; see PRD §15.2 SC list (reflow, non-text contrast, focus-not-obscured, etc.) |
| **NFR-A11Y-004** Reduced motion | E7 | `prefers-reduced-motion: reduce` honored; Playwright media-feature override test |
| **NFR-A11Y-005** Reflow at 320 CSS px | E7 | Playwright reflow test at 320 px viewport |
| **NFR-AUDIT-001** Audit record per disposition | E5 | `AuditRecord` assembled per FR-703 |
| **NFR-AUDIT-002** Sufficient for regulatory audit | E5 | input_hash + output_hash + rule_set_version + per_rule_trace + override history |
| **NFR-PORT-001** Firewall-deployable | E3 (vision seam), E4 (orchestrator seam), E8 (deployment) | `LocalVisionExtractor` (PaddleOCR + GPT-4o tiebreak) proves the on-prem vision path per D-021; orchestrator ABC permits future on-prem swap-in (e.g., vLLM) without rework; deployed URL uses cloud mode |
| **NFR-PORT-002** On-prem inference path preserved | E3, E4 | Local-mode vision impl ships in MVP; orchestrator on-prem swap-in is a new module against the existing ABC (per D-021) |
| **NFR-DET-001** Within-session determinism | E5 | Session-only canonicalized cache in `app.state` |
| **NFR-DET-002** Cross-session determinism out of scope | (deferred — OQ-ARCH-2) | Documented; no MVP work |
| **NFR-DATA-001** No persistent artwork | E1 (no DB deps), E5 (no file writes outside eval/history/) | Structural — no persistence libs in `pyproject.toml` |
| **NFR-DATA-002** Audit in-memory only | E5, E6 | `app.state.batches` dict; evicted on session end |
| **NFR-SEC-001** TLS | E8 | HF Spaces edge handles TLS termination |
| **NFR-SEC-002** Secrets from env vars | E1 | `app/config.py` Pydantic Settings; grep enforcement |
| **NFR-SEC-003** Input validation | E1, E5 | Pydantic `extra="forbid"` + magic-byte sniff in `POST /labels` |
| **NFR-SEC-004** Logging redaction | E1 | `app/logging/redaction.py` filter |
| **NFR-OBS-001** Structured logs at engine-failure events | E1 (formatter), E5 (emission per failure mode) | T3 §Q3.10 field schema |
| **NFR-OBS-002** Latency P50/P95/P99 exposure | E5 | `/metrics` or structured-log emission on every evaluation |

---

## 12. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial L1 epoch slicing. 8 epochs, 3 substitutability seams, sequential plan-of-record with parallelism noted. |
| 0.2 | 2026-05-02 | Project team | Plan-review address-pass: added §11 FR/NFR coverage matrix; reconciled boot-time vs. cold-start budgets in §2; added VPAT/ACR deferral to §7; added boot-time clarification. Per-epoch sub-files updated separately. |
| 0.3 | 2026-05-03 | Project team | Applied D-021 prototype-tier scope reduction to L1: dropped Florence-2 / Qwen2.5-VL from local vision and vLLM/XGrammar from orchestrator across §2, §3 (epoch table), §11 NFR-PORT rows, and per-epoch E3 / E4 sub-files. Substitutability seams unchanged. |
| 0.4 | 2026-05-03 | Project team | Aligned with PRD v0.5 eval-corpus right-sizing: §3 E8 row updated (full corpus ~50 labels, was ≥250). |
