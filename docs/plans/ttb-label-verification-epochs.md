# TTB Label Verification — L1 Epoch Plan

> **Plan tier:** L1 (epoch-level slicing). Strategic, not file-level.
> Each epoch ships one independently TDD-testable slice.
> **Per-epoch L2 plans (file-level + bite-sized TDD steps) are written separately**, one at a time, *immediately before* that epoch's implementation, using `superpowers:writing-plans` + `superpowers:parallel-planning`, then dispatched via `parallel-plan-executor`. This document does NOT contain L2 task decomposition.

**Goal.** Build the TTB AI-Powered Alcohol Label Verification prototype against `docs/PRD.md` v0.4 and `docs/ARCHITECTURE.md` v0.2 — a standalone, web-deployable proof-of-concept that returns a draft disposition for a single COLA label in ≤5 s with citation-grounded reasoning, plus batch handling, override, and an audit trail. No persistence; no COLAs Online integration; no production ATO claim.

**Architecture posture.** Single-process FastAPI app with three substitutability seams (D-004): `VisionExtractor` (Protocol), `Orchestrator` (ABC), `RuleLoader` (data-shape boundary). Deterministic rule core in YAML+Pydantic; AI orchestrates but never decides pass/fail (D-002, FR-303). Session-scoped state only (NFR-DATA-001/002). Cloud mode (GPT-4o-on-crop strict:true) is the default validated path; local mode (PaddleOCR + Florence-2 + GPT-4o tiebreaker + Qwen2.5-VL-AWQ) is the on-prem-trajectory companion gated by `--extra gpu`.

**Tech stack (fixed by D-013–D-016).** Python 3.12 / FastAPI / Pydantic v2 / uv / asyncio / PyYAML / RapidFuzz / OpenAI Structured Outputs (`strict:true`) / sse-starlette / Jinja2 / React 18 + TypeScript + Vite + shadcn/ui (Radix + Tailwind) + USWDS color tokens / pnpm / pytest / axe-core (CI a11y) / HF Spaces (Docker SDK, `cpu-basic`).

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
| **Vision** (#1) | `app/vision/base.py` `VisionExtractor` Protocol | `CloudVisionExtractor` (validated default), `LocalVisionExtractor` (on-prem-trajectory companion) | **E3** |
| **Orchestrator** (#2) | `app/orchestrator/base.py` `Orchestrator` ABC | `OpenAIStrictOrchestrator` (validated default), `AnthropicStrictOrchestrator` (skeleton), `VllmXgrammarOrchestrator` (skeleton, federal on-prem) | **E4** |
| **Rule loader** (data-shape, MVP-substitutable) | `app/rules/loader.py` `YamlRuleLoader` | `YamlRuleLoader` (only one in MVP); RuleEngine ABC consumes the frozen `RuleSet` data shape | **E2** |

---

## 3. Epochs at a glance

| # | Name | Primary owns | Substitutability seam | Depends on | Exit gate (epoch-level AC) |
|---|---|---|---|---|---|
| **E1** | Foundation & boot | `pyproject.toml`, `app/main.py`, `app/config.py`, `app/deps.py`, `app/schemas/*`, `app/logging/*`, `/healthz` stub, base test infra | — (DI shape only) | — | `uv run task demo` boots; `/healthz` returns 200; PRD §6.1/§6.2/§6.3/§6.4 schemas round-trip; structured-log JSON line emits with required cross-cutting fields |
| **E2** | Rule Engine + rule pack | `app/rules/*` (loader, engine, models, brand_match, _validators/), `rules/*.yaml`, `assets/warnings/govt_warning_16_21.txt`, `rules/reason_codes.yaml`, `rules/tables/cpi_16_22_a_4.yaml` | RuleLoader (data-shape) | E1 schemas | RuleLoader fail-closes on every S5 §d violation; every PRD FR-200/210/220/230 series rule passes its positive AC and fails its canonical negative AC with the correct `reason_code` + CFR citation; brand-match Stage A normalizes STONE'S THROW; per-rule timeout and whole-evaluation timeout enforce |
| **E3** | Vision Extractor seam | `app/vision/*` (base, cloud, local + helpers) | **D-004 #1** | E1 schemas (FieldObservation, Evidence) | `VisionExtractor` Protocol declared in `app/vision/base.py`; both concrete impls implement it; `tests/test_vision_substitutability.py` asserts both satisfy the Protocol; cloud impl extracts FR-001–008 fields against canned multipart JPEG/PNG fixtures; BRISQUE/NIQE quality gates emit `WARNING.LEGIBILITY.*` reason codes; local impl is import-clean under `--extra gpu` and protocol-conformant under mock |
| **E4** | AI Orchestrator seam | `app/orchestrator/*` (base, openai_strict, anthropic_strict, vllm_xgrammar, tasks/) | **D-004 #2** | E1 schemas | `Orchestrator` ABC + 3 concrete impls; substitutability test passes for all 3; FR-303 invariant: structured output schema contains no `pass | fail` field (asserted by introspection); FR-304 fallback: simulated LLM outage returns `needs_review` with `ENGINE.MODEL.UNAVAILABLE`; ring-buffer `CallRecord` populated per call |
| **E5** | Application Service + Audit + single-label flow | `app/services/evaluator.py`, `app/services/audit.py`, `app/api/labels.py`, `app/api/healthz.py` (full), `app/api/raw.py` | — | E2, E3, E4 | `POST /labels` produces wire-conforming PRD §6.2 envelope; D-017 min-aggregation confidence; D-018 audit/metrics split (`audit_trail` + sibling `metrics` block); FR-900 through FR-912 taxonomy emits the right reason code per failure path; `/healthz` warm runs fixture-01 sentinel and returns 200 within 2 s on warm system; AC-NFR-PERF-001 holds against fixture-01 (P50 ≤ 2.7 s, P99 ≤ 5.0 s with mocked LLM cache) |
| **E6** | Batch Processor + SSE + Override | `app/batch/*` (state, worker, queue, anomaly), `app/api/batches.py`, `app/api/overrides.py` | — | E5 | `POST /batches` accepts PRD §6.3 envelope; SSE stream delivers per-label results; `LOOKAHEAD_K=3` default; `request(n)` pull-based demand respected; FR-401 first-label-individual; FR-404 mid-batch override does not stop queue; FR-405 M-of-N anomaly advisory fires; `POST /labels/{eid}/overrides` records FR-801 audit fields |
| **E7** | UI — Jinja2 shell + React island | `app/ui/templates/*`, `frontend/src/components/*`, `frontend/src/tokens/uswds-tokens.css`, `frontend/vite.config.ts`, built bundle in `app/ui/static/island/` | — | E5 (single-label disposition envelope), E6 (batch envelope) | All 17 T8 components (PRD §5.6) implemented; AC-NFR-A11Y-001 zero axe-core WCAG 2.0 AA violations on demo fixtures; FR-503 visible-separation between rule verdict & AI suggestion; FR-511 disposition pill uses color + shape + text; AC-FR-803 three-keystroke override (`O → reason → ENTER`); reflow at 320 CSS px; `prefers-reduced-motion` honored; built island committed; reviewer profiles A/B/C boot the demo without Node |
| **E8** | Demo + eval harness + deploy | `fixtures/01-07/*`, `demo/cached/*`, `scripts/regenerate_fixtures.py`, `eval/manifest.jsonl`, `eval/datasheet.md`, `eval/harness.py`, `eval/dashboard.py`, `app/api/eval.py` (DEV_MODE), `Dockerfile`, `Dockerfile.gpu`, `docker-compose*.yml`, `DEMO-RUNBOOK.md`, README updates, HF Spaces config | — | E1–E7 | All 7 demo fixtures pass their PRD §8.1 ACs (fixture-07 borderline-confidence in particular exercises FR-704); eval harness runs `eval-smoke` (~20 labels) and `eval-full` (≥250 labels); §8.4 macro-F1 ≥ 0.70 on full eval; per-rule recall ≥ 0.80 on warning rules; `/eval` dashboard renders under `DEV_MODE=1`; HF Spaces deployment reachable on a public URL with TLS; `DEMO-RUNBOOK.md` complete; 5-minute recorded walkthrough delivered; deployed `/healthz` returns 200 |

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
| **E4** | `tests/test_orchestrator_substitutability.py`, `tests/test_orchestrator_strict_schema.py`, `tests/test_orchestrator_fr303_invariant.py`, `tests/test_orchestrator_fr304_fallback.py`, `tests/test_orchestrator_ring_buffer.py` | All three LLM SDKs (OpenAI, Anthropic, vLLM) | Schema introspection on Pydantic v2 models | FR-303 enforced by introspecting the Pydantic schema — `assert "pass" not in disposition_field_choices` |
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

## 11. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial L1 epoch slicing. 8 epochs, 3 substitutability seams, sequential plan-of-record with parallelism noted. |
