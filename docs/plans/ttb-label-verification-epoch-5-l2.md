# TTB Label Verification — Epoch 5 (Application Service + Audit + Single-Label Flow) — L2 Implementation Plan

> **Version:** v0.4 (2026-05-04) — see Change log for iter-2 fixes.
>
> **For agentic workers:** REQUIRED EXECUTOR: `parallel-plan-executor`. Per olorin CLAUDE.md, `superpowers:subagent-driven-development` is obsolete and fully replaced by `parallel-plan-executor` (which injects the `task-executor` skill body for TDD enforcement). Each task lands as one Red→Green→Commit cycle (or, for the few bundled tasks, multiple cycles) inside an isolated subagent. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Parent L1:** [`ttb-label-verification-epoch-5-evaluator-audit.md`](./ttb-label-verification-epoch-5-evaluator-audit.md) (v0.1)
> **L1 index:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **E4 L2 (structural template):** [`ttb-label-verification-epoch-4-l2.md`](./ttb-label-verification-epoch-4-l2.md) (v0.4 — SHIPPED)
> **PRD:** [`docs/PRD.md`](../PRD.md) — FR-300/301/302/303/304 (orchestrator), FR-505/603 (legibility), FR-700-series (audit), FR-900-912 (engine-failure taxonomy), NFR-PERF-001/003 (SLA), NFR-DET-001/002 (determinism)
> **ARCH:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — §3.2 (HTTP boundary), §4.2.2 (Evaluator), §4.2.8 (AuditRecorder), §6.7/§6.8 (audit/hash), §10.3 (honest failure), §11.1 (latency budget), §11.4 (tail-tolerant), §13.5 (audit/telemetry split)
> **ADRs in scope:** D-004 (substitutability), D-017 (min-aggregation), D-018 (audit/metrics split), D-019 (DEV_MODE raw endpoint)

**Goal.** Wire the chokepoint Application Service that composes the three E2/E3/E4 seams into one end-to-end evaluation behind `POST /labels`. After E5: `POST /labels` accepts a PRD §6.1 envelope + multipart label, returns a wire-conforming PRD §6.2 envelope inside a 5-second SLA, and the FR-900 series engine-failure taxonomy is comprehensively emitted by the right components in the right circumstances. Every architecture principle (P1–P5) is enforced here — most importantly **FR-303 at runtime** (orchestrator never overrides a rule-engine `fail` to `pass`) and **P4** (engine failures route to `needs_review`, never silently default-pass).

**Architecture.** A single Python package `app/services/` decomposed into thin, pure helper modules + a slim Evaluator orchestration class. Each pure module is independently testable and lands as a single-task Red→Green→Commit:

- `app/services/engine_meta.py` — `EvaluationTimeline` mutable accumulator (the single audit/metrics source per D-018).
- `app/services/confidence.py` — single-source `numeric → Band` mapping.
- `app/services/disposition.py` — pure `compute_disposition(results) -> str`.
- `app/services/aggregation.py` — pure `min_aggregate_confidence(fields)` per D-017.
- `app/services/patcher.py` — pure FR-303-safe `patch_validation_results(results, refined)`.
- `app/services/triggers.py` — pure `should_invoke_orchestrator(results) -> bool` (exact predicate).
- `app/services/envelope_builder.py` — pure envelope assembly (success path + short-circuit path).
- `app/services/cache.py` — `SessionCache` (NFR-DET-001).
- `app/services/metrics_builder.py` — `MetricsBuilder.build(timeline) -> Metrics`.
- `app/services/audit.py` — `AuditRecorder.assemble(...) + canonical hashing`.
- `app/services/evaluator.py` — thin `Evaluator` class that USES the above modules; the chokepoint that catches every downstream exception and routes to FR-900-series codes.

The Evaluator holds no per-evaluation state beyond the call frame; both `AuditRecorder.assemble` and `MetricsBuilder.build` consume the same `EvaluationTimeline` instance built by the Evaluator (D-018). Web layer (`app/api/labels.py`) carries no engine logic. `/healthz` upgrades to a full sentinel run; `/batches/{batch_id}/labels/{label_id}/calls` lands DEV_MODE-gated in `app/api/raw.py`.

**Tech stack.** Python 3.12, Pydantic v2 (E1), FastAPI (E1), `asyncio.wait_for` (whole-eval timeout), `httpx` (already pinned), `respx` (dev — already pinned), `pillow` (E3 — used by labels endpoint magic-byte sniff). **No new top-level dependencies.**

**TDD posture.** Each task is one Red→Green→Commit cycle on a single narrow file (or one tightly coupled file group). The `task-executor` skill body (injected by `parallel-plan-executor`) enforces "one behavior per commit". Two tasks bundle multiple cycles by necessity (T13 Evaluator core = 4 cycles; T14 Evaluator resilience = 2 cycles) — those are the only multi-cycle tasks in the plan. Each commit is atomic and Conventional (`feat:`/`test:`/`chore:`/`docs:`/`fix:`). Pre-existing main is fast-forwarded after each task.

**Hard scope boundary.** This plan owns: `app/services/{engine_meta,confidence,disposition,aggregation,patcher,triggers,envelope_builder,cache,metrics_builder,audit,evaluator}.py`, `app/api/{labels,raw}.py`, the upgrade to `app/api/healthz.py`, three new fakes under `tests/_fakes/`, an *additive* `build_evaluator` factory in `app/deps.py`, a router-registration line in `app/main.py`, **two additive surfaces in `app/rules/` — `__init__.py::build_rule_engine` (T0a) and `context.py::build_validator_context` (T0b) — neither alters E2 behavior; both are construction-time helpers callable from outside `app/rules/`**, an *additive* `rules_root` field on `app/config.py::Settings` (T0a), **an *additive* abstract method `RuleEngine.build_validator_context(self, *, started_at_ms) -> ValidatorContext` on `app/rules/engine.py` plus a concrete implementation on `YamlRuleEngine` that sources its data from the existing private `_ruleset` (iter-2 Blocker fix — see T0b)**, **an *additive* optional field `expected_values: tuple[ExpectedValue, ...] = ()` on `app/schemas/application.py::Application` (iter-2 Warning #2 fix — defaults to empty tuple so all existing callers stay green; populated by T20 fixture sidecars and forwarded by T13 Cycle C)**, and ~15 new test files. It does **NOT** modify `app/rules/loader.py`, `app/rules/yaml_engine.py`'s evaluation logic, `app/rules/_validators/` (E2 — locked), `app/vision/` (E3 — locked), `app/orchestrator/` (E4 — locked), or any other field of `app/schemas/` (existing wire shapes are stable).

**Locked-surface additions are deliberately additive only.** The new abstract method on `RuleEngine` and the new optional field on `Application` both preserve every existing call site: `RuleEngine` subclasses outside this plan don't exist (only `YamlRuleEngine` and the test `FakeRuleEngine`, both updated in lockstep — T0b/T3); `Application` callers that don't pass `expected_values` get the default empty tuple, matching today's behavior bit-for-bit. No public method signature changes; no field renames; no existing-test rewrites.

**FR-906 deferral.** The L1 names FR-906 (ruleset version mismatch — loader-time refusal to start) but it is explicitly deferred from E5: the loader-time refusal lives in E2's loader test (`tests/rules/test_loader.py::test_loader_refuses_unknown_version`) and is exercised end-to-end as part of E8 deployment readiness (subprocess assertion: an interpreter started against an incompatible ruleset exits non-zero before serving any request). E5 wires `build_rule_engine` (T0a) to call the existing E2 loader, so any FR-906-class refusal surfaces at process startup well before any T0a/T15 test runs — there is nothing for E5 to add beyond not bypassing the loader, which T0a does not.

---

## File map

| Path | Created/modified by task | Responsibility |
|---|---|---|
| `app/rules/__init__.py` | T0a | `build_rule_engine(settings) -> YamlRuleEngine`. Force-imports validators then loads ruleset. Single construction point used by `build_evaluator` (T15) and healthz (T16). |
| `app/rules/context.py` | T0b | `build_validator_context(engine, *, started_at_ms) -> ValidatorContext`. Per-evaluation factory used by T13/T14. |
| `app/services/__init__.py` | T1 | Package marker. |
| `app/services/engine_meta.py` | T1 | `EvaluationTimeline` mutable accumulator. The ONE source of truth for per-evaluation timing + outcome data. Both `AuditRecorder` and `MetricsBuilder` read from it. |
| `app/services/confidence.py` | T2 | `to_band(numeric: float) -> Band`. Single source of truth for numeric→band thresholds (0.5/0.85). |
| `tests/_fakes/__init__.py` | T3 | Package marker. |
| `tests/_fakes/orchestrator.py` + `tests/_fakes/rules.py` | T3 | `FakeOrchestrator(Orchestrator)` + `FakeRuleEngine(RuleEngine)` for evaluator unit tests. |
| `tests/_fakes/vision.py` | T4 | `FakeVisionExtractor` (Protocol-compatible — `extract` + `ensure_loaded` only). Legibility short-circuit is plumbed through `app.vision.quality.assess`, NOT a fake-only attribute. |
| `app/services/metrics_builder.py` | T5 | `MetricsBuilder.build(timeline) -> Metrics`. Pure; no I/O. |
| `app/services/audit.py` | T6 | `AuditRecorder.assemble(...)` + `_canonical_json`/`_input_hash`/`_output_hash`. |
| `app/services/disposition.py` | T7 | `compute_disposition(results) -> str`. Pure: pass iff every PASS or NOT_APPLICABLE; fail iff any FAIL; else needs_review. Empty-results → needs_review. |
| `app/services/aggregation.py` | T8 | `min_aggregate_confidence(fields) -> tuple[Band, float]`. Pure: min over per-field numeric, mapped via `confidence.to_band`. |
| `app/services/patcher.py` | T9 | `patch_validation_results(results, refined) -> tuple[VR, ...]`. **FR-303-safe** — touches only `message`/`aggregated_confidence`/`evidence`; never `outcome`/`severity`/`reason_code`. |
| `app/services/triggers.py` | T10 | `should_invoke_orchestrator(results) -> bool`. Exact predicate per L1 §7 risk #2 and FR-300. |
| `app/services/envelope_builder.py` | T11 | `build_success_envelope(...)` + `build_short_circuit_envelope(...)`. Pure assembly; no I/O. |
| `app/services/cache.py` | T12 | `SessionCache` — bounded LRU keyed by canonical input hash. NFR-DET-001. |
| `app/services/evaluator.py` | T13 (4 cycles) + T14 (2 cycles) | Thin orchestration. Uses all helpers; calls vision → rules → orchestrator (conditional) → patcher → envelope. T13 lands core wiring; T14 layers on whole-eval timeout + chokepoint exception routing. |
| `app/api/labels.py` | T15 | `POST /labels` — multipart parsing, magic-byte image check, delegation, envelope serialization. |
| `app/deps.py` | T15 | **Additive only.** Add `build_evaluator(settings) -> Evaluator`. |
| `app/main.py` | T15 + T17 | Router registration. T15 adds `labels.router`; T17 appends `raw.router`. |
| `app/api/healthz.py` | T16 | Upgrade to full sentinel against fixture-01. |
| `app/api/raw.py` | T17 | DEV_MODE-gated `GET /batches/.../calls`. |
| `tests/rules/test_build_rule_engine.py` | T0a | `build_rule_engine(settings)` factory test. |
| `tests/rules/test_build_validator_context.py` | T0b | `build_validator_context(engine, started_at_ms)` factory test. |
| `tests/test_engine_meta_timeline.py` | T1 | Timeline shape + recording API. |
| `tests/test_confidence_band_mapping.py` | T2 | Edge values + monotonicity. |
| `tests/test_fakes_orchestrator_rules.py` | T3 | Protocol conformance for orch + rules fakes. |
| `tests/test_fakes_vision.py` | T4 | Protocol conformance only — legibility goes through `app.vision.quality.assess`. |
| `tests/test_metrics_builder.py` | T5 | `MetricsBuilder.build` returns the right `Metrics` shape. |
| `tests/test_audit_recorder.py` + `tests/test_audit_metrics_split.py` | T6 | AuditRecorder shape; D-018 split. |
| `tests/test_disposition_rule.py` | T7 | Parametrized disposition rule. |
| `tests/test_confidence_aggregation.py` | T8 | D-017 min-aggregation. |
| `tests/test_patcher_fr303.py` | T9 | FR-303-safe patcher (the canary). |
| `tests/test_triggers.py` | T10 | Orchestrator-trigger exact predicate. |
| `tests/test_envelope_builder.py` | T11 | Success + short-circuit envelope shapes. |
| `tests/test_session_cache.py` | T12 | LRU eviction + `get`/`put` semantics. |
| `tests/test_evaluator_skeleton.py` + `tests/test_evaluator_happy_path.py` + `tests/test_evaluator_orchestrator_paths.py` + `tests/test_evaluator_legibility_shortcircuit.py` | T13 | One test file per cycle (4 cycles). |
| `tests/test_evaluator_timeouts.py` + `tests/test_evaluator_chokepoint.py` | T14 | Resilience cycles. |
| `tests/test_post_labels_endpoint.py` | T15 | POST happy path + 400 cases. |
| `tests/test_healthz_warmup.py` | T16 | Warm-up sentinel + warm-call latency. |
| `tests/test_raw_endpoint_dev_mode.py` | T17 | DEV_MODE 404/200 toggle. |
| `tests/test_evaluator_failure_modes.py` | T18 | Full FR-900 series coverage (parametrized). |
| `tests/test_post_labels_perf.py` | T19 | NFR-PERF-001/003 P50/P99 statistics. |
| `tests/test_ac_fixture_coverage.py` | T20 | L1 §4 AC #1–4 fixture-driven. |
| `tests/test_evaluator_chokepoint_grep.py` | T21 | P4 grep guard. |

---

## Conventions used in this plan

- **Frozen Pydantic.** All schema models retain `model_config = ConfigDict(extra="forbid", frozen=True)` (E1/E4 invariant). Service-layer accumulators (`EvaluationTimeline`) are NOT frozen — they're mutated during `evaluate()`. Every pure helper module either takes/returns immutable types directly or returns new immutable instances via `model_copy(update=...)`.
- **Pure helpers.** Modules T7-T11 have ZERO I/O, ZERO clock reads, ZERO global state. Everything in/out via parameters and return values. Tests can call them directly without async machinery.
- **Async signature.** `Evaluator.evaluate()`, the API endpoint handlers, and the rule/vision/orchestrator calls inside Evaluator are all `async def`. Pure helpers are sync.
- **DI factories.** `build_evaluator(settings) -> Evaluator` is the single construction point. `Evaluator.__init__` takes the four dependencies + cache explicitly — never reads `Settings()` itself for resolution. Web layer injects via FastAPI `Depends`.
- **FR-303 patch contract** (T9 `patcher.py`). When patching a `ValidationResult` with orchestrator output, build a NEW `ValidationResult` via `model_copy(update={...})` that touches ONLY: `message` (annotation), `aggregated_confidence` (downward-only), `evidence` (additive). NEVER touches `outcome`, `severity`, `reason_code`. Asserted by `tests/test_patcher_fr303.py` even when orchestrator-`Refined` disagrees with a rule-engine `fail`.
- **Disposition computation rule** (T7 `disposition.py`). `pass` iff every `ValidationResult.outcome ∈ {Outcome.PASS, Outcome.NOT_APPLICABLE}`; `fail` iff any `Outcome.FAIL`; otherwise `needs_review` (covers `INSUFFICIENT_EVIDENCE`, `TIMEOUT`, `ERROR`). Empty results → `needs_review`. Precedence: fail > needs_review > pass.
- **FR-300 trigger predicate** (T10 `triggers.py`). EXACTLY: a `ValidationResult` exists with `vr.reason_code == "BRAND.NAME.NEEDS_REVIEW"`. Per L1 §7 risk #2, the trigger is **not heuristic**. Test asserts trigger fires iff exact match.
  - **Resolution note.** The `Outcome` enum at `app/schemas/rejection.py:16` does NOT have a `NEEDS_REVIEW` variant — `pass`/`fail`/`insufficient_evidence`/`not_applicable`/`timeout`/`error` only. The orchestrator trigger uses the rule's `reason_code` (which IS the primary semantic signal), not the outcome enum.
- **D-017 min-aggregation** (T8 `aggregation.py`). `disposition_confidence.numeric = min(field.field_confidence.numeric for field in envelope.fields)`. The `band` is `confidence.to_band(numeric)`. Empty fields → `("low", 0.0)`.
- **FR-303 wire vestige.** `app/schemas/wire/disposition.py::AISuggestionWire.model_disposition` is a pre-FR-303 wire field. The Evaluator ALWAYS sets `model_disposition=None` because the orchestrator's `Refined` carries no disposition. The wire schema is unchanged in E5.
- **`AISuggestionWire.task` mapping.** Wire enum: `{"brand_borderline", "reasoning_enrichment", "ocr_reconciliation"}`; orchestrator names: `{"brand_disambig", "reasoning_enrich", "ocr_reconcile"}`. Mapping constant `_TASK_WIRE_NAME` lives in `envelope_builder.py`.
- **Whole-eval timeout (5 s, NFR-PERF-001)** (T14). Wrap `_evaluate_inner()` in `asyncio.wait_for(..., timeout=5.0)`. On `asyncio.TimeoutError` → return short-circuit envelope with `reason_code="ENGINE.SLA.TIMEOUT"` and the partial timeline. The Evaluator stores `_last_timeline` so the timeout branch can read partial state.
- **Chokepoint exception map** (T14). The Evaluator's outermost `except` distinguishes (a) typed engine exceptions → mapped to specific FR-900-series codes; (b) `asyncio.TimeoutError` → `ENGINE.SLA.TIMEOUT`; (c) generic `Exception` → re-raise (programmer error). The mapping is in a single private dict `_EXCEPTION_TO_REASON_CODE`. Vision call + rules call wrapped in their own try/except that records to `timeline.failures`.
- **Canonical JSON.** Hashing uses `json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")` then `hashlib.sha256(...).hexdigest()` (full 64 chars). `input_hash = sha256(canonical_app ‖ image_bytes)`; `output_hash = sha256(canonical_envelope_with_hashes_zeroed)`. Tested for byte-equality across two interpreter sessions (subprocess test).
- **Cache key.** `cache_key = sha256(canonical_app ‖ image_bytes)` — same as `input_hash`. On hit, the cached envelope's `evaluation_id` is REPLACED with the new request's UUID via `model_copy(update=...)`.
- **Inference-dep ban.** No `app/services/` file imports `openai`, `anthropic`, `vllm`, or `xgrammar`. The orchestrator-isolation grep (E4-T16) covers `app/`; E5 inherits.
- **Helpers are imported at module top** by `evaluator.py`. The Evaluator's body delegates to them; tests can substitute helpers via DI by patching the module-level imports if needed (but the cleaner path is to test helpers directly — that's why they're separate modules).

### `_stub_label()` — canonical test Label factory

All E5 tests construct `Label` via this helper to keep recipes synchronized with the locked E3 schema (`app/schemas/label.py`: `label_id`, `batch_id`, `image_bytes`, `content_type`, `face_tag`, `dimensions=None`). The wire-side `label_ref` (carried in `DispositionEnvelope`) is sourced from `Label.label_id` in production envelope-builder assembly — translation at the wire boundary, not in the test recipes. (The audit record has no `request_id` field; it identifies via `evaluation_id` + `input_hash` + `output_hash`.)

```python
# tests/conftest.py (or per-test inline)
from app.schemas.label import Label


def _stub_label(
    *,
    label_id: str = "lbl-test",
    batch_id: str = "B-test",
    image_bytes: bytes = b"\x89PNG\r\n\x1a\n",
    content_type: str = "image/png",
    face_tag: str = "front",
    dimensions=None,
) -> Label:
    return Label(
        label_id=label_id,
        batch_id=batch_id,
        image_bytes=image_bytes,
        content_type=content_type,
        face_tag=face_tag,
        dimensions=dimensions,
    )
```

Tests construct labels as `_stub_label()` (defaults) or `_stub_label(label_id="custom", face_tag="back")` for customization. **Never construct `Label(label_ref=..., mime_type=...)` — those are wire-side names, not the internal envelope shape.** If a specific test exercises the `Label.dimensions` field, pass `dimensions=Dimensions(width_px=..., height_px=..., dpi=...)`; otherwise default to `dimensions=None`.

**Where the factory lives.** The first task that needs it (T4 — fakes-vision) appends `_stub_label` to the existing `tests/conftest.py`. Subsequent tasks `from tests.conftest import _stub_label`. T4's pre-flight check: if `_stub_label` is already defined in conftest (e.g. an earlier task slipped it in via Rule 1-3), reuse the existing definition.

### Wire `label_ref` sourcing

Production envelope-builder (T11) and audit recorder (T6) source the wire `label_ref` (and audit-side request identifiers) from `Label.label_id`:

```python
# app/services/envelope_builder.py
DispositionEnvelope(
    label_ref=label.label_id,  # wire-side name <- internal name
    ...
)

# app/services/audit.py — _input_hash + assemble use label.label_id
```

There is no `label.label_ref` attribute; the translation is one-way at the wire boundary.

---

## Task 0a: app/rules/__init__.py — build_rule_engine factory

**Files:**
- Modify: `app/rules/__init__.py` (add `build_rule_engine`)
- Modify: `app/config.py` (add `rules_root: Path` setting if absent — mirror existing alias style)
- Test: `tests/rules/test_build_rule_engine.py` (new)

Wave 0 root. No deps. Eliminates the deferred-BLOCK risk in T15 (plan-review iter-1 Blocker #3).

- [ ] **Step 1: Write the failing test**

```python
# tests/rules/test_build_rule_engine.py
"""build_rule_engine(settings) — constructs YamlRuleEngine after forcing
validator-decorator imports (per loader.py:24-29 forward note)."""
from pathlib import Path

import pytest

from app.config import Settings
from app.rules import build_rule_engine
from app.rules._validators import VALIDATOR_REGISTRY
from app.rules.yaml_engine import YamlRuleEngine


@pytest.fixture
def rules_root_env(monkeypatch):
    """Pin RULES_ROOT to an absolute path so neither test depends on the
    interpreter's import-time CWD (Settings.rules_root default resolves
    `Path('rules')` at module load — see iter-2 Warning #3)."""
    monkeypatch.setenv("RULES_ROOT", str(Path("rules").resolve()))


def test_build_rule_engine_returns_yaml_engine(rules_root_env):
    engine = build_rule_engine(Settings())
    assert isinstance(engine, YamlRuleEngine)


def test_build_rule_engine_populates_validator_registry(rules_root_env):
    engine = build_rule_engine(Settings())
    # Force-import side effect must register at least one validator.
    assert len(VALIDATOR_REGISTRY) >= 1
    # Engine carries a non-empty ruleset against the real fixtures.
    assert len(engine._ruleset.rules) >= 1
```

> **iter-2 Warning #3 fix.** Both tests now consume the `rules_root_env` fixture so neither relies on the interpreter's import-time CWD. The fixture can be promoted to `tests/rules/conftest.py` if more T0a-adjacent tests land later.

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/rules/test_build_rule_engine.py -q` → ImportError (no `build_rule_engine`).

- [ ] **Step 3: Implement**

```python
# app/rules/__init__.py
"""Rule-engine package. ``build_rule_engine`` is the single construction point
used by ``app/deps.py::build_evaluator`` (T15) and the healthz warm-up (T16).

Forces validator-decorator imports (per loader.py:24-29 forward note: the loader's
cross-check 6 reads ``VALIDATOR_REGISTRY`` which is populated by ``@register``
decorators at import time) before loading the ruleset, so registration is
guaranteed regardless of import order at FastAPI startup.
"""
from __future__ import annotations

import importlib
import pkgutil

from app.config import Settings
from app.rules.loader import YamlRuleLoader
from app.rules.yaml_engine import YamlRuleEngine


def build_rule_engine(settings: Settings) -> YamlRuleEngine:
    """Force-import every validator module, then load the ruleset and wrap it."""
    import app.rules._validators as _v
    for _, modname, _ in pkgutil.iter_modules(_v.__path__):
        importlib.import_module(f"{_v.__name__}.{modname}")
    ruleset = YamlRuleLoader().load(settings.rules_root)
    return YamlRuleEngine(ruleset)
```

If `Settings` doesn't already expose `rules_root: Path`, add it (mirror existing alias style):

```python
# app/config.py — add inside class Settings
from pathlib import Path  # if not already imported

rules_root: Path = Field(
    default=Path("rules").resolve(),
    alias="RULES_ROOT",
    description="Absolute path to the YAML rules directory (D-014).",
)
```

- [ ] **Step 4: Run focused → GREEN (2 passed)**

- [ ] **Step 5: Commit**

```bash
git add app/rules/__init__.py app/config.py tests/rules/test_build_rule_engine.py
git commit -m "feat(e5): build_rule_engine factory (force-imports validators, wires YamlRuleEngine)"
```

**TDD:** 1 cycle (RED → GREEN).
**Done:** test asserts `build_rule_engine(settings)` returns a `YamlRuleEngine` against the real `rules/` tree; `VALIDATOR_REGISTRY` is non-empty after the call (force-import worked); `engine._ruleset.rules` is non-empty.

---

## Task 0b: app/rules/engine.py + yaml_engine.py + context.py — RuleEngine.build_validator_context abstract method

**Files:**
- Modify: `app/rules/engine.py` (add abstract method `build_validator_context`)
- Modify: `app/rules/yaml_engine.py` (add concrete `build_validator_context` sourcing from `self._ruleset`)
- Create: `app/rules/context.py` (thin shim — preserves the importable free-function name for callers that prefer it; delegates to the engine method)
- Test: `tests/rules/test_build_validator_context.py` (new)

Wave 0 root. No deps. Eliminates the `ValidatorContext(label=...)` constructor mismatch (plan-review iter-1 Blocker #2) AND the new iter-2 Blocker (free-function helper accessing `engine._ruleset` failed against the abstract `RuleEngine` seam used by `FakeRuleEngine`). The Evaluator (T13/T14) constructs a per-evaluation `ValidatorContext` by calling `self._rules.build_validator_context(started_at_ms=...)` on the abstraction itself, so both `YamlRuleEngine` (production) and `FakeRuleEngine` (tests, T3) implement it directly. No more reaching into a private attribute through a free function.

> **iter-2 Blocker fix.** v0.3 introduced a free-function helper `build_validator_context(engine, ...)` that read `engine._ruleset`. The Evaluator's typed seam is the abstract `RuleEngine`; the unit-test `FakeRuleEngine` carries no `_ruleset`, so T13 Cycle C tests crashed with `AttributeError` before reaching `orch.refine`. v0.4 relocates context construction onto the `RuleEngine` ABC so the abstraction owns the contract; the concrete YAML engine implements it against `self._ruleset`; the fake (T3) implements it as a stub returning empty assets/tables and a placeholder version string.

- [ ] **Step 1: Write the failing test**

```python
# tests/rules/test_build_validator_context.py
"""RuleEngine.build_validator_context — abstract-method seam.

Validates the abstract method on the concrete YamlRuleEngine wired via T0a's
build_rule_engine factory: sources assets/decision_tables/engine_version off
the engine's private ruleset; supplies the per-evaluation clock from the
caller. The FakeRuleEngine implementation is exercised in T3's test
(test_fakes_orchestrator_rules.py) so this file stays focused on production.
"""
from app.config import Settings
from app.rules import build_rule_engine
from app.rules._validators import ValidatorContext
from app.rules.context import build_validator_context  # thin shim → engine method


def test_yaml_engine_build_validator_context_returns_validator_context():
    engine = build_rule_engine(Settings())
    ctx = engine.build_validator_context(started_at_ms=12345)
    assert isinstance(ctx, ValidatorContext)


def test_yaml_engine_build_validator_context_sources_from_ruleset():
    engine = build_rule_engine(Settings())
    ctx = engine.build_validator_context(started_at_ms=99)
    assert ctx.assets == engine._ruleset.assets
    assert ctx.decision_tables == engine._ruleset.decision_tables
    assert ctx.started_at_ms == 99
    assert ctx.engine_version  # non-empty (sourced from RuleSet.version)


def test_shim_delegates_to_engine_method():
    """The free-function shim is a one-line forwarder so existing recipes that
    prefer the free-function name still work — but the contract lives on the
    abstraction."""
    engine = build_rule_engine(Settings())
    via_method = engine.build_validator_context(started_at_ms=7)
    via_shim = build_validator_context(engine, started_at_ms=7)
    assert via_method == via_shim
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/rules/test_build_validator_context.py -q` → AttributeError (`RuleEngine` has no `build_validator_context`) and ModuleNotFoundError on `app.rules.context`.

- [ ] **Step 3: Implement**

Add the abstract method to the rule-engine ABC:

```python
# app/rules/engine.py — add the abstract method to class RuleEngine
from abc import ABC, abstractmethod

from app.rules._validators import ValidatorContext  # already imported


class RuleEngine(ABC):
    @abstractmethod
    async def evaluate(...): ...

    @abstractmethod
    def build_validator_context(self, *, started_at_ms: int) -> ValidatorContext:
        """Construct a per-evaluation ``ValidatorContext`` for this engine.

        Each subclass sources ``assets``, ``decision_tables``, and
        ``engine_version`` from whatever it has on hand; the caller (the
        Evaluator) supplies the per-evaluation wall-clock reference. Pulling
        construction onto the abstraction means tests (FakeRuleEngine) can
        return a stub without reaching into private state.
        """
        ...
```

Add the concrete implementation to `YamlRuleEngine`:

```python
# app/rules/yaml_engine.py — inside class YamlRuleEngine
    def build_validator_context(self, *, started_at_ms: int) -> ValidatorContext:
        rs = self._ruleset
        return ValidatorContext(
            assets=rs.assets,
            decision_tables=rs.decision_tables,
            started_at_ms=started_at_ms,
            engine_version=rs.version,
        )
```

Create the thin shim (kept so call sites that prefer the free-function name still resolve; the contract lives on the abstraction):

```python
# app/rules/context.py
"""Backward-compatible shim over ``RuleEngine.build_validator_context``.

The abstract method on ``RuleEngine`` (``app/rules/engine.py``) is the source
of truth for per-evaluation ``ValidatorContext`` construction. This module
preserves a free-function name for any caller that prefers it; everything
delegates to the engine method.
"""
from __future__ import annotations

from app.rules._validators import ValidatorContext
from app.rules.engine import RuleEngine


def build_validator_context(
    engine: RuleEngine, *, started_at_ms: int
) -> ValidatorContext:
    return engine.build_validator_context(started_at_ms=started_at_ms)
```

> **Schema note.** `RuleSet.version` (`app/schemas/rules.py:86`) is the engine-level version field; `RuleDefinition.rule_pack_version` is per-rule. Use `rs.version` in the YAML engine implementation. If a future schema change makes `version` ambiguous, source from `rs.rules[0].rule_pack_version` and document the change.

> **FakeRuleEngine in T3.** T3 (the orch + rules fakes task) MUST also implement `build_validator_context` returning a stub — `ValidatorContext(assets={}, decision_tables={}, started_at_ms=started_at_ms, engine_version="fake")`. T3's recipe is updated below to include this. Without that concrete override, `FakeRuleEngine` cannot instantiate (Python raises `TypeError: Can't instantiate abstract class`).

- [ ] **Step 4: Run focused → GREEN (3 passed)**

- [ ] **Step 5: Commit**

```bash
git add app/rules/engine.py app/rules/yaml_engine.py app/rules/context.py tests/rules/test_build_validator_context.py
git commit -m "feat(e5): RuleEngine.build_validator_context — abstract method + YAML impl + shim"
```

**TDD:** 1 cycle (RED → GREEN).
**Done:** test calls `engine.build_validator_context(started_at_ms=12345)` on the YAML engine wired via T0a, asserts the returned `ValidatorContext` has the ruleset's `assets`, `decision_tables`, the supplied clock, and non-empty `engine_version`; a third test asserts the free-function shim delegates byte-for-byte to the engine method.

---

## Task 1: app/services/engine_meta.py — EvaluationTimeline

**Files:**
- Create: `app/services/__init__.py` (empty package marker)
- Create: `app/services/engine_meta.py`
- Test: `tests/test_engine_meta_timeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine_meta_timeline.py
"""EvaluationTimeline — per-evaluation accumulator (D-018 source of truth)."""
import pytest

from app.services.engine_meta import EvaluationTimeline, EngineFailure


def test_timeline_constructs_with_evaluation_id():
    t = EvaluationTimeline(evaluation_id="EV-001")
    assert t.evaluation_id == "EV-001"
    assert t.vision_duration_ms == 0
    assert t.orchestrator_duration_ms == 0
    assert t.per_rule_durations == {}
    assert t.failures == []


def test_timeline_records_vision_duration():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.record_vision_done(123)
    assert t.vision_duration_ms == 123


def test_timeline_records_orchestrator_duration():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.record_orchestrator_done(456)
    assert t.orchestrator_duration_ms == 456


def test_timeline_records_per_rule_outcome():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.record_rule_done(rule_id="R-001", duration_ms=42, disposition="pass", evidence_ref="ev/R-001")
    assert t.per_rule_durations == {"R-001": 42}
    assert t.per_rule_dispositions == {"R-001": "pass"}
    assert t.per_rule_evidence_refs == {"R-001": "ev/R-001"}


def test_timeline_records_engine_failure():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.record_failure(reason_code="ENGINE.SLA.RULE_TIMEOUT", message="slow", exception_class="TimeoutError")
    assert len(t.failures) == 1
    f = t.failures[0]
    assert f.reason_code == "ENGINE.SLA.RULE_TIMEOUT"
    assert f.message == "slow"
    assert f.exception_class == "TimeoutError"


def test_timeline_finish_records_completed_at():
    from datetime import datetime, timezone

    t = EvaluationTimeline(evaluation_id="EV-001")
    assert t.completed_at is None
    t.finish(total_duration_ms=500)
    assert t.total_duration_ms == 500
    assert isinstance(t.completed_at, datetime)
    assert t.completed_at.tzinfo == timezone.utc


def test_engine_failure_is_frozen():
    import dataclasses

    f = EngineFailure(reason_code="ENGINE.RULE.UNKNOWN", message="x", exception_class="ValueError")
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.reason_code = "X"  # type: ignore[misc]
```

- [ ] **Step 2: Run focused → RED**

`uv run pytest tests/test_engine_meta_timeline.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement**

```python
# app/services/__init__.py
"""Application Service layer (Evaluator + Audit + Metrics + helpers)."""
```

```python
# app/services/engine_meta.py
"""EvaluationTimeline — per-evaluation accumulator. Source: ARCH §6.8 + D-018.

Both ``AuditRecorder.assemble`` and ``MetricsBuilder.build`` consume the same
``EvaluationTimeline`` instance constructed and mutated by ``Evaluator.evaluate``.
This is the ONE source of truth for per-evaluation timing + outcome data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class EngineFailure:
    """One typed engine-failure event captured during evaluation."""
    reason_code: str
    message: str
    exception_class: str


@dataclass
class EvaluationTimeline:
    """Mutable per-evaluation accumulator. Owned by the call frame of
    ``Evaluator.evaluate`` and consumed exactly twice (audit + metrics)."""

    evaluation_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_duration_ms: int = 0
    vision_duration_ms: int = 0
    orchestrator_duration_ms: int = 0
    per_rule_durations: dict[str, int] = field(default_factory=dict)
    per_rule_dispositions: dict[str, str] = field(default_factory=dict)
    per_rule_evidence_refs: dict[str, str] = field(default_factory=dict)
    rule_set_version: str = "unknown"
    model_version: str | None = None
    prompt_version: str | None = None
    failures: list[EngineFailure] = field(default_factory=list)

    def record_vision_done(self, duration_ms: int) -> None:
        self.vision_duration_ms = duration_ms

    def record_orchestrator_done(self, duration_ms: int) -> None:
        self.orchestrator_duration_ms = duration_ms

    def record_rule_done(self, *, rule_id: str, duration_ms: int, disposition: str, evidence_ref: str) -> None:
        self.per_rule_durations[rule_id] = duration_ms
        self.per_rule_dispositions[rule_id] = disposition
        self.per_rule_evidence_refs[rule_id] = evidence_ref

    def record_failure(self, *, reason_code: str, message: str, exception_class: str) -> None:
        self.failures.append(EngineFailure(reason_code=reason_code, message=message, exception_class=exception_class))

    def finish(self, total_duration_ms: int) -> None:
        self.total_duration_ms = total_duration_ms
        self.completed_at = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run focused → GREEN (7 passed)**

- [ ] **Step 5: Commit**

```bash
git add app/services/__init__.py app/services/engine_meta.py tests/test_engine_meta_timeline.py
git commit -m "feat(e5): EvaluationTimeline accumulator (single audit/metrics source)"
```

---

## Task 2: app/services/confidence.py — band mapping

**Files:**
- Create: `app/services/confidence.py`
- Test: `tests/test_confidence_band_mapping.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_confidence_band_mapping.py
"""Single-source numeric→band mapping (L1 §7 risk #5)."""
import pytest

from app.services.confidence import to_band


@pytest.mark.parametrize("numeric, expected", [
    (0.0, "low"),
    (0.49, "low"),
    (0.5, "medium"),
    (0.84, "medium"),
    (0.85, "high"),
    (0.92, "high"),
    (1.0, "high"),
])
def test_to_band_edges(numeric, expected):
    assert to_band(numeric) == expected


def test_to_band_monotonic():
    rank = {"low": 0, "medium": 1, "high": 2}
    last = -1
    for x in [i / 100 for i in range(0, 101)]:
        b = to_band(x)
        assert rank[b] >= last
        last = rank[b]


def test_to_band_rejects_out_of_range():
    with pytest.raises(ValueError):
        to_band(-0.01)
    with pytest.raises(ValueError):
        to_band(1.01)
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/confidence.py
"""Numeric → Band mapping. Single source of truth (L1 §7 risk #5).

Thresholds (inclusive on the higher band):
- numeric < 0.5  → "low"
- 0.5 ≤ x < 0.85 → "medium"
- 0.85 ≤ x ≤ 1.0 → "high"
"""
from __future__ import annotations

from typing import Literal

Band = Literal["low", "medium", "high"]


def to_band(numeric: float) -> Band:
    if numeric < 0.0 or numeric > 1.0:
        raise ValueError(f"numeric out of [0, 1]: {numeric!r}")
    if numeric >= 0.85:
        return "high"
    if numeric >= 0.5:
        return "medium"
    return "low"
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/confidence.py tests/test_confidence_band_mapping.py
git commit -m "feat(e5): single-source confidence band mapping"
```

---

## Task 3: tests/_fakes/{orchestrator,rules}.py — orchestrator + rules fakes

**Files:**
- Create: `tests/_fakes/__init__.py` (empty)
- Create: `tests/_fakes/orchestrator.py`
- Create: `tests/_fakes/rules.py`
- Test: `tests/test_fakes_orchestrator_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fakes_orchestrator_rules.py
"""Fakes must conform to the real seams' interfaces."""
import inspect

import pytest

from app.orchestrator.base import Orchestrator
from app.rules.engine import RuleEngine
from app.schemas.application import Application
from app.schemas.refined import Refined
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine


def test_fake_orchestrator_subclasses_orchestrator():
    assert issubclass(FakeOrchestrator, Orchestrator)


def test_fake_orchestrator_refine_is_coroutine():
    assert inspect.iscoroutinefunction(FakeOrchestrator.refine)


@pytest.mark.asyncio
async def test_fake_orchestrator_returns_canned_refined():
    canned = Refined(evaluation_id="EV-001")
    fake = FakeOrchestrator(refined_outputs=[canned])
    out = await fake.refine(application=Application(application_id="A", evaluation_id="EV-001"), observations=[], validation_results=[])
    assert out == canned
    assert fake.call_count == 1


@pytest.mark.asyncio
async def test_fake_orchestrator_can_raise_on_nth_call():
    fake = FakeOrchestrator(refined_outputs=[Refined(evaluation_id="EV-001")], raise_on_call=1)
    with pytest.raises(RuntimeError):
        await fake.refine(application=Application(application_id="A", evaluation_id="EV-001"), observations=[], validation_results=[])


def test_fake_rule_engine_subclasses_rule_engine():
    assert issubclass(FakeRuleEngine, RuleEngine)


@pytest.mark.asyncio
async def test_fake_rule_engine_returns_canned_results():
    from app.schemas.expected import BeverageClass
    from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult

    em = EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)
    canned = (
        ValidationResult(
            rule_id="R-001", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
            outcome=Outcome.PASS, severity=Severity.INFO, aggregated_confidence=1.0, engine_meta=em,
        ),
    )
    fake = FakeRuleEngine(results=canned)
    out = await fake.evaluate(observations=[], expected=[], context=None)  # type: ignore[arg-type]
    assert out == canned


def test_fake_rule_engine_build_validator_context_returns_stub():
    """T0b adds an abstract ``build_validator_context`` to ``RuleEngine``;
    the fake must implement it so `FakeRuleEngine(...)` is instantiable
    and the Evaluator can call `self._rules.build_validator_context(...)`
    against the abstraction in T13/T14."""
    from app.rules._validators import ValidatorContext

    fake = FakeRuleEngine(results=())
    ctx = fake.build_validator_context(started_at_ms=42)
    assert isinstance(ctx, ValidatorContext)
    assert ctx.assets == {}
    assert ctx.decision_tables == {}
    assert ctx.started_at_ms == 42
    assert ctx.engine_version == "fake"
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# tests/_fakes/__init__.py
"""Test fakes for E5 evaluator unit tests."""
```

```python
# tests/_fakes/orchestrator.py
from __future__ import annotations

from typing import Sequence

from app.orchestrator.base import Orchestrator
from app.schemas.application import Application
from app.schemas.extracted import FieldObservation
from app.schemas.refined import Refined
from app.schemas.rejection import ValidationResult


class FakeOrchestrator(Orchestrator):
    def __init__(self, *, refined_outputs: Sequence[Refined] = (), raise_on_call: int | None = None) -> None:
        self._outputs = list(refined_outputs)
        self._raise_on = raise_on_call
        self.call_count = 0

    async def ensure_client(self) -> None:
        return None

    async def refine(
        self,
        application: Application,
        observations: list[FieldObservation],
        validation_results: list[ValidationResult],
    ) -> Refined:
        self.call_count += 1
        if self._raise_on is not None and self.call_count == self._raise_on:
            raise RuntimeError("fake orchestrator scheduled failure")
        if not self._outputs:
            return Refined(evaluation_id=getattr(application, "evaluation_id", "EV-fake"))
        return self._outputs.pop(0)
```

```python
# tests/_fakes/rules.py
from __future__ import annotations

from typing import Sequence

from app.rules._validators import ValidatorContext
from app.rules.engine import RuleEngine
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import ValidationResult


class FakeRuleEngine(RuleEngine):
    def __init__(self, *, results: tuple[ValidationResult, ...] = ()) -> None:
        self._results = results

    async def evaluate(
        self,
        observations: Sequence[FieldObservation],
        expected: Sequence[ExpectedValue],
        context,  # type: ignore[no-untyped-def]
    ) -> tuple[ValidationResult, ...]:
        return self._results

    def build_validator_context(self, *, started_at_ms: int) -> ValidatorContext:
        # Stub: empty assets/tables + placeholder engine_version. Sufficient
        # for any test that doesn't exercise asset-driven validators.
        return ValidatorContext(
            assets={},
            decision_tables={},
            started_at_ms=started_at_ms,
            engine_version="fake",
        )
```

- [ ] **Step 4: Run focused → GREEN (7 passed)**

- [ ] **Step 5: Commit**

```bash
git add tests/_fakes/__init__.py tests/_fakes/orchestrator.py tests/_fakes/rules.py tests/test_fakes_orchestrator_rules.py
git commit -m "test(e5): injectable Orchestrator + RuleEngine fakes"
```

---

## Task 4: tests/_fakes/vision.py — VisionExtractor fake

**Files:**
- Create: `tests/_fakes/vision.py`
- Modify: `tests/conftest.py` (append `_stub_label` factory per Conventions §)
- Test: `tests/test_fakes_vision.py`

> **iter-1 fix (Blocker #4):** the legibility short-circuit moved off `vision.needs_better_photo` (fake-only attribute, not on the real `VisionExtractor` Protocol — `app/vision/base.py:15-21`) and onto `app.vision.quality.assess(label)`. The fake now matches the Protocol exactly: `extract()` + `ensure_loaded()` only.
>
> **iter-1 fix (Blocker #1):** T4 is also the first task that needs `_stub_label`, so it appends the factory (per Conventions §`_stub_label()`) to the existing `tests/conftest.py`. Downstream tasks (T6, T11, T13, T14, T15, T16, T17, T18, T19, T20) `from tests.conftest import _stub_label`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fakes_vision.py
"""FakeVisionExtractor — Protocol-compatible (extract + ensure_loaded)."""
import pytest

from app.schemas.extracted import FieldObservation
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label  # canonical Label factory (Conventions §)


def test_fake_vision_satisfies_protocol():
    from app.vision.base import VisionExtractor
    fake = FakeVisionExtractor(observations=[])
    assert isinstance(fake, VisionExtractor)


@pytest.mark.asyncio
async def test_fake_vision_returns_canned():
    obs: list[FieldObservation] = []
    fake = FakeVisionExtractor(observations=obs)
    result = await fake.extract(_stub_label())
    assert result == obs


@pytest.mark.asyncio
async def test_fake_vision_ensure_loaded_is_noop():
    fake = FakeVisionExtractor(observations=[])
    # Protocol method must exist and be awaitable.
    await fake.ensure_loaded()
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# tests/_fakes/vision.py
from __future__ import annotations

from typing import Sequence

from app.schemas.extracted import FieldObservation
from app.schemas.label import Label


class FakeVisionExtractor:
    """Protocol-compatible VisionExtractor stub. The legibility short-circuit
    is plumbed through ``app.vision.quality.assess`` (monkeypatched in tests),
    NOT through any fake-only attribute."""

    def __init__(self, *, observations: Sequence[FieldObservation] = ()) -> None:
        self._obs = list(observations)

    async def extract(self, label: Label) -> list[FieldObservation]:
        return list(self._obs)

    async def ensure_loaded(self) -> None:
        return None
```

- [ ] **Step 4: Run focused → GREEN (3 passed)**

- [ ] **Step 5: Commit**

```bash
git add tests/_fakes/vision.py tests/conftest.py tests/test_fakes_vision.py
git commit -m "test(e5): VisionExtractor fake + _stub_label factory (Protocol-compatible)"
```

---

## Task 5: app/services/metrics_builder.py — pure assembly

**Files:**
- Create: `app/services/metrics_builder.py`
- Test: `tests/test_metrics_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_metrics_builder.py
from app.schemas.metrics import Metrics
from app.services.engine_meta import EvaluationTimeline
from app.services.metrics_builder import MetricsBuilder


def test_build_returns_metrics():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.record_vision_done(100)
    t.record_orchestrator_done(200)
    t.record_rule_done(rule_id="R-001", duration_ms=10, disposition="pass", evidence_ref="r1")
    t.record_rule_done(rule_id="R-002", duration_ms=20, disposition="fail", evidence_ref="r2")
    t.finish(total_duration_ms=400)

    m = MetricsBuilder().build(t)
    assert isinstance(m, Metrics)
    assert m.total_duration_ms == 400
    assert m.vision_duration_ms == 100
    assert m.orchestrator_duration_ms == 200
    assert {(e.rule_id, e.duration_ms) for e in m.per_rule_durations_ms} == {
        ("R-001", 10), ("R-002", 20),
    }


def test_build_with_empty_per_rule():
    t = EvaluationTimeline(evaluation_id="EV-002")
    t.finish(total_duration_ms=1)
    m = MetricsBuilder().build(t)
    assert m.per_rule_durations_ms == ()


def test_build_is_pure_no_side_effects():
    t = EvaluationTimeline(evaluation_id="EV-003")
    t.record_vision_done(50)
    t.finish(total_duration_ms=60)
    builder = MetricsBuilder()
    assert builder.build(t) == builder.build(t)
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/metrics_builder.py
"""MetricsBuilder — pure assembly from EvaluationTimeline. Source: D-018."""
from __future__ import annotations

from app.schemas.metrics import Metrics, PerRuleDurationEntry
from app.services.engine_meta import EvaluationTimeline


class MetricsBuilder:
    def build(self, timeline: EvaluationTimeline) -> Metrics:
        per_rule = tuple(
            PerRuleDurationEntry(rule_id=rid, duration_ms=ms)
            for rid, ms in timeline.per_rule_durations.items()
        )
        return Metrics(
            total_duration_ms=timeline.total_duration_ms,
            per_rule_durations_ms=per_rule,
            vision_duration_ms=timeline.vision_duration_ms,
            orchestrator_duration_ms=timeline.orchestrator_duration_ms,
        )
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/metrics_builder.py tests/test_metrics_builder.py
git commit -m "feat(e5): MetricsBuilder pure-assembly from EvaluationTimeline"
```

---

## Task 6: app/services/audit.py — AuditRecorder + canonical hashing

**Files:**
- Create: `app/services/audit.py`
- Test: `tests/test_audit_recorder.py`
- Test: `tests/test_audit_metrics_split.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_audit_recorder.py
"""AuditRecorder — pure assembly + canonical hashing (ARCH §6.7 / §6.8)."""
import subprocess
import sys

from app.schemas.application import Application
from app.schemas.audit import AuditRecord
from app.services.audit import AuditRecorder, _canonical_json, _input_hash, _output_hash
from app.services.engine_meta import EvaluationTimeline
from tests.conftest import _stub_label  # Conventions §_stub_label()


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


def test_canonical_json_is_byte_stable():
    a = {"b": 2, "a": 1, "c": [3, 2, 1]}
    b = {"a": 1, "c": [3, 2, 1], "b": 2}
    assert _canonical_json(a) == _canonical_json(b)


def test_input_hash_is_deterministic():
    h1 = _input_hash(_stub_app(), _stub_label())
    h2 = _input_hash(_stub_app(), _stub_label())
    assert h1 == h2 and len(h1) == 64


def test_output_hash_is_deterministic():
    env_dict = {"evaluation_id": "EV-001", "disposition": "pass"}
    assert _output_hash(env_dict) == _output_hash(env_dict)
    assert len(_output_hash(env_dict)) == 64


def test_audit_assemble_returns_record():
    t = EvaluationTimeline(evaluation_id="EV-001", rule_set_version="rs-1.0")
    t.record_rule_done(rule_id="R-001", duration_ms=10, disposition="pass", evidence_ref="ev/R-001")
    t.finish(total_duration_ms=100)
    rec = AuditRecorder().assemble(
        timeline=t, application=_stub_app(), label=_stub_label(),
        envelope_for_hash={"disposition": "pass", "fields": []},
    )
    assert isinstance(rec, AuditRecord)
    assert rec.evaluation_id == "EV-001"
    assert rec.rule_set_version == "rs-1.0"
    assert len(rec.per_rule_trace) == 1
    assert rec.per_rule_trace[0].rule_id == "R-001"
    assert not hasattr(rec.per_rule_trace[0], "duration_ms")  # D-018


def test_input_hash_byte_stable_across_processes():
    code = """
from app.schemas.application import Application
from app.schemas.label import Label
app = Application(application_id="A-001", evaluation_id="EV-001")
label = Label(label_id="lbl-001", batch_id="B-001", image_bytes=b"fake-png",
              content_type="image/png", face_tag="front")
from app.services.audit import _input_hash
print(_input_hash(app, label))
"""
    r1 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    r2 = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert r1.returncode == 0 and r2.returncode == 0
    assert r1.stdout.strip() == r2.stdout.strip()
```

```python
# tests/test_audit_metrics_split.py
"""D-018: split blocks; both build from same timeline."""
from app.schemas.application import Application
from app.services.audit import AuditRecorder
from app.services.engine_meta import EvaluationTimeline
from app.services.metrics_builder import MetricsBuilder
from tests.conftest import _stub_label


def test_split_no_duration_in_audit_per_rule_trace():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.record_rule_done(rule_id="R-001", duration_ms=10, disposition="pass", evidence_ref="r1")
    t.finish(total_duration_ms=20)

    audit = AuditRecorder().assemble(
        timeline=t,
        application=Application(application_id="A", evaluation_id="EV-001"),
        label=_stub_label(),
        envelope_for_hash={"x": 1},
    )
    metrics = MetricsBuilder().build(t)

    assert audit.per_rule_trace[0].rule_id == "R-001"
    assert not hasattr(audit.per_rule_trace[0], "duration_ms")
    assert metrics.per_rule_durations_ms[0].duration_ms == 10
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/audit.py
"""AuditRecorder — pure assembly + canonical hashing.

input_hash  = sha256(canonical_application_json ‖ image_bytes)
output_hash = sha256(canonical_envelope_with_hashes_zeroed)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.schemas.application import Application
from app.schemas.audit import AuditRecord, PerRuleTraceEntry
from app.schemas.label import Label
from app.services.engine_meta import EvaluationTimeline


def _canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def _input_hash(application: Application, label: Label) -> str:
    app_bytes = _canonical_json(application.model_dump(mode="json"))
    return hashlib.sha256(app_bytes + label.image_bytes).hexdigest()


def _output_hash(envelope_for_hash: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(envelope_for_hash)).hexdigest()


class AuditRecorder:
    def assemble(
        self,
        *,
        timeline: EvaluationTimeline,
        application: Application,
        label: Label,
        envelope_for_hash: dict[str, Any],
    ) -> AuditRecord:
        per_rule = tuple(
            PerRuleTraceEntry(
                rule_id=rid,
                disposition=timeline.per_rule_dispositions.get(rid, "not_applicable"),  # type: ignore[arg-type]
                evidence_ref=timeline.per_rule_evidence_refs.get(rid, ""),
            )
            for rid in timeline.per_rule_durations.keys()
        )
        completed = timeline.completed_at or datetime.now(timezone.utc)
        return AuditRecord(
            evaluation_id=timeline.evaluation_id,
            rule_set_version=timeline.rule_set_version,
            model_version=timeline.model_version,
            prompt_version=timeline.prompt_version,
            input_hash=_input_hash(application, label),
            output_hash=_output_hash(envelope_for_hash),
            started_at=timeline.started_at,
            completed_at=completed,
            per_rule_trace=per_rule,
            overrides=(),
        )
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/audit.py tests/test_audit_recorder.py tests/test_audit_metrics_split.py
git commit -m "feat(e5): AuditRecorder + canonical input/output hashing (D-018, ARCH §6.7)"
```

---

## Task 7: app/services/disposition.py — pure disposition rule

**Files:**
- Create: `app/services/disposition.py`
- Test: `tests/test_disposition_rule.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_disposition_rule.py
"""L1 §10.3 honest-failure-mode invariant."""
import pytest

from app.schemas.expected import BeverageClass
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.disposition import compute_disposition


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


def _vr(outcome):
    return ValidationResult(rule_id="R", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                            outcome=outcome, severity=Severity.INFO, aggregated_confidence=0.9, engine_meta=_em())


@pytest.mark.parametrize("outcomes, expected", [
    ((Outcome.PASS, Outcome.PASS), "pass"),
    ((Outcome.PASS, Outcome.NOT_APPLICABLE), "pass"),
    ((Outcome.PASS, Outcome.FAIL), "fail"),
    ((Outcome.FAIL, Outcome.NOT_APPLICABLE), "fail"),
    ((Outcome.PASS, Outcome.INSUFFICIENT_EVIDENCE), "needs_review"),
    ((Outcome.PASS, Outcome.TIMEOUT), "needs_review"),
    ((Outcome.PASS, Outcome.ERROR), "needs_review"),
    ((Outcome.FAIL, Outcome.TIMEOUT), "fail"),  # fail wins
])
def test_disposition_rule(outcomes, expected):
    assert compute_disposition(tuple(_vr(o) for o in outcomes)) == expected


def test_empty_results_route_to_needs_review():
    assert compute_disposition(()) == "needs_review"
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/disposition.py
"""Pure disposition rule. Source: L1 §10.3 / §2.1 step 7."""
from __future__ import annotations

from typing import Iterable, Literal

from app.schemas.rejection import Outcome, ValidationResult


Disposition = Literal["pass", "fail", "needs_review"]
_PASS_LIKE = {Outcome.PASS, Outcome.NOT_APPLICABLE}


def compute_disposition(results: Iterable[ValidationResult]) -> Disposition:
    """fail iff any FAIL; pass iff every PASS or NOT_APPLICABLE; else needs_review.
    Empty results → needs_review (engine produced nothing — honest failure)."""
    results = tuple(results)
    if not results:
        return "needs_review"
    if any(r.outcome == Outcome.FAIL for r in results):
        return "fail"
    if all(r.outcome in _PASS_LIKE for r in results):
        return "pass"
    return "needs_review"
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/disposition.py tests/test_disposition_rule.py
git commit -m "feat(e5): pure compute_disposition (fail > needs_review > pass)"
```

---

## Task 8: app/services/aggregation.py — pure D-017 min-aggregation

**Files:**
- Create: `app/services/aggregation.py`
- Test: `tests/test_confidence_aggregation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_confidence_aggregation.py
"""D-017: min-aggregation across envelope fields."""
from app.schemas.wire.disposition import (
    AISuggestionWire, ConfidenceBand, FieldEvidenceWire, FieldFindingWire, RuleFindingWire,
)
from app.services.aggregation import min_aggregate_confidence


def _field(name, numeric, band):
    return FieldFindingWire(
        field_name=name, extracted_value="x", expected_value="x",
        evidence=FieldEvidenceWire(bbox=(0, 0, 10, 10), crop_ref="c", extraction_confidence=numeric),
        rule_findings=(RuleFindingWire(rule_id="R", cfr_citation="27 CFR §x",
                                       disposition="pass", reason_code="OK", plain_language_explanation="ok"),),
        ai_suggestion=AISuggestionWire(present=False),
        field_confidence=ConfidenceBand(band=band, numeric=numeric),
    )


def test_min_aggregation_across_fields():
    fields = (
        _field("brand_name", 0.95, "high"),
        _field("class_type", 0.6, "medium"),
        _field("alcohol_content", 0.4, "low"),
    )
    band, numeric = min_aggregate_confidence(fields)
    assert numeric == 0.4
    assert band == "low"


def test_empty_fields_returns_low_zero():
    band, numeric = min_aggregate_confidence(())
    assert band == "low" and numeric == 0.0
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/aggregation.py
"""Pure D-017 min-aggregation. Disposition confidence = min over per-field."""
from __future__ import annotations

from typing import Iterable

from app.schemas.wire.disposition import FieldFindingWire
from app.services.confidence import Band, to_band


def min_aggregate_confidence(fields: Iterable[FieldFindingWire]) -> tuple[Band, float]:
    fields = tuple(fields)
    if not fields:
        return ("low", 0.0)
    numeric = min(f.field_confidence.numeric for f in fields)
    return (to_band(numeric), numeric)
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/aggregation.py tests/test_confidence_aggregation.py
git commit -m "feat(e5): pure D-017 min-aggregate confidence"
```

---

## Task 9: app/services/patcher.py — FR-303-safe patcher (the canary)

**Files:**
- Create: `app/services/patcher.py`
- Test: `tests/test_patcher_fr303.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_patcher_fr303.py
"""FR-303 patch invariant — orchestrator never overrides outcome/severity/reason_code.

This is the L1 §4 AC #10 enforcement (synthetic 'orchestrator disagrees' case)
and the §7 risk #2 mitigation."""
import pytest

from app.schemas.expected import BeverageClass
from app.schemas.refined import Refined, TaskSlice
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.patcher import patch_validation_results


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


def test_patcher_does_not_override_fail():
    """Orchestrator says 'match' but rule engine said FAIL — disposition stays FAIL."""
    fail_vr = ValidationResult(
        rule_id="X.brand.present", cfr_citation="27 CFR §5.42", beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.FAIL, severity=Severity.REJECT, reason_code="BRAND.NAME.MISMATCH",
        aggregated_confidence=0.95, engine_meta=_em(),
    )
    refined = Refined(evaluation_id="EV-001", tasks=(
        TaskSlice(task="brand_disambig", rule_id="X.brand.present",
                  payload={"decision": "match", "justification": "phonetic"}),
    ))
    patched = patch_validation_results((fail_vr,), refined)
    assert patched[0].outcome == Outcome.FAIL
    assert patched[0].reason_code == "BRAND.NAME.MISMATCH"
    assert patched[0].severity == Severity.REJECT


def test_patcher_annotates_message_with_orchestrator_view():
    vr = ValidationResult(
        rule_id="X.brand.present", cfr_citation="27 CFR §5.42", beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.INSUFFICIENT_EVIDENCE, severity=Severity.WARN,
        reason_code="BRAND.NAME.NEEDS_REVIEW",
        aggregated_confidence=0.6, engine_meta=_em(), message=None,
    )
    refined = Refined(evaluation_id="EV-001", tasks=(
        TaskSlice(task="brand_disambig", rule_id="X.brand.present",
                  payload={"decision": "match", "justification": "phonetic"}),
    ))
    patched = patch_validation_results((vr,), refined)
    assert patched[0].message is not None
    assert "brand_disambig" in patched[0].message.lower()


def test_patcher_unmatched_rule_returns_unchanged():
    """A ValidationResult with no matching slice returns unchanged."""
    vr = ValidationResult(
        rule_id="R-OTHER", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.PASS, severity=Severity.INFO,
        aggregated_confidence=0.9, engine_meta=_em(),
    )
    refined = Refined(evaluation_id="EV-001", tasks=())
    patched = patch_validation_results((vr,), refined)
    assert patched == (vr,)


def test_patcher_qualifier_only_slice_annotates_qualifier():
    """A slice with no payload but a qualifier annotates the message with the qualifier."""
    vr = ValidationResult(
        rule_id="X.brand.present", cfr_citation="27 CFR §5.42", beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.INSUFFICIENT_EVIDENCE, severity=Severity.WARN,
        aggregated_confidence=0.6, engine_meta=_em(),
    )
    refined = Refined(evaluation_id="EV-001", tasks=(
        TaskSlice(task="brand_disambig", rule_id="X.brand.present", qualifier="ENGINE.MODEL.UNAVAILABLE"),
    ))
    patched = patch_validation_results((vr,), refined)
    assert "ENGINE.MODEL.UNAVAILABLE" in (patched[0].message or "")
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/patcher.py
"""FR-303-safe ValidationResult patcher.

Touches ONLY ``message`` (annotation), ``aggregated_confidence`` (downward-only),
``evidence`` (additive). NEVER touches ``outcome``, ``severity``, ``reason_code``.

Asserted by ``tests/test_patcher_fr303.py`` even when orchestrator disagrees
with a rule-engine FAIL.
"""
from __future__ import annotations

from typing import Iterable

from app.schemas.refined import Refined
from app.schemas.rejection import ValidationResult


def patch_validation_results(
    results: Iterable[ValidationResult], refined: Refined,
) -> tuple[ValidationResult, ...]:
    slices_by_rule = {s.rule_id: s for s in refined.tasks if s.rule_id is not None}
    patched: list[ValidationResult] = []
    for vr in results:
        slice_ = slices_by_rule.get(vr.rule_id)
        if slice_ is None:
            patched.append(vr)
            continue
        annotation = (
            f"orchestrator/{slice_.task} note: "
            + (str(slice_.payload) if slice_.payload else f"qualifier={slice_.qualifier}")
        )
        new_message = (vr.message + " | " + annotation) if vr.message else annotation
        # FR-303: outcome / severity / reason_code untouched.
        patched.append(vr.model_copy(update={"message": new_message}))
    return tuple(patched)
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/patcher.py tests/test_patcher_fr303.py
git commit -m "feat(e5): FR-303-safe patcher — annotates message, never overrides outcome"
```

---

## Task 10: app/services/triggers.py — pure orchestrator-trigger predicate

**Files:**
- Create: `app/services/triggers.py`
- Test: `tests/test_triggers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_triggers.py
"""Exact orchestrator-trigger predicate (L1 §7 risk #2)."""
from app.schemas.expected import BeverageClass
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.triggers import should_invoke_orchestrator


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


def _vr(reason_code: str | None):
    return ValidationResult(
        rule_id="X.brand.present", cfr_citation="27 CFR §5.42", beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.INSUFFICIENT_EVIDENCE, severity=Severity.WARN, reason_code=reason_code,
        aggregated_confidence=0.6, engine_meta=_em(),
    )


def test_trigger_fires_on_brand_needs_review():
    assert should_invoke_orchestrator((_vr("BRAND.NAME.NEEDS_REVIEW"),)) is True


def test_trigger_does_not_fire_on_unrelated_code():
    assert should_invoke_orchestrator((_vr("BRAND.NAME.MISSING"),)) is False
    assert should_invoke_orchestrator((_vr(None),)) is False


def test_trigger_empty_results_no_fire():
    assert should_invoke_orchestrator(()) is False


def test_trigger_multi_result_fires_on_any_match():
    pass_vr = ValidationResult(
        rule_id="R-OK", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.PASS, severity=Severity.INFO, aggregated_confidence=0.95, engine_meta=_em(),
    )
    assert should_invoke_orchestrator((pass_vr, _vr("BRAND.NAME.NEEDS_REVIEW"))) is True
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/triggers.py
"""Pure orchestrator-trigger predicate. Source: FR-300 / L1 §7 risk #2.

Exact predicate: any ValidationResult.reason_code == "BRAND.NAME.NEEDS_REVIEW".
Not heuristic. New trigger codes are added by extending the set; the test
in tests/test_triggers.py guards against silent regression.
"""
from __future__ import annotations

from typing import Iterable

from app.schemas.rejection import ValidationResult

_ORCHESTRATOR_TRIGGER_CODES: frozenset[str] = frozenset({"BRAND.NAME.NEEDS_REVIEW"})


def should_invoke_orchestrator(results: Iterable[ValidationResult]) -> bool:
    return any(vr.reason_code in _ORCHESTRATOR_TRIGGER_CODES for vr in results)
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/triggers.py tests/test_triggers.py
git commit -m "feat(e5): pure orchestrator-trigger predicate (FR-300 exact match)"
```

---

## Task 11: app/services/envelope_builder.py — pure envelope assembly

**Files:**
- Create: `app/services/envelope_builder.py`
- Test: `tests/test_envelope_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_envelope_builder.py
"""Pure envelope assembly — success path + short-circuit."""
from app.schemas.application import Application
from app.schemas.wire.disposition import DispositionEnvelope
from app.services.audit import AuditRecorder
from app.services.engine_meta import EvaluationTimeline
from app.services.envelope_builder import build_short_circuit_envelope, build_success_envelope
from app.services.metrics_builder import MetricsBuilder
from tests.conftest import _stub_label  # Conventions §_stub_label()


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


def test_build_short_circuit_envelope():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.finish(total_duration_ms=10)
    env = build_short_circuit_envelope(
        application=_stub_app(), label=_stub_label(), timeline=t,
        reason_code="WARNING.LEGIBILITY.NEEDS_BETTER_PHOTO",
        audit=AuditRecorder().assemble(timeline=t, application=_stub_app(), label=_stub_label(),
                                       envelope_for_hash={"x": 1}),
        metrics=MetricsBuilder().build(t),
    )
    assert isinstance(env, DispositionEnvelope)
    assert env.disposition == "needs_review"
    assert env.evaluation_id == "EV-001"
    rule_ids = {entry.rule_id for entry in env.audit_trail.per_rule_trace}
    # Short-circuit envelope's per_rule_trace surfaces the reason code as a
    # synthetic entry so reviewers see why the engine routed here.
    assert "WARNING.LEGIBILITY.NEEDS_BETTER_PHOTO" in rule_ids


def test_build_success_envelope_minimal():
    t = EvaluationTimeline(evaluation_id="EV-001")
    t.finish(total_duration_ms=10)
    env = build_success_envelope(
        application=_stub_app(), label=_stub_label(), timeline=t,
        disposition="pass", fields=(),
        audit=AuditRecorder().assemble(timeline=t, application=_stub_app(), label=_stub_label(),
                                       envelope_for_hash={"x": 1}),
        metrics=MetricsBuilder().build(t),
    )
    assert env.disposition == "pass"
    assert env.evaluation_id == "EV-001"
    # Empty fields → ("low", 0.0) for disposition_confidence per aggregation.py
    assert env.disposition_confidence.numeric == 0.0
    assert env.disposition_confidence.band == "low"
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/envelope_builder.py
"""Pure envelope assembly — success path + short-circuit path.

No I/O, no clock; takes a pre-built AuditRecord + Metrics so audit/metrics
ownership stays clean.
"""
from __future__ import annotations

from typing import Iterable

from app.schemas.application import Application
from app.schemas.audit import AuditRecord, PerRuleTraceEntry
from app.schemas.label import Label
from app.schemas.metrics import Metrics
from app.schemas.wire.disposition import ConfidenceBand, DispositionEnvelope, FieldFindingWire
from app.services.aggregation import min_aggregate_confidence
from app.services.engine_meta import EvaluationTimeline


# Wire-shape vestige (PRD §6.2): orchestrator task names → wire enum.
_TASK_WIRE_NAME = {
    "brand_disambig": "brand_borderline",
    "reasoning_enrich": "reasoning_enrichment",
    "ocr_reconcile": "ocr_reconciliation",
}


def build_success_envelope(
    *,
    application: Application,
    label: Label,
    timeline: EvaluationTimeline,
    disposition: str,
    fields: Iterable[FieldFindingWire],
    audit: AuditRecord,
    metrics: Metrics,
) -> DispositionEnvelope:
    fields_t = tuple(fields)
    band, numeric = min_aggregate_confidence(fields_t)
    return DispositionEnvelope(
        evaluation_id=application.evaluation_id,
        label_ref=label.label_id,  # wire-side name <- internal name (Conventions §)
        disposition=disposition,  # type: ignore[arg-type]
        disposition_confidence=ConfidenceBand(band=band, numeric=numeric),
        fields=fields_t,
        audit_trail=audit,
        metrics=metrics,
    )


def build_short_circuit_envelope(
    *,
    application: Application,
    label: Label,
    timeline: EvaluationTimeline,
    reason_code: str,
    audit: AuditRecord,
    metrics: Metrics,
) -> DispositionEnvelope:
    """Assemble a needs_review envelope when an upstream short-circuit fired
    (legibility, whole-eval timeout, total engine failure). Surfaces the
    reason code as a synthetic per_rule_trace entry so reviewers see why."""
    # Augment audit trail with the short-circuit reason if not already present.
    existing_ids = {e.rule_id for e in audit.per_rule_trace}
    if reason_code not in existing_ids:
        synthetic = PerRuleTraceEntry(
            rule_id=reason_code, disposition="needs_review",
            evidence_ref=f"engine_failure/{reason_code}",
        )
        augmented = audit.model_copy(update={"per_rule_trace": audit.per_rule_trace + (synthetic,)})
    else:
        augmented = audit
    return DispositionEnvelope(
        evaluation_id=application.evaluation_id,
        label_ref=label.label_id,  # wire-side name <- internal name (Conventions §)
        disposition="needs_review",
        disposition_confidence=ConfidenceBand(band="low", numeric=0.0),
        fields=(),
        audit_trail=augmented,
        metrics=metrics,
    )
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/envelope_builder.py tests/test_envelope_builder.py
git commit -m "feat(e5): pure envelope assembly (success + short-circuit)"
```

---

## Task 12: app/services/cache.py — SessionCache (NFR-DET-001)

**Files:**
- Create: `app/services/cache.py`
- Test: `tests/test_session_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_session_cache.py
"""SessionCache — bounded LRU keyed by canonical input hash."""
import pytest

from app.schemas.application import Application
from app.schemas.audit import AuditRecord
from app.schemas.label import Dimensions, Label
from app.schemas.metrics import Metrics
from app.schemas.wire.disposition import ConfidenceBand, DispositionEnvelope
from app.services.cache import SessionCache


def _stub_envelope(eid="EV-001"):
    from datetime import datetime, timezone
    return DispositionEnvelope(
        evaluation_id=eid, label_ref="lbl", disposition="pass",
        disposition_confidence=ConfidenceBand(band="high", numeric=1.0),
        fields=(),
        audit_trail=AuditRecord(
            evaluation_id=eid, rule_set_version="rs",
            input_hash="0" * 64, output_hash="0" * 64,
            started_at=datetime.now(timezone.utc), completed_at=datetime.now(timezone.utc),
            per_rule_trace=(),
        ),
        metrics=Metrics(total_duration_ms=0, per_rule_durations_ms=(),
                        vision_duration_ms=0, orchestrator_duration_ms=0),
    )


def test_cache_get_miss_returns_none():
    c = SessionCache(maxsize=2)
    assert c.get("nope") is None


def test_cache_put_then_get():
    c = SessionCache(maxsize=2)
    env = _stub_envelope()
    c.put("k1", env)
    assert c.get("k1") == env


def test_cache_evicts_lru_at_maxsize():
    c = SessionCache(maxsize=2)
    e1 = _stub_envelope("EV-1")
    e2 = _stub_envelope("EV-2")
    e3 = _stub_envelope("EV-3")
    c.put("k1", e1)
    c.put("k2", e2)
    c.put("k3", e3)  # evicts k1 (LRU)
    assert c.get("k1") is None
    assert c.get("k2") == e2
    assert c.get("k3") == e3


def test_cache_get_promotes_to_most_recent():
    c = SessionCache(maxsize=2)
    e1 = _stub_envelope("EV-1")
    e2 = _stub_envelope("EV-2")
    e3 = _stub_envelope("EV-3")
    c.put("k1", e1)
    c.put("k2", e2)
    c.get("k1")            # promote k1
    c.put("k3", e3)        # should evict k2 now (LRU)
    assert c.get("k1") == e1
    assert c.get("k2") is None


def test_cache_clear_removes_all():
    c = SessionCache(maxsize=2)
    c.put("k1", _stub_envelope())
    c.clear()
    assert c.get("k1") is None
    assert len(c) == 0
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/services/cache.py
"""SessionCache — bounded LRU keyed by canonical input hash.

Per NFR-DET-001: within a session, the same canonicalized input returns
the same envelope (with a refreshed evaluation_id at the call site).
Not persisted across process restarts (NFR-DET-002 out-of-scope).
"""
from __future__ import annotations

from collections import OrderedDict

from app.schemas.wire.disposition import DispositionEnvelope


class SessionCache:
    def __init__(self, *, maxsize: int = 128) -> None:
        self._maxsize = maxsize
        self._items: OrderedDict[str, DispositionEnvelope] = OrderedDict()

    def get(self, key: str) -> DispositionEnvelope | None:
        env = self._items.get(key)
        if env is not None:
            self._items.move_to_end(key)
        return env

    def put(self, key: str, envelope: DispositionEnvelope) -> None:
        self._items[key] = envelope
        self._items.move_to_end(key)
        while len(self._items) > self._maxsize:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/services/cache.py tests/test_session_cache.py
git commit -m "feat(e5): SessionCache bounded LRU (NFR-DET-001)"
```

---

## Task 13: app/services/evaluator.py — Evaluator core (4-cycle bundle)

**Files:**
- Create: `app/services/evaluator.py` (created Cycle A; mutated through D)
- Test: `tests/test_evaluator_skeleton.py` (Cycle A)
- Test: `tests/test_evaluator_legibility_shortcircuit.py` (Cycle B)
- Test: `tests/test_evaluator_orchestrator_paths.py` (Cycle C)
- Test: `tests/test_evaluator_happy_path.py` (Cycle D)

This is a 4-cycle bundle. Each cycle is one Red→Green→Commit on the same file. The Evaluator is THIN — it delegates to the helpers from T7-T12 and audit/metrics from T5/T6.

### Cycle A — skeleton + DI signature

- [ ] **Step A.1: Write the failing test**

```python
# tests/test_evaluator_skeleton.py
"""Evaluator skeleton — DI signature."""
import inspect

from app.services.evaluator import Evaluator


def test_evaluator_init_accepts_5_deps():
    sig = inspect.signature(Evaluator.__init__)
    params = list(sig.parameters.keys())
    for name in ("vision", "rules", "orchestrator", "settings", "cache"):
        assert name in params


def test_evaluate_is_coroutine():
    assert inspect.iscoroutinefunction(Evaluator.evaluate)


def test_evaluate_signature():
    sig = inspect.signature(Evaluator.evaluate)
    params = list(sig.parameters.keys())
    assert params == ["self", "application", "label"]
```

- [ ] **Step A.2: Run focused → RED**

- [ ] **Step A.3: Implement skeleton**

```python
# app/services/evaluator.py
"""Application Service chokepoint. Source: ARCH §4.2.2, E5 L1 §2.1.

Composes vision (E3), rule engine (E2), orchestrator (E4) into one
end-to-end evaluation behind ``POST /labels``.

Thin — all logic lives in helpers under ``app/services/`` (disposition,
aggregation, patcher, triggers, envelope_builder, audit, metrics_builder,
cache, engine_meta). The Evaluator's job is orchestration + chokepoint
exception routing (P4: every downstream exception → needs_review).
"""
from __future__ import annotations

from app.config import Settings
from app.orchestrator.base import Orchestrator
from app.rules.engine import RuleEngine
from app.schemas.application import Application
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope
from app.services.cache import SessionCache
from app.vision.base import VisionExtractor


class Evaluator:
    def __init__(
        self,
        *,
        vision: VisionExtractor,
        rules: RuleEngine,
        orchestrator: Orchestrator,
        settings: Settings,
        cache: SessionCache | None = None,
    ) -> None:
        self._vision = vision
        self._rules = rules
        self._orchestrator = orchestrator
        self._settings = settings
        self._cache = cache

    async def evaluate(self, application: Application, label: Label) -> DispositionEnvelope:
        raise NotImplementedError("Cycle A skeleton")
```

- [ ] **Step A.4: Run focused → GREEN (3 passed)**

- [ ] **Step A.5: Commit**

```bash
git add app/services/evaluator.py tests/test_evaluator_skeleton.py
git commit -m "feat(e5): Evaluator skeleton — DI signature"
```

### Cycle B — legibility short-circuit + happy-path delegation

> **iter-1 fix (Blocker #4):** the legibility short-circuit calls `app.vision.quality.assess(label)` (the real, pure module — `app/vision/quality.py:85`), not a fake-only attribute. `assess()` returns a `QualityReport(disposition: Literal["ok","needs_better_photo"], reason_code, dpi)` and works on any `Label`, so the short-circuit fires against real vision impls AND tests that monkeypatch `app.services.evaluator.assess_quality`.

- [ ] **Step B.1: Write the failing test**

```python
# tests/test_evaluator_legibility_shortcircuit.py
"""Quality.assess returns needs_better_photo → short-circuit to needs_review."""
import pytest

from app.config import Settings
from app.schemas.application import Application
from app.services.evaluator import Evaluator
from app.vision.quality import QualityReport
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label


@pytest.mark.asyncio
async def test_legibility_short_circuit(monkeypatch):
    # iter-2 Warning #4: stub uses the canonical WARNING.LEGIBILITY.* prefix
    # so unit-test reason codes match what `app.vision.quality.assess` emits
    # in production (LOW_RESOLUTION / GLARE / MOTION_BLUR / LOW_DPI).
    monkeypatch.setattr(
        "app.services.evaluator.assess_quality",
        lambda lbl: QualityReport(
            disposition="needs_better_photo",
            reason_code="WARNING.LEGIBILITY.LOW_DPI",
            dpi=72,
        ),
    )
    evaluator = Evaluator(vision=FakeVisionExtractor(observations=[]),
                          rules=FakeRuleEngine(results=()),
                          orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await evaluator.evaluate(
        application=Application(application_id="A-001", evaluation_id="EV-001"),
        label=_stub_label(),
    )
    assert envelope.disposition == "needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert "WARNING.LEGIBILITY.LOW_DPI" in rule_ids
```

- [ ] **Step B.2: Run focused → RED**

- [ ] **Step B.3: Implement Cycle B**

Add the import at the top of `evaluator.py`:

```python
from app.vision.quality import assess as assess_quality
```

Replace the `evaluate` body:

```python
    async def evaluate(self, application: Application, label: Label) -> DispositionEnvelope:
        from app.services.audit import AuditRecorder
        from app.services.engine_meta import EvaluationTimeline
        from app.services.envelope_builder import build_short_circuit_envelope, build_success_envelope
        from app.services.metrics_builder import MetricsBuilder
        import time

        t_total = time.monotonic()
        timeline = EvaluationTimeline(evaluation_id=application.evaluation_id)

        # Step 1: vision
        t0 = time.monotonic()
        observations = await self._vision.extract(label)
        timeline.record_vision_done(int((time.monotonic() - t0) * 1000))

        # Step 2: legibility short-circuit (L1 §2.1 step 2; FR-505/603)
        quality = assess_quality(label)
        if quality.disposition == "needs_better_photo":
            timeline.record_failure(
                reason_code=quality.reason_code,
                message=f"image quality insufficient: {quality.reason_code}",
                exception_class="N/A",
            )
            return self._short_circuit(application, label, timeline, quality.reason_code, t_total)

        # Step 3-4: rules (Cycle C)
        # Step 5-6: orchestrator + patching (Cycle C)
        # Step 7-10: assembly (Cycle D)
        timeline.finish(total_duration_ms=int((time.monotonic() - t_total) * 1000))
        envelope_for_hash = {"evaluation_id": application.evaluation_id, "disposition": "pass", "fields": []}
        audit = AuditRecorder().assemble(timeline=timeline, application=application, label=label,
                                         envelope_for_hash=envelope_for_hash)
        metrics = MetricsBuilder().build(timeline)
        return build_success_envelope(
            application=application, label=label, timeline=timeline,
            disposition="pass", fields=(), audit=audit, metrics=metrics,
        )

    def _short_circuit(self, application, label, timeline, reason_code: str, t_total: float):
        from app.services.audit import AuditRecorder
        from app.services.envelope_builder import build_short_circuit_envelope
        from app.services.metrics_builder import MetricsBuilder
        import time

        timeline.finish(total_duration_ms=int((time.monotonic() - t_total) * 1000))
        envelope_for_hash = {"evaluation_id": application.evaluation_id, "disposition": "needs_review",
                             "reason_code": reason_code}
        audit = AuditRecorder().assemble(timeline=timeline, application=application, label=label,
                                         envelope_for_hash=envelope_for_hash)
        metrics = MetricsBuilder().build(timeline)
        return build_short_circuit_envelope(
            application=application, label=label, timeline=timeline,
            reason_code=reason_code, audit=audit, metrics=metrics,
        )
```

- [ ] **Step B.4: Run focused → GREEN**

- [ ] **Step B.5: Commit**

```bash
git add app/services/evaluator.py tests/test_evaluator_legibility_shortcircuit.py
git commit -m "feat(e5): Evaluator vision + legibility short-circuit (steps 1-2)"
```

### Cycle C — rules + orchestrator paths (steps 3-6)

- [ ] **Step C.1: Write the failing test**

```python
# tests/test_evaluator_orchestrator_paths.py
"""Orchestrator trigger fires/doesn't fire correctly + patcher integrates."""
import pytest

from app.config import Settings
from app.schemas.application import Application
from app.schemas.expected import BeverageClass
from app.schemas.refined import Refined, TaskSlice
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.evaluator import Evaluator
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label  # Conventions §_stub_label()


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


@pytest.mark.asyncio
async def test_orchestrator_not_invoked_when_no_trigger():
    rules = FakeRuleEngine(results=tuple(
        ValidationResult(rule_id=f"R-{i}", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.PASS, severity=Severity.INFO, aggregated_confidence=0.95, engine_meta=_em())
        for i in range(3)
    ))
    orch = FakeOrchestrator()
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=orch, settings=Settings())
    await e.evaluate(application=Application(application_id="A", evaluation_id="EV-001"), label=_stub_label())
    assert orch.call_count == 0


@pytest.mark.asyncio
async def test_orchestrator_invoked_on_brand_needs_review():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="X.brand.present", cfr_citation="27 CFR §5.42",
                         beverage_class=BeverageClass.SPIRITS, outcome=Outcome.INSUFFICIENT_EVIDENCE,
                         severity=Severity.WARN, reason_code="BRAND.NAME.NEEDS_REVIEW",
                         aggregated_confidence=0.6, engine_meta=_em()),
    ))
    canned = Refined(evaluation_id="EV-001", tasks=(
        TaskSlice(task="brand_disambig", rule_id="X.brand.present",
                  payload={"decision": "match", "justification": "phonetic"}),
    ))
    orch = FakeOrchestrator(refined_outputs=[canned])
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=orch, settings=Settings())
    await e.evaluate(application=Application(application_id="A", evaluation_id="EV-001"), label=_stub_label())
    assert orch.call_count == 1
```

- [ ] **Step C.2: Run focused → RED**

- [ ] **Step C.3: Implement Cycle C — wire rules + orchestrator paths**

Insert after the legibility short-circuit (before the assembly):

```python
        # Step 3-4: rules
        # T0b: context construction is owned by the rule-engine abstraction
        # itself — we call the engine method, NOT a free function over a
        # private attribute. Both YamlRuleEngine and FakeRuleEngine implement
        # `build_validator_context`.
        started_at_ms = int(time.monotonic() * 1000)
        ctx = self._rules.build_validator_context(started_at_ms=started_at_ms)
        # iter-2 Warning #2 fix: forward expected_values from the Application
        # (additive optional field, defaults to empty tuple). T20's AC fixtures
        # populate it via per-fixture sidecar JSON; everywhere else it is empty.
        expected = tuple(application.expected_values)
        results = await self._rules.evaluate(observations, expected, ctx)

        # Step 5-6: orchestrator (conditional) + FR-303 patching
        from app.services.triggers import should_invoke_orchestrator
        from app.services.patcher import patch_validation_results
        if should_invoke_orchestrator(results):
            t_orch = time.monotonic()
            try:
                refined = await self._orchestrator.refine(application, list(observations), list(results))
                results = patch_validation_results(results, refined)
            except Exception as e:
                timeline.record_failure(
                    reason_code="ENGINE.MODEL.UNAVAILABLE",
                    message=str(e), exception_class=type(e).__name__,
                )
            finally:
                timeline.record_orchestrator_done(int((time.monotonic() - t_orch) * 1000))

        # Surface failures into per_rule_trace so AuditRecorder picks them up.
        for failure in timeline.failures:
            timeline.record_rule_done(rule_id=failure.reason_code, duration_ms=0,
                                      disposition="needs_review",
                                      evidence_ref=f"engine_failure/{failure.exception_class}")
```

> **iter-1 fix (Blocker #2):** the deferred-BLOCK mitigation has been replaced by Wave 0 task T0b (`app/rules/context.py::build_validator_context`), so the construction path is deterministic. If `build_validator_context` import fails at runtime, T0b is broken — fix T0b, not T13.

- [ ] **Step C.4: Run focused → GREEN**

- [ ] **Step C.5: Commit**

```bash
git add app/services/evaluator.py tests/test_evaluator_orchestrator_paths.py
git commit -m "feat(e5): Evaluator wires rules + orchestrator + FR-303 patcher (steps 3-6)"
```

### Cycle D — disposition + assembly + cache (steps 7-10)

- [ ] **Step D.1: Write the failing test**

```python
# tests/test_evaluator_happy_path.py
"""End-to-end via fakes — disposition + cache + envelope shape."""
import pytest

from app.config import Settings
from app.schemas.application import Application
from app.schemas.expected import BeverageClass
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.cache import SessionCache
from app.services.evaluator import Evaluator
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label  # Conventions §_stub_label()


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


@pytest.mark.asyncio
async def test_happy_path_pass_disposition():
    rules = FakeRuleEngine(results=tuple(
        ValidationResult(rule_id=f"R-{i}", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.PASS, severity=Severity.INFO, aggregated_confidence=1.0, engine_meta=_em())
        for i in range(3)
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules,
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=Application(application_id="A", evaluation_id="EV-001"), label=_stub_label())
    assert envelope.evaluation_id == "EV-001"
    assert envelope.disposition == "pass"
    assert envelope.audit_trail.input_hash != "0" * 64  # real hash
    assert envelope.audit_trail.output_hash != "0" * 64


@pytest.mark.asyncio
async def test_fail_disposition():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="R-1", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.FAIL, severity=Severity.REJECT, reason_code="X.FAIL.CASE",
                         aggregated_confidence=0.95, engine_meta=_em()),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules,
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=Application(application_id="A", evaluation_id="EV-001"), label=_stub_label())
    assert envelope.disposition == "fail"


@pytest.mark.asyncio
async def test_cache_hit_replaces_evaluation_id():
    cache = SessionCache(maxsize=8)
    rules = FakeRuleEngine(results=())
    vision_calls = []

    class CountingVision(FakeVisionExtractor):
        async def extract(self, label):
            vision_calls.append(label.label_id)
            return await super().extract(label)

    e = Evaluator(vision=CountingVision(observations=[]), rules=rules,
                  orchestrator=FakeOrchestrator(), settings=Settings(), cache=cache)
    label = _stub_label()
    e1 = await e.evaluate(application=Application(application_id="A", evaluation_id="EV-1"), label=label)
    e2 = await e.evaluate(application=Application(application_id="A", evaluation_id="EV-2"), label=label)

    assert len(vision_calls) == 1, "cache miss: vision called twice"
    assert e2.evaluation_id == "EV-2"
    assert e1.disposition == e2.disposition
```

- [ ] **Step D.2: Run focused → RED**

- [ ] **Step D.3: Implement Cycle D — full assembly + cache integration**

Replace the assembly section of `evaluate` (after Cycle C's failures-surface block) with:

```python
        # Step 7-8: disposition + per-rule timeline updates
        from app.services.disposition import compute_disposition
        for vr in results:
            disposition_label = (
                "pass" if vr.outcome == Outcome.PASS else
                "fail" if vr.outcome == Outcome.FAIL else
                "not_applicable" if vr.outcome == Outcome.NOT_APPLICABLE else
                "needs_review"
            )
            timeline.record_rule_done(rule_id=vr.rule_id, duration_ms=vr.engine_meta.elapsed_ms,
                                      disposition=disposition_label, evidence_ref=f"vr/{vr.rule_id}")
        disposition = compute_disposition(results)

        # Step 9-10: assembly
        from app.services.audit import AuditRecorder
        from app.services.envelope_builder import build_success_envelope
        from app.services.metrics_builder import MetricsBuilder

        timeline.finish(total_duration_ms=int((time.monotonic() - t_total) * 1000))
        envelope_for_hash = {
            "evaluation_id": application.evaluation_id,
            "label_ref": label.label_id,  # wire-side name <- internal name
            "disposition": disposition,
            "fields": [],
        }
        audit = AuditRecorder().assemble(timeline=timeline, application=application, label=label,
                                         envelope_for_hash=envelope_for_hash)
        metrics = MetricsBuilder().build(timeline)
        envelope = build_success_envelope(
            application=application, label=label, timeline=timeline,
            disposition=disposition, fields=(), audit=audit, metrics=metrics,
        )
        # T20 (AC fixture coverage) lands the per-field FieldFindingWire construction.
```

Also remove the Cycle B placeholder happy-path return (now superseded by the full assembly above).

Add cache integration at the TOP of `evaluate`:

```python
        # NFR-DET-001 cache check
        if self._cache is not None:
            from app.services.audit import _input_hash
            cache_key = _input_hash(application, label)
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached.model_copy(update={"evaluation_id": application.evaluation_id})
        else:
            cache_key = None
```

And cache write at the end (before `return envelope`):

```python
        if self._cache is not None and cache_key is not None:
            self._cache.put(cache_key, envelope)
        return envelope
```

Replace the import of `Outcome` at the top of `evaluator.py`:

```python
from app.schemas.rejection import Outcome
```

- [ ] **Step D.4: Run focused → GREEN**

Run full Evaluator test suite to confirm no regressions:
`uv run pytest tests/test_evaluator_skeleton.py tests/test_evaluator_legibility_shortcircuit.py tests/test_evaluator_orchestrator_paths.py tests/test_evaluator_happy_path.py -v`

- [ ] **Step D.5: Commit**

```bash
git add app/services/evaluator.py tests/test_evaluator_happy_path.py
git commit -m "feat(e5): Evaluator disposition + assembly + cache integration (steps 7-10)"
```

---

## Task 14: app/services/evaluator.py — Resilience (2-cycle bundle)

**Files:**
- Modify: `app/services/evaluator.py`
- Test: `tests/test_evaluator_timeouts.py` (Cycle A)
- Test: `tests/test_evaluator_chokepoint.py` (Cycle B)

### Cycle A — whole-eval timeout (FR-909)

- [ ] **Step A.1: Write the failing test**

```python
# tests/test_evaluator_timeouts.py
"""Whole-eval timeout (FR-909 ENGINE.SLA.TIMEOUT)."""
import asyncio

import pytest

from app.config import Settings
from app.schemas.application import Application
from app.services.evaluator import Evaluator
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label


@pytest.mark.asyncio
async def test_whole_eval_timeout_routes_to_needs_review():
    class SlowRules(FakeRuleEngine):
        async def evaluate(self, *a, **kw):
            await asyncio.sleep(10)
            return ()

    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=SlowRules(),
                  orchestrator=FakeOrchestrator(), settings=Settings())
    e._sla_seconds = 0.1
    envelope = await e.evaluate(
        application=Application(application_id="A", evaluation_id="EV-001"),
        label=_stub_label(),
    )
    assert envelope.disposition == "needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert "ENGINE.SLA.TIMEOUT" in rule_ids
```

- [ ] **Step A.2: Run focused → RED**

- [ ] **Step A.3: Implement Cycle A**

Refactor `Evaluator.evaluate` to extract the body into `_evaluate_inner`. Wrap with `asyncio.wait_for`:

```python
import asyncio

# ... inside class Evaluator:
    _DEFAULT_SLA_SECONDS = 5.0

    async def evaluate(self, application: Application, label: Label) -> DispositionEnvelope:
        # Cache hit short-circuit (Cycle D logic moves here)
        if self._cache is not None:
            from app.services.audit import _input_hash
            cache_key = _input_hash(application, label)
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached.model_copy(update={"evaluation_id": application.evaluation_id})
        else:
            cache_key = None

        sla = getattr(self, "_sla_seconds", self._DEFAULT_SLA_SECONDS)
        try:
            envelope = await asyncio.wait_for(self._evaluate_inner(application, label), timeout=sla)
        except asyncio.TimeoutError:
            envelope = self._timeout_envelope(application, label)

        if self._cache is not None and cache_key is not None:
            self._cache.put(cache_key, envelope)
        return envelope

    async def _evaluate_inner(self, application, label):
        # Move ALL the existing body of evaluate here (everything after the
        # cache check from Cycle D). Capture timeline as self._last_timeline
        # at the top so the timeout fallback can read partial state.
        from app.services.engine_meta import EvaluationTimeline
        timeline = EvaluationTimeline(evaluation_id=application.evaluation_id)
        self._last_timeline = timeline
        # ... (the rest of Cycle D's body verbatim)

    def _timeout_envelope(self, application, label):
        from app.services.audit import AuditRecorder
        from app.services.engine_meta import EvaluationTimeline
        from app.services.envelope_builder import build_short_circuit_envelope
        from app.services.metrics_builder import MetricsBuilder

        timeline = getattr(self, "_last_timeline", EvaluationTimeline(evaluation_id=application.evaluation_id))
        timeline.finish(total_duration_ms=timeline.total_duration_ms or 0)
        envelope_for_hash = {"evaluation_id": application.evaluation_id, "disposition": "needs_review",
                             "reason_code": "ENGINE.SLA.TIMEOUT"}
        audit = AuditRecorder().assemble(timeline=timeline, application=application, label=label,
                                         envelope_for_hash=envelope_for_hash)
        metrics = MetricsBuilder().build(timeline)
        return build_short_circuit_envelope(
            application=application, label=label, timeline=timeline,
            reason_code="ENGINE.SLA.TIMEOUT", audit=audit, metrics=metrics,
        )
```

- [ ] **Step A.4: Run focused → GREEN**

- [ ] **Step A.5: Commit**

```bash
git add app/services/evaluator.py tests/test_evaluator_timeouts.py
git commit -m "feat(e5): Evaluator whole-eval timeout (FR-909 ENGINE.SLA.TIMEOUT)"
```

### Cycle B — vision/rules chokepoint exception routing

- [ ] **Step B.1: Write the failing test**

```python
# tests/test_evaluator_chokepoint.py
"""P4 chokepoint: vision/rules exceptions route to needs_review."""
import pytest

from app.config import Settings
from app.schemas.application import Application
from app.services.evaluator import Evaluator
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label as _label  # alias keeps the existing name


@pytest.mark.asyncio
async def test_vision_exception_routes_to_needs_review():
    class FailingVision:
        async def extract(self, label):
            raise RuntimeError("vision boom")
        async def ensure_loaded(self):
            return None

    e = Evaluator(vision=FailingVision(), rules=FakeRuleEngine(results=()),  # type: ignore[arg-type]
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=Application(application_id="A", evaluation_id="EV-001"), label=_label())
    assert envelope.disposition == "needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert any("VISION" in c or "EXTRACTION" in c for c in rule_ids)


@pytest.mark.asyncio
async def test_rule_engine_exception_routes_to_needs_review():
    class FailingRules:
        async def evaluate(self, *a, **kw):
            raise RuntimeError("rules boom")

    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=FailingRules(),  # type: ignore[arg-type]
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=Application(application_id="A", evaluation_id="EV-001"), label=_label())
    assert envelope.disposition == "needs_review"
```

- [ ] **Step B.2: Run focused → RED**

- [ ] **Step B.3: Implement Cycle B — wrap vision + rules calls inside `_evaluate_inner`**

Replace the vision call with:

```python
        t0 = time.monotonic()
        try:
            observations = await self._vision.extract(label)
        except Exception as e:
            timeline.record_failure(reason_code="ENGINE.EXTRACTION.UNAVAILABLE",
                                    message=str(e), exception_class=type(e).__name__)
            observations = []
        timeline.record_vision_done(int((time.monotonic() - t0) * 1000))
```

Replace the rules call with (using the T0b abstract method on the engine):

```python
        # T0b: build_validator_context is an abstract method on RuleEngine —
        # YamlRuleEngine sources from self._ruleset; FakeRuleEngine returns a
        # stub. The Evaluator never reaches into a private attribute itself.
        try:
            ctx = self._rules.build_validator_context(
                started_at_ms=int(time.monotonic() * 1000)
            )
            expected = tuple(application.expected_values)  # iter-2 Warning #2
            results = await self._rules.evaluate(observations, expected, ctx)
        except Exception as e:
            timeline.record_failure(reason_code="ENGINE.RULES.UNAVAILABLE",
                                    message=str(e), exception_class=type(e).__name__)
            _logger.info(  # NFR-OBS-001: log every routed FR-900 event
                "engine_failure_routed",
                extra={
                    "reason_code": "ENGINE.RULES.UNAVAILABLE",
                    "evaluation_id": application.evaluation_id,
                    "exception_class": type(e).__name__,
                },
            )
            results = ()
```

> **iter-2 Warning #1 fix (NFR-OBS-001).** Every FR-900 routing event in the chokepoint also emits one structured log line via the module-level `_logger = logging.getLogger("app.services.evaluator")`. Apply the same `_logger.info("engine_failure_routed", extra={"reason_code": <code>, "evaluation_id": ..., "exception_class": ...})` pattern to the vision-exception branch (`ENGINE.EXTRACTION.UNAVAILABLE`), the timeout fallback (`ENGINE.SLA.TIMEOUT` in `_timeout_envelope`), the legibility short-circuit (`quality.reason_code` from Cycle B), and the orchestrator-exception branch (`ENGINE.MODEL.UNAVAILABLE` from Cycle C). The Cycle B done-criteria below assert at least one log line was emitted with the matching `reason_code` (use `caplog` from pytest's logging plugin: `assert any(r.reason_code == "ENGINE.RULES.UNAVAILABLE" for r in caplog.records)` after the call).

The `compute_disposition(())` call from T7 already routes empty results to `needs_review`, so the disposition is honest.

- [ ] **Cycle B done-criteria additions (NFR-OBS-001).** Both Cycle B tests assert that the routed FR-900 event also produced a structured log line with the matching `reason_code` extra. Use pytest's `caplog` fixture: at the top of each test, `caplog.set_level(logging.INFO, logger="app.services.evaluator")`; after `await e.evaluate(...)`, assert `any(getattr(r, "reason_code", None) for r in caplog.records)` is truthy and matches the expected code.

- [ ] **Step B.4: Run focused → GREEN**

- [ ] **Step B.5: Commit**

```bash
git add app/services/evaluator.py tests/test_evaluator_chokepoint.py
git commit -m "feat(e5): Evaluator chokepoint wraps vision + rules (FR-907/911/912)"
```

---

## Task 15: app/api/labels.py + app/deps.py + app/main.py — POST /labels

**Files:**
- Create: `app/api/labels.py`
- Modify: `app/deps.py` (additive — `build_evaluator`)
- Modify: `app/main.py` (register router)
- Test: `tests/test_post_labels_endpoint.py`

- [ ] **Step 1: Write the failing test**

> **iter-1 fix (Warning #5):** the happy-path test monkeypatches `build_vision_extractor` and `build_orchestrator` in `app.deps` so the endpoint is exercised against deterministic fakes. This removes the `nvidia-smi`-dependent path and decouples the smoke test from real OpenAI / local-CUDA latency. The AC-fixture E2E (real seams against canned recordings) lives in T20.

```python
# tests/test_post_labels_endpoint.py
"""POST /labels — multipart parsing, validation, delegation (deterministic)."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor


@pytest.fixture
def deterministic_seams(monkeypatch):
    """Wire fakes into the build_evaluator factory so the endpoint test
    exercises only the Application Service / serialization path."""
    monkeypatch.setattr(
        "app.deps.build_vision_extractor",
        lambda settings: FakeVisionExtractor(observations=[]),
    )
    monkeypatch.setattr(
        "app.deps.build_orchestrator",
        lambda settings: FakeOrchestrator(),
    )
    # Rules engine still real (cheap; loads YAML once); if a deterministic
    # rule path is needed for a specific test, monkeypatch build_rule_engine too.


def test_post_labels_happy_path(deterministic_seams):
    client = TestClient(app)
    payload = {"application_id": "A-001", "evaluation_id": "EV-001"}
    files = {
        "application": ("a.json", json.dumps(payload), "application/json"),
        "label": ("l.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"),
    }
    response = client.post("/labels", files=files)
    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_id"] == "EV-001"
    assert body["disposition"] in {"pass", "fail", "needs_review"}
    # disposition must carry a non-empty reason_code (P4 honest-failure).
    assert body["disposition"]  # placeholder — refine once envelope schema is final


def test_post_labels_rejects_tiff():
    client = TestClient(app)
    payload = {"application_id": "A-001", "evaluation_id": "EV-001"}
    files = {
        "application": ("a.json", json.dumps(payload), "application/json"),
        "label": ("l.tiff", b"II*\x00" + b"\x00" * 12, "image/tiff"),
    }
    response = client.post("/labels", files=files)
    assert response.status_code == 400


def test_post_labels_rejects_malformed_json():
    client = TestClient(app)
    files = {
        "application": ("a.json", "not-json", "application/json"),
        "label": ("l.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"),
    }
    response = client.post("/labels", files=files)
    assert response.status_code == 400
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement endpoint + DI factory**

```python
# app/api/labels.py
"""POST /labels — single-label evaluation endpoint."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import Settings
from app.deps import build_evaluator
from app.schemas.application import Application
from app.schemas.label import Label
from app.schemas.wire.disposition import DispositionEnvelope


router = APIRouter(tags=["evaluation"])

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def _detect_content_type(data: bytes) -> str | None:
    if data.startswith(_PNG_MAGIC):
        return "image/png"
    if data.startswith(_JPEG_MAGIC):
        return "image/jpeg"
    return None


def _get_settings() -> Settings:
    return Settings()


@router.post("/labels", response_model=DispositionEnvelope)
async def post_labels(
    application: UploadFile = File(...),
    label: UploadFile = File(...),
    settings: Settings = Depends(_get_settings),
) -> DispositionEnvelope:
    try:
        app_bytes = await application.read()
        app_obj = Application(**json.loads(app_bytes))
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"rejected_input: {e}")

    label_bytes = await label.read()
    content_type = _detect_content_type(label_bytes)
    if content_type is None:
        raise HTTPException(status_code=400, detail="rejected_input: unsupported MIME (only PNG/JPEG)")

    # Internal Label uses E3-locked field names; wire-side label_ref is sourced
    # from label_id by envelope_builder/audit (Conventions §wire label_ref sourcing).
    label_obj = Label(
        label_id=label.filename or "label",
        batch_id=app_obj.application_id,  # single-label flow: batch == application
        image_bytes=label_bytes,
        content_type=content_type,
        face_tag="front",
        dimensions=None,  # E3 quality.assess() reads DPI from the image itself
    )
    evaluator = build_evaluator(settings)
    return await evaluator.evaluate(application=app_obj, label=label_obj)
```

In `app/deps.py`, add (additive):

```python
def build_evaluator(settings: "Settings") -> "Evaluator":
    """Construct an Evaluator wired to all four real dependencies."""
    from app.rules import build_rule_engine  # T0a — Wave 0
    from app.services.cache import SessionCache
    from app.services.evaluator import Evaluator
    vision = build_vision_extractor(settings)
    rules = build_rule_engine(settings)
    orchestrator = build_orchestrator(settings)
    cache = SessionCache(maxsize=128)
    return Evaluator(vision=vision, rules=rules, orchestrator=orchestrator, settings=settings, cache=cache)
```

Register the router in `app/main.py`:

```python
from app.api import labels as labels_module
app.include_router(labels_module.router)
```

- [ ] **Step 4: Run focused → GREEN**

> **iter-1 fix (Blocker #3):** the deferred-BLOCK escalation has been replaced by Wave 0 task T0a. `build_rule_engine` is guaranteed to exist when T15 runs because T0a lands first. If `build_rule_engine` import fails, T0a is broken — fix T0a, not T15.

- [ ] **Step 5: Commit**

```bash
git add app/api/labels.py app/deps.py app/main.py tests/test_post_labels_endpoint.py
git commit -m "feat(e5): POST /labels endpoint + build_evaluator DI factory"
```

---

## Task 16: app/api/healthz.py — full warm-up sentinel

**Depends on:** T0a (`build_rule_engine`), T0b (`build_validator_context`), T14 (Evaluator), T15 (`build_evaluator`).

**Files:**
- Modify: `app/api/healthz.py`
- Test: `tests/test_healthz_warmup.py`

> **iter-1 fix (Warning #4):** T16 imports `build_evaluator` from `app/deps.py`, which is added by T15 — so T16 must run AFTER T15 to avoid a runtime symbol-resolution race. Moved from Wave 5 to Wave 6.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_healthz_warmup.py
"""/healthz upgraded — runs full sentinel pipeline against fixture-01."""
import time

from fastapi.testclient import TestClient

from app.main import app


def test_healthz_first_invocation_runs_warmup():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "warmup_ran" in body or "sentinel_disposition" in body


def test_healthz_warm_call_under_2s():
    client = TestClient(app)
    client.get("/healthz")  # warm
    t0 = time.monotonic()
    response = client.get("/healthz")
    elapsed = time.monotonic() - t0
    assert response.status_code == 200
    assert elapsed < 2.0, f"warm /healthz took {elapsed:.2f}s, expected < 2s"
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Upgrade `app/api/healthz.py`**

```python
"""GET /healthz — E5 upgrades to full warm-up sentinel."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from app.config import Settings


router = APIRouter(tags=["health"])
_logger = logging.getLogger("app.healthz")
_warmed: dict[str, bool] = {"done": False}


def _get_settings() -> Settings:
    return Settings()


@router.get("/healthz")
async def healthz(settings: Settings = Depends(_get_settings)) -> dict[str, object]:
    body: dict[str, object] = {
        "status": "ok",
        "version": settings.app_version,
        "mode": {"vision": settings.vision_mode, "orchestrator": settings.orchestrator_backend},
    }
    if not _warmed["done"]:
        try:
            from app.deps import build_evaluator
            from app.schemas.application import Application
            from app.schemas.label import Label

            evaluator = build_evaluator(settings)
            await evaluator._vision.ensure_loaded()
            await evaluator._orchestrator.ensure_client()
            fixture_path = Path("fixtures/01-spirits-clean/label.png")
            if fixture_path.exists():
                label = Label(
                    label_id="01-spirits-clean",
                    batch_id="warmup",
                    image_bytes=fixture_path.read_bytes(),
                    content_type="image/png",
                    face_tag="front",
                    dimensions=None,
                )
                application = Application(application_id="warmup", evaluation_id="warmup-EV")
                envelope = await evaluator.evaluate(application=application, label=label)
                body["sentinel_disposition"] = envelope.disposition
            body["warmup_ran"] = True
            _warmed["done"] = True
        except Exception as e:
            body["warmup_error"] = str(e)
            body["warmup_ran"] = False
    _logger.info("healthz_invoked", extra={"reason_code": "ENGINE.OK.NONE"})
    return body
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/api/healthz.py tests/test_healthz_warmup.py
git commit -m "feat(e5): /healthz full warm-up sentinel (fixture-01 pre-warm)"
```

---

## Task 17: app/api/raw.py — DEV_MODE-gated ring-buffer endpoint

**Files:**
- Create: `app/api/raw.py`
- Modify: `app/main.py` (append router registration after T15's)
- Test: `tests/test_raw_endpoint_dev_mode.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_raw_endpoint_dev_mode.py
"""GET /batches/.../calls — DEV_MODE-gated per ADR D-019."""
from fastapi.testclient import TestClient

from app.main import app


def test_raw_endpoint_404_when_dev_mode_off(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "false")
    client = TestClient(app)
    response = client.get("/batches/B-001/labels/L-001/calls")
    assert response.status_code == 404


def test_raw_endpoint_200_when_dev_mode_on(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    client = TestClient(app)
    response = client.get("/batches/B-001/labels/L-001/calls")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement**

```python
# app/api/raw.py
"""GET /batches/{batch_id}/labels/{label_id}/calls — DEV_MODE-gated (D-019)."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException


router = APIRouter(tags=["dev"])


def _dev_mode_on() -> bool:
    return os.environ.get("DEV_MODE", "false").lower() == "true"


@router.get("/batches/{batch_id}/labels/{label_id}/calls")
async def get_calls(batch_id: str, label_id: str) -> list[dict]:
    if not _dev_mode_on():
        raise HTTPException(status_code=404, detail="not found")
    # E5 returns empty list — actual ring-buffer population is via the
    # Evaluator → orchestrator path; tests can populate app.state.calls[label_id].
    return []
```

Append to `app/main.py`:

```python
from app.api import raw as raw_module
app.include_router(raw_module.router)
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add app/api/raw.py app/main.py tests/test_raw_endpoint_dev_mode.py
git commit -m "feat(e5): DEV_MODE-gated /batches/.../calls endpoint (D-019)"
```

---

## Task 18: tests/test_evaluator_failure_modes.py — full FR-900 series

**Files:**
- Test: `tests/test_evaluator_failure_modes.py`

- [ ] **Step 1: Write the parametrized test (FR-902, FR-903, FR-904, FR-905, FR-907, FR-908, FR-909, FR-910, FR-911, FR-912 — Web-layer FR-900/901 covered by T15's endpoint tests; FR-906 deferred — see Hard Scope Boundary)**

```python
# tests/test_evaluator_failure_modes.py
"""Full FR-900 series Evaluator-layer coverage."""
import asyncio

import pytest

from app.config import Settings
from app.schemas.application import Application
from app.schemas.expected import BeverageClass
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.evaluator import Evaluator
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label  # Conventions §_stub_label()


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


@pytest.mark.asyncio
async def test_fr902_conflicting_rules():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="R-A", cfr_citation="27 CFR §1", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.PASS, severity=Severity.INFO, aggregated_confidence=0.95, engine_meta=_em()),
        ValidationResult(rule_id="R-B", cfr_citation="27 CFR §2", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.FAIL, severity=Severity.REJECT, reason_code="X.CONFLICT.DETECTED",
                         aggregated_confidence=0.95, engine_meta=_em()),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "fail"


# iter-2 Warning #1: extend coverage to FR-903 / FR-904 / FR-905 / FR-910.
# Each case wires a downstream signal (typically a ValidationResult with the
# matching reason_code) and asserts the chokepoint routes the disposition to
# `needs_review` and surfaces the reason code in `per_rule_trace`.
@pytest.mark.asyncio
@pytest.mark.parametrize("reason_code, outcome, fr_label", [
    ("ENGINE.OCR.AMBIGUOUS",            Outcome.INSUFFICIENT_EVIDENCE, "FR-903"),
    ("ENGINE.CLASS.UNKNOWN",            Outcome.INSUFFICIENT_EVIDENCE, "FR-904"),
    ("ENGINE.CLASS.DISAGREEMENT",       Outcome.INSUFFICIENT_EVIDENCE, "FR-905"),
    ("ENGINE.DPI.MISSING",              Outcome.INSUFFICIENT_EVIDENCE, "FR-910"),
])
async def test_fr_900_series_routes_to_needs_review(reason_code, outcome, fr_label):
    """FR-903 / FR-904 / FR-905 / FR-910 — when an upstream signal carries
    one of these reason codes, the chokepoint must route to needs_review and
    keep the reason code visible in the per-rule trace."""
    rules = FakeRuleEngine(results=(
        ValidationResult(
            rule_id=f"R-{fr_label}", cfr_citation="27 CFR §x",
            beverage_class=BeverageClass.SPIRITS,
            outcome=outcome, severity=Severity.WARN,
            reason_code=reason_code,
            aggregated_confidence=0.4, engine_meta=_em(),
        ),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules,
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review", f"{fr_label} did not route to needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert reason_code in rule_ids or any(reason_code.split(".")[1] in rid for rid in rule_ids), (
        f"{fr_label}: reason_code {reason_code} not surfaced in per_rule_trace ({rule_ids})"
    )


@pytest.mark.asyncio
async def test_fr907_validator_exception():
    class FailingRules:
        async def evaluate(self, *a, **kw):
            raise RuntimeError("validator boom")

    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=FailingRules(),  # type: ignore[arg-type]
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"


@pytest.mark.asyncio
async def test_fr908_per_rule_timeout_outcome_routes_to_needs_review():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="R-slow", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.TIMEOUT, severity=Severity.INFO,
                         reason_code="ENGINE.SLA.RULE_TIMEOUT",
                         aggregated_confidence=0.0, engine_meta=_em()),
        ValidationResult(rule_id="R-ok", cfr_citation="27 CFR §y", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.PASS, severity=Severity.INFO,
                         aggregated_confidence=0.95, engine_meta=_em()),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"


@pytest.mark.asyncio
async def test_fr909_whole_eval_timeout():
    class SlowRules:
        async def evaluate(self, *a, **kw):
            await asyncio.sleep(10)
            return ()

    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=SlowRules(),  # type: ignore[arg-type]
                  orchestrator=FakeOrchestrator(), settings=Settings())
    e._sla_seconds = 0.1
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert "ENGINE.SLA.TIMEOUT" in rule_ids


@pytest.mark.asyncio
async def test_fr911_reference_data_unavailable():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="R-cpi", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.ERROR, severity=Severity.INFO,
                         reason_code="ENGINE.REFERENCE_DATA.UNAVAILABLE",
                         aggregated_confidence=0.0, engine_meta=_em()),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"


@pytest.mark.asyncio
async def test_fr912_model_unavailable():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="X.brand.present", cfr_citation="27 CFR §5.42",
                         beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.INSUFFICIENT_EVIDENCE, severity=Severity.WARN,
                         reason_code="BRAND.NAME.NEEDS_REVIEW",
                         aggregated_confidence=0.6, engine_meta=_em()),
    ))
    orch = FakeOrchestrator(refined_outputs=[], raise_on_call=1)
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=orch, settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert any("ENGINE.MODEL" in c for c in rule_ids)
```

- [ ] **Step 2: Run focused → expect GREEN (T13/T14 already implement the code paths)**

If any case unexpectedly fails, that's a Rule 1-3 inline gap in T14's chokepoint surfacing — fix the surfacing minimally (do NOT change disposition logic, only ensure the failure code lands in `per_rule_dispositions`).

- [ ] **Step 3: Commit**

```bash
git add tests/test_evaluator_failure_modes.py
git commit -m "test(e5): full FR-902/903/904/905/907/908/909/910/911/912 coverage"
```

---

## Task 19: tests/test_post_labels_perf.py — NFR-PERF-001/003 P50/P99

**Files:**
- Test: `tests/test_post_labels_perf.py`

> **iter-1 fix (Warning #5):** the perf test must run against deterministic seams (canned vision observations + fake orchestrator) so it measures Application Service / Evaluator / serialization overhead — NOT vision-model load time, NOT real OpenAI latency. Use `vision_mode="cloud"` with respx-mocked endpoints if a closer-to-prod profile is needed; otherwise inject fakes via the same `monkeypatch` seams as T15.

- [ ] **Step 1: Write the perf test**

```python
# tests/test_post_labels_perf.py
"""NFR-PERF-001 / NFR-PERF-003 — P50 ≤ 2.7s, P99 ≤ 5.0s.

Measures Application Service / Evaluator / serialization overhead against
deterministic seams (vision + orchestrator fakes). Vision-model load time
and LLM latency are bypassed by design — those are E3/E4 perf concerns,
not E5's chokepoint perf concerns.
"""
import json
import statistics
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.vision import FakeVisionExtractor


@pytest.fixture
def deterministic_seams(monkeypatch):
    monkeypatch.setattr(
        "app.deps.build_vision_extractor",
        lambda settings: FakeVisionExtractor(observations=[]),
    )
    monkeypatch.setattr(
        "app.deps.build_orchestrator",
        lambda settings: FakeOrchestrator(),
    )


@pytest.mark.slow
def test_post_labels_perf_p50_p99(deterministic_seams):
    client = TestClient(app)
    payload = json.dumps({"application_id": "A-001", "evaluation_id": "EV-001"})
    image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    durations: list[float] = []
    for _ in range(30):
        t0 = time.monotonic()
        response = client.post("/labels", files={
            "application": ("a.json", payload, "application/json"),
            "label": ("l.png", image, "image/png"),
        })
        durations.append(time.monotonic() - t0)
        assert response.status_code == 200

    p50 = statistics.median(durations)
    p99 = sorted(durations)[max(0, int(len(durations) * 0.99) - 1)]
    print(f"\nperf: P50={p50:.3f}s P99={p99:.3f}s (n={len(durations)})")
    assert p50 <= 2.7, f"P50 {p50:.3f}s exceeds NFR-PERF-001 budget 2.7s"
    assert p99 <= 5.0, f"P99 {p99:.3f}s exceeds NFR-PERF-003 budget 5.0s"
```

- [ ] **Step 2: Run with `uv run pytest tests/test_post_labels_perf.py -v -s` → expect GREEN**

- [ ] **Step 3: Commit**

```bash
git add tests/test_post_labels_perf.py
git commit -m "test(e5): NFR-PERF-001/003 P50/P99 budget assertion (30-trial)"
```

---

## Task 20: tests/test_ac_fixture_coverage.py — L1 §4 AC #1-4

**Files:**
- Modify: `app/schemas/application.py` (additive optional `expected_values: tuple[ExpectedValue, ...] = ()` field — see Hard Scope Boundary)
- Create: `fixtures/<fixture_id>/expected.json` per fixture (sidecar describing expected values per field)
- Test: `tests/test_ac_fixture_coverage.py`

> **iter-2 Warning #2 fix.** v0.3 left `expected = []` hardcoded in T13 Cycle C and gave T20 no way to populate it, so AC #1 (`01-spirits-clean → pass`) and AC #4 (`06-abv-out-of-tolerance → fail`) couldn't be satisfied — every fixture would have routed to `needs_review` because the rule engine was given nothing to validate against. v0.4 closes the gap with the smallest possible additive surface change: an optional `expected_values: tuple[ExpectedValue, ...] = ()` on `Application`. T13 Cycle C and T14 Cycle B already read it via `tuple(application.expected_values)` (see those task recipes); T20 here builds the application with values loaded from a per-fixture sidecar JSON.

- [ ] **Step 1: Add the additive Application field**

```python
# app/schemas/application.py — add the optional field. Default of `()`
# preserves every existing call site (T0a/T6/T11/T13/T14/T15/T16/T18/T19
# tests construct Application without `expected_values`; they all keep
# working).
from app.schemas.expected import ExpectedValue


class Application(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    application_id: str
    evaluation_id: str
    expected_values: tuple[ExpectedValue, ...] = ()
```

- [ ] **Step 2: Add per-fixture sidecars**

For each fixture in the AC-coverage parametrize list, drop a sidecar JSON describing the expected values per field. The schema mirrors `app/schemas/expected.py::ExpectedValue` (`field_id` + the field-specific value keys; consult that schema for the exact field names — the fixture sidecar carries whatever the rule pack needs to make the disposition deterministic).

```
fixtures/01-spirits-clean/expected.json
fixtures/03-warning-title-case/expected.json
fixtures/04-low-res-blurry/expected.json
fixtures/06-abv-out-of-tolerance/expected.json
```

Each file is a JSON list of objects, e.g.:

```json
[
  {"field_id": "brand_name", "expected_brand_name": "Crown Royal"},
  {"field_id": "alcohol_content", "expected_abv_pct": 40.0, "abv_tolerance_pct": 0.3}
]
```

The exact keys per field come from `ExpectedValue` — pull them out at fixture-build time and let pydantic surface any schema drift as a load error.

- [ ] **Step 3: Write the AC tests**

```python
# tests/test_ac_fixture_coverage.py
"""L1 §4 AC #1/#2/#3/#4 — fixture-driven dispositions (full real stack).

Each fixture carries a sidecar `expected.json` describing the per-field
ExpectedValues the rule engine validates against. T13 Cycle C reads them
via `application.expected_values` (additive optional field — see iter-2
Warning #2 fix in the Hard Scope Boundary)."""
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.deps import build_evaluator
from app.schemas.application import Application
from app.schemas.expected import ExpectedValue
from app.schemas.label import Label


def _label_from_fixture(fixture_id: str) -> Label:
    img = Path(f"fixtures/{fixture_id}/label.png")
    if not img.exists():
        img = Path(f"fixtures/{fixture_id}/label.jpg")
    suffix = img.suffix.lower()
    content_type = "image/png" if suffix == ".png" else "image/jpeg"
    return Label(
        label_id=fixture_id,
        batch_id="ac-coverage",
        image_bytes=img.read_bytes() if img.exists() else b"",
        content_type=content_type,
        face_tag="front",
        dimensions=None,  # E3 quality.assess() reads DPI from the image itself
    )


def _expected_from_fixture(fixture_id: str) -> tuple[ExpectedValue, ...]:
    """Load the per-fixture sidecar and parse into ExpectedValue tuple.
    Missing sidecar → empty tuple (the rule engine treats every field as
    'no expected'); present sidecar → strict pydantic parse so schema drift
    fails loud."""
    sidecar = Path(f"fixtures/{fixture_id}/expected.json")
    if not sidecar.exists():
        return ()
    raw = json.loads(sidecar.read_text())
    return tuple(ExpectedValue(**entry) for entry in raw)


@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_id, expected_disposition", [
    ("01-spirits-clean", "pass"),
    ("03-warning-title-case", "fail"),
    ("04-low-res-blurry", "needs_review"),
    ("06-abv-out-of-tolerance", "fail"),
])
async def test_ac_fixture_disposition(fixture_id, expected_disposition):
    settings = Settings()
    evaluator = build_evaluator(settings)
    application = Application(
        application_id="A-001",
        evaluation_id=f"EV-{fixture_id}",
        expected_values=_expected_from_fixture(fixture_id),
    )
    label = _label_from_fixture(fixture_id)
    envelope = await evaluator.evaluate(application=application, label=label)
    assert envelope.disposition == expected_disposition, (
        f"fixture {fixture_id}: expected {expected_disposition}, got {envelope.disposition}"
    )
```

- [ ] **Step 4: Run focused → expect GREEN once sidecars + schema field land together**

If any case fails, identify which seam (vision/rules/orchestrator) is producing wrong output. E2/E3/E4 are LOCKED for evaluation logic — if they produce wrong output against a fixture, report `STATUS: BLOCKED — AC #X requires upstream fix in <epoch>`. The Application schema field is in scope here (additive), so a `expected_values`-related fail is fixable inside this task.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/application.py fixtures/*/expected.json tests/test_ac_fixture_coverage.py
git commit -m "feat(e5): AC fixture coverage 01/03/04/06 + Application.expected_values"
```

---

## Task 21: tests/test_evaluator_chokepoint_grep.py — P4 grep guard

**Files:**
- Test: `tests/test_evaluator_chokepoint_grep.py`

- [ ] **Step 1: Write the grep test**

```python
# tests/test_evaluator_chokepoint_grep.py
"""P4 enforcement: Evaluator never raises; chokepoint catches everything.
Allowed exceptions: NotImplementedError (skeleton residue) or lines preceded
by a `# programmer error` comment within 2 lines."""
import re
from pathlib import Path


_RAISE_RX = re.compile(r"^\s*raise\s+(\S+)")


def test_evaluator_has_no_bare_raise():
    src = Path("app/services/evaluator.py").read_text()
    lines = src.splitlines()
    violations: list[str] = []
    for i, line in enumerate(lines, start=1):
        m = _RAISE_RX.match(line)
        if not m:
            continue
        what = m.group(1)
        if "NotImplementedError" in what:
            continue
        prior_2 = "\n".join(lines[max(0, i - 3):i - 1]).lower()
        if "programmer error" in prior_2 or "programmer-error" in prior_2:
            continue
        violations.append(f"L{i}: {line.strip()}")
    assert not violations, "P4 violation — bare raise in evaluator.py:\n" + "\n".join(violations)
```

- [ ] **Step 2: Run focused → expect GREEN**

If RED, audit `app/services/evaluator.py`: either wrap the raise in a try/except that records to `timeline.failures`, or annotate as `# programmer error: ...` if intentional.

- [ ] **Step 3: Commit**

```bash
git add tests/test_evaluator_chokepoint_grep.py
git commit -m "test(e5): P4 grep enforcement — no bare raise in evaluator chokepoint"
```

---

## Final integration check

After T21 lands:

- [ ] Run: `uv run pytest -q` — all green (target ~444 tests; +4 from the T0a/T0b factory tests).
- [ ] Run: `uv run pytest tests/test_ac_fixture_coverage.py tests/test_evaluator_failure_modes.py tests/test_post_labels_perf.py -v -s`.
- [ ] Verify warm-up: `uv run python -c "from fastapi.testclient import TestClient; from app.main import app; print(TestClient(app).get('/healthz').json())"`.
- [ ] Verify chokepoint: `grep -n "^\s*raise " app/services/evaluator.py | grep -v "NotImplementedError" | grep -v "programmer"` — empty.

---

## Self-review

**Spec coverage** — checked L1 §1 through §8 against tasks. All 12 exit-gate items have a task: AC #1-4 → T20; AC #5 (FR-900) → T18; AC #6/#7 (audit/metrics) → T6 + T13; AC #8 (perf) → T19; AC #9 (healthz) → T16; AC #10 (FR-303 runtime) → T9 + T13 Cycle C; AC #11 (chokepoint grep) → T21; AC #12 (evaluation_id consistency) → T13 Cycle D's happy-path test.

**Wave 0 coverage** — T0a (`build_rule_engine`) covers FR-303/700-series indirectly by ensuring T15's deterministic startup; T0b (`build_validator_context`) covers FR-907/911 indirectly by ensuring T13/T14 can construct a valid context against the locked E2 dataclass. Neither task introduces new requirement coverage — both are construction-path determinism for tasks downstream.

**Placeholder scan** — all code blocks are concrete. T13 leaves per-field `FieldFindingWire` construction to T20 (notes this explicitly in Cycle D Step 3); T20's tests will surface gaps if the construction logic is missing.

**Type consistency** — `EvaluationTimeline` shape consistent across T1, T5, T6, T13, T14. `compute_disposition`/`min_aggregate_confidence`/`patch_validation_results`/`should_invoke_orchestrator` are pure module-level functions (no class state). `Evaluator.__init__` signature is `(*, vision, rules, orchestrator, settings, cache=None)` consistent across T13, T14, T15.

**Wave-structure note** — added §"Dependency Graph" + §"Wave structure". Pre-flight ownership disjointness verified. T13 and T14 are SAME file — sequential. T15 and T17 both touch `app/main.py` — T15 writes the file (creates labels endpoint); T17 appends a single line for raw router. Sequential per the wave structure.

**FR-303 enforcement chain** — T9 (`patcher.py`) is pure and directly tested. T13 Cycle C uses the patcher. The L1 §4 AC #10 runtime invariant is satisfied because the patcher is the ONLY place ValidationResults are mutated; outcome/severity/reason_code are immutable on frozen ValidationResult and the patcher proves at construction time that they're untouched.

**Helper extraction rationale** — every pure helper (T7-T12) is independently testable WITHOUT running the Evaluator. This means Wave 3 fans out to 6 concurrent subagents (T7-T12 all parallel), and the Evaluator (T13-T14) becomes a thin orchestration layer that integrates them. This is the "narrow scope + parallel up to 6" optimization the user asked for.

**Empty-results case** — `compute_disposition(())` explicitly returns `needs_review` (T7). Vision-and-rules-both-fail path → empty results → needs_review per the chokepoint. No silent-pass risk.

**`AISuggestionWire.task` rename** — wire enum and orchestrator names mismatch is encoded in the `_TASK_WIRE_NAME` constant in `envelope_builder.py` (T11). The actual rename happens in T20 when per-field FieldFindingWire construction lands; T11 sets up the constant.

**Cache key vs evaluation_id collision** — cache key uses `_input_hash` (canonical app + image bytes); same input → same key regardless of evaluation_id. Cached envelope's evaluation_id is replaced on hit so audit trails don't conflate. Tested in T13 Cycle D.

**Rule-engine factory dependency** — T15 imports `build_rule_engine(settings)` from `app/rules/__init__.py`, which is created by Wave 0 task **T0a**. The deferred-BLOCK escalation that v0.2 documented has been replaced by deterministic dependency: T15 cannot start until T0a is committed.

**ValidatorContext factory dependency** — T13/T14 build `ValidatorContext` via `app/rules/context.py::build_validator_context` (Wave 0 task **T0b**). This sources `assets`/`decision_tables`/`engine_version` from `engine._ruleset` (no `label` field — v0.2 Cycle C had a fabricated kwarg). T0b lands before Wave 3.

---

## L1 → Task Coverage Map

This map tracks every L1-named requirement (FR-/NFR-) and acceptance criterion against the task that owns its coverage. It is the artifact a future plan-reviewer reads first to confirm nothing was dropped.

| L1 Requirement | Status | Task / Notes |
|---|---|---|
| FR-300 / FR-301 / FR-302 (orchestrator trigger + invocation) | Covered | T10 (`should_invoke_orchestrator` predicate); T13 Cycle C (Evaluator wiring). |
| FR-303 (orchestrator never overrides fail) | Covered | T9 (`patcher.py` — pure FR-303-safe patcher); T13 Cycle C (uses patcher); T20 (`test_patcher_fr303` is the canary). |
| FR-304 (CallRecord retry visibility) | Covered upstream (E4) | E4 ships the orchestrator-side recording; E5 carries it through unchanged. |
| FR-505 / FR-603 (legibility short-circuit) | Covered | T13 Cycle B (`assess_quality(label)` short-circuit). |
| FR-700-series (audit) | Covered | T6 (`AuditRecorder` + canonical hashes); T13 Cycle D (assembly). |
| FR-902 (conflicting rules) | Covered | T18 `test_fr902_conflicting_rules`. |
| FR-903 (ambiguous OCR) | Covered (iter-2) | T18 parametrized — `test_fr_900_series_routes_to_needs_review[FR-903]`. |
| FR-904 (unknown class) | Covered (iter-2) | T18 parametrized — `test_fr_900_series_routes_to_needs_review[FR-904]`. |
| FR-905 (class disagreement) | Covered (iter-2) | T18 parametrized — `test_fr_900_series_routes_to_needs_review[FR-905]`. |
| FR-906 (ruleset version mismatch — loader-time refusal) | Deferred | Loader-time refusal lives in E2's loader test (`tests/rules/test_loader.py`); end-to-end exercised in E8 deployment readiness. T0a calls the existing E2 loader, so any FR-906 refusal surfaces at process startup before any E5 test runs. See Hard Scope Boundary. |
| FR-907 (validator exception) | Covered | T14 Cycle B (rules try/except → `ENGINE.RULES.UNAVAILABLE`); T18 `test_fr907_validator_exception`. |
| FR-908 (per-rule timeout) | Covered | T18 `test_fr908_per_rule_timeout_outcome_routes_to_needs_review` (semantics enforced by E2's `YamlRuleEngine`; E5 routes the resulting outcome). |
| FR-909 (whole-eval timeout) | Covered | T14 Cycle A (`asyncio.wait_for` → `ENGINE.SLA.TIMEOUT`); T18 `test_fr909_whole_eval_timeout`. |
| FR-910 (missing DPI) | Covered (iter-2) | T18 parametrized — `test_fr_900_series_routes_to_needs_review[FR-910]`. |
| FR-911 (reference-data unavailable) | Covered | T18 `test_fr911_reference_data_unavailable`. |
| FR-912 (model unavailable) | Covered | T14 Cycle B (orchestrator try/except → `ENGINE.MODEL.UNAVAILABLE`); T18 `test_fr912_model_unavailable`. |
| NFR-PERF-001 / NFR-PERF-003 (P50 / P99 SLA) | Covered | T19 perf test (30-trial P50/P99 budget). |
| NFR-DET-001 (session determinism) | Covered | T12 (`SessionCache`); T13 Cycle D (cache integration). |
| NFR-DET-002 (cross-process determinism) | Out of scope (MVP) | E5 does not persist the cache across restarts; documented in T12 module docstring. |
| NFR-OBS-001 (FR-900 logs) | Covered (iter-2) | T14 Cycle B emits `_logger.info("engine_failure_routed", extra={"reason_code": ..., ...})` for every routed FR-900 event; Cycle B done-criteria assert via `caplog`. Same logging pattern applied to vision-exception, timeout, legibility, and orchestrator-exception branches. |
| L1 §4 AC #1-4 (fixture dispositions) | Covered | T20 with per-fixture `expected.json` sidecars + additive `Application.expected_values`. |
| L1 §4 AC #5 (FR-900 series) | Covered | T18 (parametrized — see FR rows above). |
| L1 §4 AC #6 / AC #7 (audit / metrics split) | Covered | T6 + T13 Cycle D; D-018. |
| L1 §4 AC #8 (perf) | Covered | T19. |
| L1 §4 AC #9 (healthz) | Covered | T16. |
| L1 §4 AC #10 (FR-303 runtime) | Covered | T9 + T13 Cycle C; the `test_patcher_does_not_override_fail` canary. |
| L1 §4 AC #11 (chokepoint grep) | Covered | T21 P4 grep guard. |
| L1 §4 AC #12 (evaluation_id consistency) | Covered | T13 Cycle D `test_cache_hit_replaces_evaluation_id` (cache path); same UUID flows audit + metrics + envelope. |

---

## Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-04 | Project team | Initial E5 L2 plan. 16 tasks across 8 waves; bottlenecked on T7+T8 (Evaluator file). |
| 0.2 | 2026-05-04 | Project team | **Refactored for parallelism per user feedback**: extracted Evaluator helpers into 6 separate pure modules (T7 disposition, T8 aggregation, T9 patcher, T10 triggers, T11 envelope_builder, T12 cache) so Wave 3 fans out to 6 concurrent subagents. Evaluator (T13 + T14) is now thin — 4 cycles (core) + 2 cycles (resilience) instead of 6+4. Total tasks: 21; total waves: 8; max parallelism: 6 (Wave 3); expected commits: ~26. |
| 0.3 | 2026-05-04 | Project team | **plan-review iter-1 fixes** (4 blockers + 3 warnings). **B1**: Added `_stub_label()` test factory in Conventions; swept test recipes to use real `Label` shape (`label_id`, `content_type`, `face_tag`); production code sources wire `label_ref` from `Label.label_id`. **B2**: New Wave 0 task **T0b** introduces `app/rules/context.py::build_validator_context(engine, started_at_ms)`; T13 Cycle C + T14 Cycle B use it instead of constructing `ValidatorContext(label=...)`. **B3**: New Wave 0 task **T0a** introduces `app/rules/__init__.py::build_rule_engine(settings)`; T15 imports it instead of relying on a runtime BLOCK escalation. **B4**: T13 Cycle B uses `app.vision.quality.assess(label)` instead of fake-only `getattr(vision, "needs_better_photo", False)`; FakeVisionExtractor drops the flag; Cycle B test monkeypatches `app.services.evaluator.assess_quality`. **W4**: T16 → T15 dependency added; T16 moved from Wave 5 to Wave 6 (Wave 6 now: T16 + T17, fanout 2). **W5**: T15 happy-path test + T19 perf test now monkeypatch `build_vision_extractor` + `build_orchestrator` (or use respx-mocked cloud) to remove flakiness against real vision. **W6 / B1 follow-on**: T20 fixture coverage uses `dimensions=None` (drops hardcoded `Dimensions(200, 200)`). Total tasks: 23; total waves: 9; max parallelism: 6 (Wave 1a); expected commits: ~28. |
| 0.4 | 2026-05-04 | Project team | **plan-review iter-2 fixes** (1 blocker + 4 warnings + 3 info). **B-iter2** (v0.3-regression): the v0.3 free-function `build_validator_context` accessed `engine._ruleset` and crashed against the abstract `RuleEngine` seam used by `FakeRuleEngine`. T0b is rewritten so context construction lives on the rule-engine ABC itself (`RuleEngine.build_validator_context(self, *, started_at_ms)`); `YamlRuleEngine` implements it against `self._ruleset`; `FakeRuleEngine` (T3) implements a stub returning empty assets/tables and `engine_version="fake"`; the free-function in `app/rules/context.py` is kept as a thin shim. T13 Cycle C and T14 Cycle B call `self._rules.build_validator_context(...)` on the abstraction. Hard Scope Boundary acknowledges the additive abstract method. **W1-iter2** (FR-903/904/905/906/910 + NFR-OBS-001): T18 extends the parametrized FR-900 series with FR-903 (ambiguous OCR), FR-904 (unknown class), FR-905 (class disagreement), FR-910 (missing DPI) — each asserts the chokepoint routes disposition to needs-review with the matching reason code. FR-906 documented as deferred to E2 loader test + E8 deployment readiness. NFR-OBS-001 added: T14 Cycle B chokepoint emits a structured log line via `_logger.info("engine_failure_routed", extra={"reason_code": ..., ...})` for every routed FR-900 event; Cycle B done-criteria assert via `caplog`. **W2-iter2**: T20 acquires per-fixture `expected.json` sidecars; new additive optional `expected_values: tuple[ExpectedValue, ...] = ()` on `Application`; T13 Cycle C and T14 Cycle B forward `application.expected_values` to the rule engine; Hard Scope Boundary acknowledges the additive field. **W3-iter2**: T0a both tests now consume a `rules_root_env` fixture that pins `RULES_ROOT` to `Path("rules").resolve()` so neither relies on the import-time CWD. **W4-iter2**: T13 Cycle B test stub uses canonical `WARNING.LEGIBILITY.LOW_DPI` reason-code prefix (matches `app/vision/quality.py`). **I1-iter2**: T4 file-map row no longer mentions removed `needs_better_photo` flag. **I2-iter2**: stale Wave-1 inline header replaced with the split-header pointer to Wave 1a/1b. **I3-iter2**: Conventions §`_stub_label()` no longer claims `label_ref` is carried in audit `request_id` (audit identifies via `evaluation_id` + hashes; no such field). Total tasks: 23; total waves: 9; max parallelism: 6 (Wave 1a); expected commits: ~28 (unchanged — all v0.4 changes are doc-only edits within the existing tasks, no new tasks added). |

---

## Dependency Graph

### Task Dependencies

| Task | Depends On | Blocks | Files Owned |
|------|-----------|--------|-------------|
| T0a: build_rule_engine factory | — | T13, T14, T15, T16 | `app/rules/__init__.py`, `app/config.py` (additive), `tests/rules/test_build_rule_engine.py` |
| T0b: RuleEngine.build_validator_context | — | T3, T13, T14 | `app/rules/engine.py` (additive abstract method), `app/rules/yaml_engine.py` (concrete impl), `app/rules/context.py` (thin shim), `tests/rules/test_build_validator_context.py` |
| T1: EvaluationTimeline | — | T5, T6, T11, T13, T14 | `app/services/__init__.py`, `app/services/engine_meta.py`, `tests/test_engine_meta_timeline.py` |
| T2: confidence band | — | T8, T11 | `app/services/confidence.py`, `tests/test_confidence_band_mapping.py` |
| T3: orch + rules fakes | T0b | T13, T14, T18 | `tests/_fakes/__init__.py`, `tests/_fakes/orchestrator.py`, `tests/_fakes/rules.py`, `tests/test_fakes_orchestrator_rules.py` |
| T4: vision fake | — | T6, T11, T13, T14, T15, T16, T17, T18, T19, T20 | `tests/_fakes/vision.py`, `tests/conftest.py` (append `_stub_label`), `tests/test_fakes_vision.py` |
| T5: metrics_builder | T1 | T11, T13 | `app/services/metrics_builder.py`, `tests/test_metrics_builder.py` |
| T6: audit | T1, T4 (conftest `_stub_label`) | T11, T13 | `app/services/audit.py`, `tests/test_audit_recorder.py`, `tests/test_audit_metrics_split.py` |
| T7: disposition | — | T13 | `app/services/disposition.py`, `tests/test_disposition_rule.py` |
| T8: aggregation | T2 | T11 | `app/services/aggregation.py`, `tests/test_confidence_aggregation.py` |
| T9: patcher (FR-303) | — | T13 | `app/services/patcher.py`, `tests/test_patcher_fr303.py` |
| T10: triggers | — | T13 | `app/services/triggers.py`, `tests/test_triggers.py` |
| T11: envelope_builder | T1, T2, T4 (conftest), T5, T6, T8 | T13 | `app/services/envelope_builder.py`, `tests/test_envelope_builder.py` |
| T12: cache | — | T13 | `app/services/cache.py`, `tests/test_session_cache.py` |
| T13: Evaluator core (4 cycles) | T0b, T1, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12 | T14, T15, T16, T18 | `app/services/evaluator.py`, `tests/test_evaluator_skeleton.py`, `tests/test_evaluator_legibility_shortcircuit.py`, `tests/test_evaluator_orchestrator_paths.py`, `tests/test_evaluator_happy_path.py` |
| T14: Evaluator resilience (2 cycles) | T0b, T13 | T15, T18, T21 | `app/services/evaluator.py` (modify), `tests/test_evaluator_timeouts.py`, `tests/test_evaluator_chokepoint.py` |
| T15: POST /labels endpoint | T0a, T14 | T16, T17, T19, T20 | `app/api/labels.py`, `app/deps.py` (additive), `app/main.py` (write+register), `tests/test_post_labels_endpoint.py` |
| T16: /healthz warm-up | T0a, T0b, T14, T15 | — | `app/api/healthz.py`, `tests/test_healthz_warmup.py` |
| T17: /raw endpoint | T15 | — | `app/api/raw.py`, `app/main.py` (append) |
| T18: FR-900 series tests | T14 | — | `tests/test_evaluator_failure_modes.py` |
| T19: perf test | T15 | — | `tests/test_post_labels_perf.py` |
| T20: AC fixture coverage | T15 | — | `app/schemas/application.py` (additive `expected_values`), `fixtures/<id>/expected.json` (sidecars), `tests/test_ac_fixture_coverage.py` |
| T21: chokepoint grep | T14 | — | `tests/test_evaluator_chokepoint_grep.py` |

### Shared Files

- `app/services/evaluator.py` — modified by T13 (creates) AND T14 (extends). Sequential.
- `app/main.py` — modified by T15 (writes router registration) AND T17 (appends). Sequential.
- `app/deps.py` — modified by T15 only (additive `build_evaluator`).

### Execution Waves

> **iter-1 fix:** Wave 0 added (T0a + T0b) eliminates two deferred-BLOCK risks (Blockers #2, #3). T16 moved Wave 5 → Wave 6 (now joins T17) because T16 imports `build_evaluator` from T15 (Warning #4). Total tasks: **23**; total waves: **9** (10 sub-waves).

```
Wave 0 (parallel, 2): [T0a, T0b]                 ← root-level rules-package factories
Wave 1 (8 candidates, executor cap = 6): split into 1a + 1b — see below
  → T7, T9, T10, T12 are pure roots (no deps); T1, T2, T3, T4 are seed deps.
```

**Wave-1 split** (8 candidates > 6 executor cap): execute as two back-to-back sub-waves.

- Wave 1a (parallel, 6): [T1, T2, T3, T4, T7, T9]
- Wave 1b (parallel, 2): [T10, T12]

```
Wave 2 (parallel, 4): [T5, T6, T8, T11]
  → T5, T6 need T1; T8 needs T2; T11 needs T1+T2+T5+T6+T8.
  → T11 strictly depends on T5+T6+T8 — must come AFTER them.
```

**Wave-2 split** to honor T11's deps:

- Wave 2a (parallel, 3): [T5, T6, T8]
- Wave 2b (single): [T11]

```
Wave 3 (single, 4 cycles): [T13]                 ← needs all of T0b, T1-T12
Wave 4 (single, 2 cycles): [T14]                 ← needs T13 (same file)
Wave 5 (parallel, 3): [T15, T18, T21]            ← need T14 (T15 also needs T0a)
Wave 6 (parallel, 2): [T16, T17]                 ← need T15 (build_evaluator + main.py append)
Wave 7 (parallel, 2): [T19, T20]                 ← need T15
Wave 8 (single, run-only): [final integration check]
```

**Resolved wave plan (final):**

- Wave 0 (parallel, 2): T0a, T0b
- Wave 1a (parallel, 6): T1, T2, T3, T4, T7, T9
- Wave 1b (parallel, 2): T10, T12
- Wave 2a (parallel, 3): T5, T6, T8
- Wave 2b (single): T11
- Wave 3 (single, 4-cycle bundle): T13
- Wave 4 (single, 2-cycle bundle): T14
- Wave 5 (parallel, 3): T15, T18, T21
- Wave 6 (parallel, 2): T16, T17
- Wave 7 (parallel, 2): T19, T20
- Wave 8 (run-only): final integration check

**Total expected new commits on `main`:** 28 (T0a+T0b+T1+T2+T3+T4+T5+T6+T7+T8+T9+T10+T11+T12+T15+T16+T17+T18+T19+T20+T21 = 21; T13 = 4; T14 = 2; total = 27 minimum + small margin for inline Rule 1-3 fixes).

**Critical path (longest dependency chain):** T0a → T15 → T16/T17 (parallel) and T1 → T6 → T11 → T13 (4 cycles) → T14 (2 cycles) → T15 → T16/T17. **8 wave hops** (counting sub-wave boundaries within Wave 1 and Wave 2 as logical hops, the realized critical-path latency is 10 sub-waves). The Evaluator's 6 cycles (4 in T13 + 2 in T14) dominate the critical path because they're file-serialized.

**Parallelism factor.** 23 tasks across 9 waves (10 sub-waves) → effective parallelism ≈ 2.6× vs strict serial. Wave 1a is the densest (6 concurrent subagents — at the executor cap); Wave 0 is the lightest (2).

**Pre-flight invariant** (parallel-plan-executor enforces): for each (sub-)wave, the union of file-ownership sets is strict-disjoint. Verified above in §Shared Files.

### Execution Strategy

> **For Claude:** Use `parallel-plan-executor` to execute this plan. The executor dispatches every task in a sub-wave concurrently (up to 6 at a time) and holds a barrier between (sub-)waves. Each task runs as an isolated subagent with the `task-executor` skill body injected for TDD enforcement.

- **Wave 0** — Dispatch [T0a, T0b] concurrently. Barrier. Verify 2 commits.
- **Wave 1a** — Dispatch [T1, T2, T3, T4, T7, T9] concurrently (6 subagents). Barrier. Verify 6 commits.
- **Wave 1b** — Dispatch [T10, T12] concurrently. Barrier. Verify 2 commits.
- **Wave 2a** — Dispatch [T5, T6, T8] concurrently. Barrier. Verify 3 commits.
- **Wave 2b** — Dispatch [T11] alone. Barrier. Verify 1 commit.
- **Wave 3** — Dispatch [T13] alone (4-cycle bundle inside one subagent). Barrier. Verify 4 commits.
- **Wave 4** — Dispatch [T14] alone (2-cycle bundle). Barrier. Verify 2 commits.
- **Wave 5** — Dispatch [T15, T18, T21] concurrently. Barrier. Verify 3 commits.
- **Wave 6** — Dispatch [T16, T17] concurrently. Barrier. Verify 2 commits.
- **Wave 7** — Dispatch [T19, T20] concurrently. Barrier. Verify 2 commits.
- **Wave 8** — Run-only final integration check (no commits unless cleanup needed).

**Total commits expected:** 27 (sum of per-wave verifications above). Margin for inline Rule 1-3 fixes: +1-2.
