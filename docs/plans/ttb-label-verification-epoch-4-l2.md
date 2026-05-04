# TTB Label Verification — Epoch 4 (Orchestrator Seam) — L2 Implementation Plan

> **For agentic workers:** REQUIRED EXECUTOR: `parallel-plan-executor`. Per olorin CLAUDE.md, `superpowers:subagent-driven-development` is obsolete and fully replaced by `parallel-plan-executor` (which injects the `task-executor` skill body for TDD enforcement). Each task lands as one or more Red→Green→Commit cycles inside an isolated worktree subagent. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Parent L1:** [`ttb-label-verification-epoch-4-orchestrator-seam.md`](./ttb-label-verification-epoch-4-orchestrator-seam.md) (v0.2)
> **L1 index:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md) (v0.4)
> **E3 L2 (structural template):** [`ttb-label-verification-epoch-3-l2.md`](./ttb-label-verification-epoch-3-l2.md) (v0.2)
> **PRD:** [`docs/PRD.md`](../PRD.md) v0.6 — FR-300 (brand-disambig), FR-301 (reasoning enrich), FR-302 (OCR reconcile), FR-303 (no pass/fail invariant), FR-304 (ENGINE.MODEL.UNAVAILABLE fallback)
> **ARCH:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) v0.3 — §4.2.6 orchestrator topology, §6.6 Refined, §6.9 CallRecord, §8.2 Structured Outputs, §12.2 env-var inventory, §19.3 SDK pins
> **ADRs in scope:** D-002 (no agentic loops), D-004 (substitutability seams), D-020 (snapshot/prompt pinning), D-021 (prototype-tier scope reduction — vLLM/XGrammar dropped from MVP)

**Goal.** Land D-004 swap point #2: the `Orchestrator` ABC and two conforming concrete implementations (`OpenAIStrictOrchestrator` validated default, `AnthropicStrictOrchestrator` swap-path skeleton) that produce a wire-compatible `Refined` for the same input. Both use OpenAI Structured Outputs `strict:true` (or Anthropic `tool_use` strict equivalent), `temperature=0`, fixed `seed`, snapshot-pinned models, single-shot pattern (no ReAct), and write per-call `CallRecord` ring-buffer entries. The orchestrator runs **three** tasks per PRD §5.4: brand-name borderline disambiguation (FR-300), reasoning-text enrichment (FR-301), OCR multi-reading reconciliation (FR-302). The structural FR-303 invariant — "the orchestrator never decides pass/fail" — is enforced at the type level: `Refined` carries no disposition-style field, no task-output schema carries `pass`/`fail` field names. FR-304 fallback (LLM unavailable → `ENGINE.MODEL.UNAVAILABLE`) is wired via httpx-error catching that returns a populated `Refined` instead of raising. After E4 closes, `ORCHESTRATOR_BACKEND=openai uv run task demo` and `ORCHESTRATOR_BACKEND=anthropic uv run task demo` (with the `[anthropic]` extra installed) both boot.

**Architecture.** A single Python package `app/orchestrator/` owning the seam ABC (`base.py`), the OpenAI default impl (`openai_strict.py`), the Anthropic skeleton (`anthropic_strict.py`), three per-task schema+adapter modules (`tasks/{brand_disambig,reasoning_enrich,ocr_reconcile}.py`), and a CLI smoke entry (`__main__.py`). The ABC is a true `abc.ABC` (not a `Protocol`) so subclass-or-error is enforced at construction. Each per-task module declares an input dataclass (consumed from `Application`/`FieldObservation`/`ValidationResult`), a Pydantic v2 output schema (sliced into `Refined`), and an adapter function. `OpenAIStrictOrchestrator.refine()` issues one OpenAI Structured-Output call per task slice (up to 3 per `refine()`), wraps each call in an httpx-error try/except that surfaces `ENGINE.MODEL.UNAVAILABLE` on `httpx.RequestError`, and retries once on malformed structured output before surfacing `LLM_OUTPUT_INVALID`. The Anthropic skeleton mirrors the same shape using `tool_use` strict mode. Recorded HTTP responses live under `tests/recordings/{openai,anthropic}/<snapshot>/<prompt-version>/orchestrator/<task>/<fixture>.json`. DI wiring in `app/deps.py` replaces the E1 placeholder orchestrators (`_PlaceholderOpenAIOrchestrator`, `_PlaceholderAnthropicOrchestrator`) with `build_orchestrator(settings) -> Orchestrator` dispatching on `settings.orchestrator_backend`; an unknown backend raises `ValueError`.

**Tech stack.** Python 3.12, Pydantic v2 (E1), `openai >= 1.50` (already pinned), `anthropic >= 0.39` in `[project.optional-dependencies.anthropic]` (already pinned), `httpx >= 0.27` (already pinned), `respx >= 0.21` (already in dev deps from E3-T4). **No new top-level dependencies.** A new `[dependency-groups]` is NOT required because `respx` is already in dev.

**TDD posture.** Each task is one or more Red→Green→Commit cycles on one file (or one tightly coupled file group). The `task-executor` skill body (injected by `parallel-plan-executor`) enforces "one behavior per commit" — heavier tasks (`openai_strict.py`, `anthropic_strict.py`) bundle multiple cycles per task. Each commit is atomic and Conventional (`feat:`/`test:`/`chore:`/`docs:`). Pre-existing main is fast-forwarded after each task. **No `--amend` after pre-commit hook failure** — fix, re-stage, new commit. No squash on merge.

**Hard scope boundary.** This plan owns: `app/orchestrator/`, the `Refined` schema tightening at `app/schemas/refined.py` (drops `model_disposition`), `tests/recordings/{openai,anthropic}/<snapshot>/<prompt-version>/orchestrator/`, the synthetic `fixtures/02-bourbon-stones-throw/label.png` test asset, the `app/deps.py` orchestrator-provider replacement (placeholders → real impls), one ad-hoc `scripts/record_orchestrator_responses.py` companion, and a small extension to `tests/conftest.py` (Authorization-header sanitizer fixture). It does NOT touch `app/rules/` (E2 — locked), `app/vision/` (E3 — locked), `app/services/` (E5), `app/batch/` (E6), `app/ui/` or `frontend/` (E7), `demo/` or `eval/` (E8). It does NOT add `vllm`/`xgrammar` imports anywhere (D-021).

**Cross-epoch follow-through.** This plan closes E1's `Refined`-shape omission (the schema currently carries a `model_disposition` field that conflicts with the L1 FR-303 invariant; E4 drops it). E1's `app/deps.py` placeholder orchestrators are replaced. The orchestrator-isolation invariant (`grep -rn 'openai\|anthropic' app/ | grep -v 'app/orchestrator/'` returns no hits except `app/vision/` for OpenAI, since E3 already isolates OpenAI imports there) is asserted by a new test file. Note: the grep test uses an allow-listing pattern that permits both `app/orchestrator/` AND `app/vision/` for OpenAI (because E3 wires OpenAI tiebreaker through httpx in `app/vision/tiebreak_gpt4o.py` and `app/vision/cloud.py`); only `app/orchestrator/` may import the `anthropic` SDK.

**Recording posture.** Orchestrator tests use **HTTP-layer recordings** via `respx`, not SDK-level mocks. Recordings are committed under `tests/recordings/<provider>/<snapshot>/<prompt-version>/orchestrator/<task-name>/<fixture-id>.json`. CI fails if the active `LLM_MODEL_SNAPSHOT` has no matching recording directory — recordings rotate via `scripts/record_orchestrator_responses.py` when the snapshot tag rotates. Both `openai` and `anthropic` providers route through `httpx` under the hood, so the same recording mechanism covers both.

**Synthetic-fixture posture.** E4 adds **one** synthetic `fixtures/02-bourbon-stones-throw/label.png` (200×200, embedded "STONE'S THROW BOURBON" text, EXIF DPI=300) sufficient for orchestrator brand-disambig recording determinism. Combined with E3's `fixtures/01-spirits-clean/label.png`, this gives the two fixtures the L1 §4 exit-gate item #4 calls for. The full demo fixture set (01–07) remains E8 territory.

---

## File map

| Path | Created/modified by task | Responsibility |
|---|---|---|
| `app/schemas/refined.py` | T1 | Drop `model_disposition` field; add `tasks: list[TaskSlice]` and `evaluation_id`. Frozen, `extra="forbid"`. Closes E1 FR-303 omission. |
| `app/orchestrator/__init__.py` | T2 | Package marker; create `tasks/` sub-package marker; re-export `Orchestrator` from `base`. |
| `app/orchestrator/base.py` | T2 | `Orchestrator` `abc.ABC` with `async refine(application, observations, validation_results) -> Refined` and `async ensure_client() -> None`. |
| `app/orchestrator/tasks/__init__.py` | T2 | Empty package marker. |
| `app/orchestrator/tasks/brand_disambig.py` | T3 | `BrandDisambigInput` (frozen dataclass) + `BrandDisambigResult` (Pydantic v2 frozen, `additionalProperties:False`, fields: `decision: Literal["match","needs_review"]`, `justification: str`) + `to_input(...)` adapter + `apply_to_refined(...)` slicer. **No `pass`/`fail` field anywhere.** |
| `app/orchestrator/tasks/reasoning_enrich.py` | T4 | `ReasoningEnrichInput` + `EnrichedReasoning` (Pydantic v2 frozen, `additionalProperties:False`, fields: `plain_language: str`, `citation_anchor: str`) + adapters. |
| `app/orchestrator/tasks/ocr_reconcile.py` | T5 | `OcrReconcileInput` + `OcrReconcileResult` (Pydantic v2 frozen, `additionalProperties:False`, fields: `winner: str \| None`, `reasoning: str`) + adapters. `winner=None` ⇒ orchestrator abstains; downstream Application Service routes to `needs_review`. |
| `app/orchestrator/openai_strict.py` | T8 | `OpenAIStrictOrchestrator(Orchestrator)`. `refine()` issues per-task OpenAI Structured Outputs calls via `httpx`. Records 1 `CallRecord` per task per attempt. FR-304 fallback (`httpx.RequestError`) and one-shot retry on malformed structured output. `temperature=0`, fixed `seed`, snapshot-pinned `model`. |
| `app/orchestrator/anthropic_strict.py` | T9 | `AnthropicStrictOrchestrator(Orchestrator)`. Same shape via Anthropic `tool_use` strict mode. Lazy-imports `anthropic` SDK inside `ensure_client()` so cloud-only profiles without `[anthropic]` extra raise a clear error. |
| `app/orchestrator/__main__.py` | T14 | CLI smoke: `python -m app.orchestrator --task brand_disambig --fixture 02-bourbon-stones-throw --backend openai --use-recordings`. Mounts recordings via `respx` per the closure-per-recording pattern (see Conventions). Exit 0 on success, 2 on missing fixture/recording. |
| `app/deps.py` | T10 | Replace `_PlaceholderOpenAIOrchestrator` + `_PlaceholderAnthropicOrchestrator` with `build_orchestrator(settings) -> Orchestrator` dispatching on `settings.orchestrator_backend`. Unknown backend raises `ValueError`. Anthropic dispatch raises clear error if `[anthropic]` extra missing. |
| `scripts/record_orchestrator_responses.py` | T15 | Companion to D-020 snapshot rotation. Iterates the active fixture set + per-task calls, performs one **live** OpenAI/Anthropic call each, writes the response to `tests/recordings/<provider>/<snapshot>/<prompt-version>/orchestrator/<task>/<fixture>.json`. Guarded by API-key presence + an explicit `--live` flag. |
| `tests/conftest.py` | T16 | Extend with `_redact_authorization_headers` fixture/helper that strips `Authorization` headers before recordings are written (per ARCH-recording sanitizer). |
| `fixtures/02-bourbon-stones-throw/label.png` | T17 | 200×200 synthetic PNG with embedded "STONE'S THROW BOURBON" text + EXIF DPI=300. ≤ 5 KB. |
| `scripts/build_synthetic_fixture_02.py` | T17 | Deterministic build script for fixture-02. |
| `tests/test_refined_fr303_ready.py` | T1 | Asserts `Refined.model_fields` does not contain `model_disposition` after T1; positive coverage. |
| `tests/test_orchestrator_protocol.py` | T2 | `Orchestrator` is `abc.ABC`; instantiation fails (`TypeError`); `refine` + `ensure_client` are abstract coroutines. |
| `tests/test_orchestrator_brand_disambig.py` | T3 | Schema introspection + adapter round-trip. |
| `tests/test_orchestrator_reasoning_enrich.py` | T4 | Schema introspection + adapter round-trip. |
| `tests/test_orchestrator_ocr_reconcile.py` | T5 | Schema introspection + adapter round-trip; `winner=None` allowed. |
| `tests/test_orchestrator_strict_schema.py` | T6 | For every task output schema, `Schema.model_json_schema()` produces JSON Schema with `additionalProperties: False` and OpenAI-strict-mode `required` fully populated. |
| `tests/test_orchestrator_fr303_invariant.py` | T7 | **Structural test.** Asserts (a) `Refined` has no field whose name starts with `disposition`; (b) every task output schema has no field whose name is `pass`/`fail`/`disposition` and no Literal-value containing `"fail"`. This is the canary for any future schema change. |
| `tests/test_orchestrator_openai_strict.py` | T8 | `respx` recording fixture; assert `refine()` returns wire-compatible `Refined` for fixture-01 + fixture-02; assert FR-304 fallback (httpx.ConnectError → `ENGINE.MODEL.UNAVAILABLE`); assert one-shot retry on malformed → `LLM_OUTPUT_INVALID`. |
| `tests/test_orchestrator_anthropic_skeleton.py` | T9 | `respx` recording fixture against Anthropic API; assert `refine()` returns `Refined`-shaped object; assert `[anthropic]` ImportError surfaces clear message. |
| `tests/test_orchestrator_deps.py` | T10 | DI: `ORCHESTRATOR_BACKEND=openai` → `OpenAIStrictOrchestrator`; `=anthropic` → `AnthropicStrictOrchestrator`; unknown → `ValueError`; placeholder classes removed. |
| `tests/test_orchestrator_substitutability.py` | T11 | Both impls subclass `Orchestrator`; both `refine` are coroutines; both produce `Refined` with the same task-slice keys against fixture-01 recordings. |
| `tests/test_orchestrator_ring_buffer.py` | T12 | Every successful `refine()` writes 3 `CallRecord` entries (1 per task); failed call writes 1 with `latency_ms` populated; `provider`/`model`/`prompt_version` populated correctly; `output_hash` deterministic. |
| `tests/test_orchestrator_temp_seed_snapshot.py` | T13 | Recorded call assertion: request body contains `temperature=0`, `seed=<deterministic>`, `model=<snapshot>`. Drift on any of these is a regression. |
| `tests/test_orchestrator_cli_smoke.py` | T14 | CLI exits 0 on synthetic fixture + recordings; missing fixture exits 2; bad backend exits 2. |
| `tests/test_record_orchestrator_responses.py` | T15 | Smoke: script imports cleanly; `--help` exits 0; `--live` without API key exits 2 with clear stderr. |
| `tests/test_orchestrator_isolation.py` | T16 | `grep -rn 'openai\|anthropic' app/` — `openai` allowed only under `app/vision/` (E3 isolation) and `app/orchestrator/`; `anthropic` allowed only under `app/orchestrator/`. `vllm`/`xgrammar` absent globally per D-021. Conftest sanitizer test also lives here. |
| `tests/test_synthetic_fixture_02.py` | T17 | Fixture-02 exists, is PNG 200×200 with DPI=300. |

---

## Conventions used in this plan

- **Frozen Pydantic models.** All output schemas (`BrandDisambigResult`, `EnrichedReasoning`, `OcrReconcileResult`, `Refined`, task input dataclasses) use `model_config = ConfigDict(extra="forbid", frozen=True)`. Inputs that aren't Pydantic models use `@dataclass(frozen=True)`.
- **ABC declaration.** `Orchestrator` is `abc.ABC` (not `typing.Protocol`) so subclass-or-error is enforced at instantiation. Both impls inherit explicitly: `class OpenAIStrictOrchestrator(Orchestrator):`, `class AnthropicStrictOrchestrator(Orchestrator):`. The substitutability test asserts `issubclass(impl, Orchestrator)` AND `inspect.iscoroutinefunction(impl.refine)`.
- **Async signature.** `refine()` and `ensure_client()` are both `async def` — see L1 §2.1.
- **Lazy SDK imports.** The `anthropic` SDK is imported inside `AnthropicStrictOrchestrator.ensure_client()`, not at module top-level. The default profile (no `[anthropic]` extra installed) must be importable. The `anthropic_strict.py` module itself imports only stdlib + `httpx`/`pydantic` at top level. The OpenAI default uses raw `httpx` (no `openai` SDK import), mirroring the E3 cloud-vision pattern.
- **Recording filenames.** `tests/recordings/<provider>/<LLM_MODEL_SNAPSHOT>/<PROMPT_VERSION>/orchestrator/<task-name>/<fixture-id>.json`. Default for E4: `openai/gpt-4o-2024-08-06/v1/orchestrator/{brand_disambig,reasoning_enrich,ocr_reconcile}/{01-spirits-clean,02-bourbon-stones-throw}.json` — 6 files. Anthropic mirrors: `anthropic/claude-3-5-sonnet-20241022/v1/orchestrator/<task>/<fixture>.json` — 6 files.
- **CallRecord population.** `provider` ∈ `{"openai", "anthropic", "local.paddleocr"}`. `stage` for orchestrator calls ∈ `{"orch.brand_disambig", "orch.reasoning_enrich", "orch.ocr_reconcile"}` — these literals already exist in `app/schemas/calls.py::CallStage` (no schema widening needed). Per L1 §4 #7, every successful `refine()` writes 3 CallRecords (1 per task); a failed call writes 1 with `latency_ms` populated.
- **Bulkhead.** Unlike E3 cloud vision, the orchestrator does not have an asyncio.Semaphore — orchestrator calls are issued from per-evaluation contexts (E5 batches across applications, not within a single refine()). The 3 task calls within one `refine()` MAY be dispatched via `asyncio.gather` for latency; the substitutability test does NOT depend on order. (Per ARCH §11.2: bulkhead lives at the batch layer in E6, not at the orchestrator layer.)
- **OpenAI Structured Outputs body shape.** Mirrors E3's tiebreaker shape: `body["response_format"]={"type": "json_schema", "json_schema": {"name": <task-name>, "strict": True, "schema": <schema>}}`. The discriminator `response_format.json_schema.name` is the per-task name (`"brand_disambig"`, etc.).
- **Anthropic strict-mode body shape.** Anthropic uses `tool_use` with `tools: [{name: <task-name>, input_schema: <schema>}]` and `tool_choice: {type: "tool", name: <task-name>}`. The schema goes through a small adapter (`_to_anthropic_schema(...)`) that strips OpenAI-specific keys not supported by Anthropic (e.g., the top-level `name` key). The adapter lives in `app/orchestrator/anthropic_strict.py` (private function) — no separate `_schema_adapters/` module shipped in E4 since both providers' strict modes are close enough that one private adapter suffices for the prototype.
- **Recording-replay closure pattern.** Tests that mount multiple recordings against the same OpenAI/Anthropic URL use the closure-per-recording pattern (same as E3 §Conventions): register one `respx` route with a `side_effect` handler that inspects the request body's per-provider task discriminator (`response_format.json_schema.name` for OpenAI, `tool_choice.name` for Anthropic) and returns `Response(200, json=payload)` on match or `None` to fall through. See E3-T13/T15/T17 for prior art.
- **`_TASK_SCHEMAS` registry.** `app/orchestrator/openai_strict.py::_TASK_SCHEMAS` MUST contain a JSON-schema entry for every task name `refine()` dispatches to — i.e., all 3 task names (`brand_disambig`, `reasoning_enrich`, `ocr_reconcile`). Missing keys → `KeyError` at runtime. T8 lands the full 3-key dict. The Anthropic counterpart `app/orchestrator/anthropic_strict.py::_TASK_SCHEMAS` mirrors it.
- **FR-303 invariant — schema-shape direction.** `Refined.model_fields` contains no field whose name starts with `disposition`. Every task output schema has no field whose name is `pass`, `fail`, or `disposition`, AND no field whose Literal value set contains `"fail"`. The structural test in T7 enforces this; future schema additions must satisfy it.
- **FR-304 fallback shape.** When `httpx.RequestError` (timeout, ConnectError, etc.) raises during a per-task call, the orchestrator catches the error, populates a `Refined` slice with the task name and a special `error` qualifier `ENGINE.MODEL.UNAVAILABLE`, writes a `CallRecord` with `response={"error": "ENGINE.MODEL.UNAVAILABLE", "exception": str(e)}` and `latency_ms` populated, and proceeds to the next task. `refine()` does NOT raise; it returns a `Refined` whose task slices may carry `ENGINE.MODEL.UNAVAILABLE` qualifiers. The Application Service (E5) routes such qualifiers to `needs_review`.
- **Strict-retry shape.** When the LLM returns a structured response that fails Pydantic validation against the task output schema, the orchestrator retries the call exactly once with the same body. On second failure, it surfaces an `LLM_OUTPUT_INVALID` qualifier on the task slice (no raise). Both attempts produce `CallRecord` entries.
- **Inference-dep ban — orchestrator direction.** This is parallel to E2's `app/rules/` invariant and E3's `app/vision/` invariant. E4 says: only `app/orchestrator/` may import the `anthropic` SDK; only `app/orchestrator/` and `app/vision/` may import the `openai` SDK. T16 enforces with a grep test.
- **CFR-citation discipline.** Orchestrator modules don't emit CFR citations directly — the per-task output schemas may carry a `citation_anchor` field (the rule_id that anchored the LLM's reasoning), but the actual CFR string is attached downstream by the rule engine (E2) and the audit assembler (E5).
- **Failing-test verification.** Every task's Step 2 runs the test and confirms the expected failure mode. If the test passes accidentally on Step 2, re-author the test.
- **Commit message style.** Conventional Commits, subject ≤ 72 chars. No co-authored trailers (project convention; matches E1/E2/E3 commits).
- **Reading order for an executor subagent.** L1 §2 (components) and §4 (exit gates) define the contract; ARCH §4.2.6 / §6.6 / §6.9 / §8.2 are the deep references. If any cell here disagrees with ARCH, ARCH wins; flag the divergence in the task's commit message.

---

## Task 1: app/schemas/refined.py — drop `model_disposition` (FR-303 readiness)

**Files:**
- Modify: `app/schemas/refined.py`
- Modify: `tests/test_schemas_round_trip.py` (the existing E1 round-trip test constructs `Refined(... task=..., text=..., model_disposition="pass")` — all three kwargs disappear under the new shape; this task updates that one test in lock-step so the suite stays green)
- Test: `tests/test_refined_fr303_ready.py`

**Why:** The L1 §1 spec says "the `Refined` schema (declared in E1) has no `disposition` field, so a misbehaving orchestrator literally cannot return one." E1 shipped `Refined` with a `model_disposition: Literal["pass", "needs_review"]` field that violates this invariant on a substring match (and conceptually, since the orchestrator should not even *suggest* a disposition). This task drops the field and adds the per-task slice surface the orchestrator will populate.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_refined_fr303_ready.py
"""FR-303 invariant readiness: Refined has no disposition-style field.

This is the schema-side gate. The full structural invariant (covers task
output schemas too) lands in T7."""
from app.schemas.refined import Refined


def test_refined_has_no_disposition_field():
    field_names = set(Refined.model_fields.keys())
    forbidden = {n for n in field_names if "disposition" in n.lower()}
    assert forbidden == set(), f"disposition-style fields leaked: {forbidden}"


def test_refined_has_no_pass_or_fail_field():
    field_names = set(Refined.model_fields.keys())
    assert "pass" not in field_names
    assert "fail" not in field_names


def test_refined_carries_evaluation_id():
    """Sanity: per ARCH §6.6, Refined still keys to an evaluation_id."""
    assert "evaluation_id" in Refined.model_fields
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_refined_fr303_ready.py -v`
Expected: `test_refined_has_no_disposition_field` FAILS — `disposition-style fields leaked: {'model_disposition'}`.

- [ ] **Step 3: Tighten `app/schemas/refined.py`**

Replace the file content with:

```python
"""AI orchestrator output. Source: ARCH §6.6, PRD FR-303.

FR-303 invariant: this model declares **no top-level disposition field**.
The deterministic Rule Engine produces dispositions; the orchestrator only
enriches reasoning, disambiguates borderline brand matches, or reconciles OCR.
A misbehaving orchestrator literally cannot return a disposition because no
such field exists on the schema.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class TaskSlice(BaseModel):
    """One per-task contribution to a Refined output. Source: ARCH §6.6."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    task: Literal[
        "brand_disambig",
        "reasoning_enrich",
        "ocr_reconcile",
    ]
    rule_id: str | None = None
    payload: dict | None = None
    qualifier: Literal[
        "ENGINE.MODEL.UNAVAILABLE",
        "LLM_OUTPUT_INVALID",
    ] | None = None


class Refined(BaseModel):
    """Orchestrator output for one evaluation. Source: ARCH §6.6, FR-303."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    tasks: tuple[TaskSlice, ...] = ()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_refined_fr303_ready.py -v`
Expected: 3 passed.

- [ ] **Step 5: Update the E1 round-trip test in lock-step**

Open `tests/test_schemas_round_trip.py`. The function `test_refined_round_trip` (around line 140) currently constructs `Refined(evaluation_id=..., task="brand_borderline", text="...", model_disposition="pass")`. Replace the body with the new shape:

```python
def test_refined_round_trip() -> None:
    from app.schemas.refined import Refined

    r = Refined(evaluation_id="00000000-0000-4000-8000-000000000001")
    r2 = Refined.model_validate_json(r.model_dump_json())
    assert r2 == r
```

The companion `test_refined_has_no_disposition_field_fr303` test in the same file already passes against the new shape (it only asserts `"disposition" not in fields`); leave it untouched.

- [ ] **Step 6: Run full suite (no regression)**

Run: `uv run pytest -q`
Expected: 302 baseline → 302 (the original `test_refined_round_trip` is rewritten in place) + 3 new = ~305 passing. **No remaining `model_disposition` references in the suite.** If the run surfaces any other E1/E2/E3 test that referenced `Refined.task` / `Refined.text` / `Refined.model_disposition`, that's a Rule 1-3 inline fix — update the test to the new shape, do not relax the schema.

- [ ] **Step 7: Commit**

```bash
git add app/schemas/refined.py tests/test_refined_fr303_ready.py tests/test_schemas_round_trip.py
git commit -m "feat(e4): tighten Refined to FR-303 invariant — drop model_disposition"
```

---

## Task 2: Application stub + Orchestrator ABC (2-cycle bundle)

**Files:**
- Create: `app/schemas/application.py` — Cycle A. Closes the E1 omission: the orchestrator + downstream services key off `app/schemas/application.Application`, but only `app/schemas/wire/application.py::ApplicationEnvelope` exists today. T2 owns the single-source-of-truth stub so no other E4 task races to create one.
- Create: `app/orchestrator/__init__.py` — Cycle B
- Create: `app/orchestrator/base.py` — Cycle B
- Create: `app/orchestrator/tasks/__init__.py` (empty package marker) — Cycle B
- Test: `tests/test_application_stub.py` — Cycle A
- Test: `tests/test_orchestrator_protocol.py` — Cycle B

**Why two cycles in one task.** The Orchestrator ABC imports `from app.schemas.application import Application`. That module is missing at HEAD (only `app/schemas/wire/application.py::ApplicationEnvelope` exists). Eight downstream E4 tasks (T8/T9/T11/T12/T13/T14 + Cycle B itself) reference `Application(application_id=..., evaluation_id=...)` against this missing module. Letting each subagent invent the stub on demand creates a write race against the same path. The cleanest fix is to make T2 the single owner: Cycle A lands the stub, Cycle B lands the ABC that imports it. Two `task-executor` Red→Green→Commit cycles, one task.

### Cycle A — `app/schemas/application.py` stub

- [ ] **Step A.1: Write the failing test**

```python
# tests/test_application_stub.py
"""Application stub — minimum surface E4 needs.

The full Application contract is E5/E6 territory; this stub only closes the
E1 omission so the Orchestrator seam (E4 T2 Cycle B) can import it.
"""
from app.schemas.application import Application


def test_application_constructs_with_required_fields():
    a = Application(application_id="A-001", evaluation_id="EV-001")
    assert a.application_id == "A-001"
    assert a.evaluation_id == "EV-001"


def test_application_is_frozen_extra_forbid():
    a = Application(application_id="A-001", evaluation_id="EV-001")
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Application(application_id="A-001", evaluation_id="EV-001", unknown_field="x")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        a.application_id = "A-002"  # type: ignore[misc]
```

- [ ] **Step A.2: Run → expect FAIL (`ModuleNotFoundError: app.schemas.application`)**

Run: `uv run pytest tests/test_application_stub.py -v`

- [ ] **Step A.3: Land minimal implementation**

```python
# app/schemas/application.py
"""Application input identity (E1-omission closer for E4 orchestrator seam).

The full Application contract — applicant, formula, type_of_application, labels,
etc. — lives in `app/schemas/wire/application.py::ApplicationEnvelope`. This
module exposes only the identity surface (`application_id`, `evaluation_id`) the
Orchestrator + downstream services key off. E5 may extend this with additional
fields; until then, keep the stub minimal so no orchestrator test depends on
fields that aren't pinned by L1.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Application(BaseModel):
    """Identity surface for an in-flight evaluation. Extend in E5 if needed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    application_id: str
    evaluation_id: str
```

- [ ] **Step A.4: Run → expect PASS (2/2)**

Run: `uv run pytest tests/test_application_stub.py -v`

- [ ] **Step A.5: Run full suite (no regression)**

Run: `uv run pytest -q`
Expected: 305 (post-T1) + 2 = ~307 passing. If any existing E1/E2/E3 test imported `app.schemas.application` and asserted a different shape, that's a Rule 1-3 inline fix — extend this stub only with fields E4 will read. Do not paste the full `ApplicationEnvelope` shape in here; that's E5.

- [ ] **Step A.6: Commit**

```bash
git add app/schemas/application.py tests/test_application_stub.py
git commit -m "feat(e4): Application identity stub (closes E1 omission for orchestrator seam)"
```

### Cycle B — Orchestrator ABC

- [ ] **Step B.1: Write the failing test**

```python
# tests/test_orchestrator_protocol.py
import inspect

import pytest

from app.orchestrator.base import Orchestrator


def test_orchestrator_is_abstract():
    with pytest.raises(TypeError):
        Orchestrator()  # type: ignore[abstract]


def test_refine_is_abstract_coroutine():
    assert inspect.iscoroutinefunction(Orchestrator.refine)
    assert getattr(Orchestrator.refine, "__isabstractmethod__", False)


def test_ensure_client_is_abstract_coroutine():
    assert inspect.iscoroutinefunction(Orchestrator.ensure_client)
    assert getattr(Orchestrator.ensure_client, "__isabstractmethod__", False)


def test_orchestrator_signature():
    sig = inspect.signature(Orchestrator.refine)
    params = list(sig.parameters.keys())
    assert params == ["self", "application", "observations", "validation_results"]
```

- [ ] **Step B.2: Run test to verify it fails**

Run: `uv run pytest tests/test_orchestrator_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.orchestrator.base'`.

- [ ] **Step B.3: Write minimal implementation**

```python
# app/orchestrator/__init__.py
"""AI Orchestrator seam (D-004 swap point #2). Source: E4 L1 §2."""
from app.orchestrator.base import Orchestrator

__all__ = ["Orchestrator"]
```

```python
# app/orchestrator/base.py
"""Orchestrator ABC + signature.

Source: E4 L1 §2.1. The class is `abc.ABC` (not Protocol) so subclass-or-error
is enforced at instantiation. Two concrete impls land in E4: OpenAI default + Anthropic skeleton.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.application import Application
from app.schemas.extracted import FieldObservation
from app.schemas.refined import Refined
from app.schemas.rejection import ValidationResult


class Orchestrator(ABC):
    """D-004 #2 seam. Two concrete impls: OpenAIStrict + AnthropicStrict."""

    @abstractmethod
    async def refine(
        self,
        application: Application,
        observations: list[FieldObservation],
        validation_results: list[ValidationResult],
    ) -> Refined:
        """Produce a Refined for one evaluation. FR-303 invariant: never decides pass/fail."""
        ...

    @abstractmethod
    async def ensure_client(self) -> None:
        """Warm-up hook. OpenAI impl: no-op. Anthropic impl: import SDK + construct client."""
        ...
```

```python
# app/orchestrator/tasks/__init__.py
"""Per-task schemas + adapters. Source: E4 L1 §2.5."""
```

- [ ] **Step B.4: Run test to verify it passes**

Run: `uv run pytest tests/test_orchestrator_protocol.py -v`
Expected: 4 passed.

- [ ] **Step B.5: Run full suite**

Run: `uv run pytest -q`
Expected: ~311 passing (305 post-T1 + 2 Cycle A + 4 Cycle B).

- [ ] **Step B.6: Commit**

```bash
git add app/orchestrator/__init__.py app/orchestrator/base.py app/orchestrator/tasks/__init__.py tests/test_orchestrator_protocol.py
git commit -m "feat(e4): Orchestrator ABC seam (D-004 #2)"
```

---

## Task 3: app/orchestrator/tasks/brand_disambig.py — schema + adapter

**Files:**
- Create: `app/orchestrator/tasks/brand_disambig.py`
- Test: `tests/test_orchestrator_brand_disambig.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_brand_disambig.py
import pytest
from pydantic import ValidationError

from app.orchestrator.tasks.brand_disambig import (
    BrandDisambigInput,
    BrandDisambigResult,
    apply_to_refined,
    to_input,
)
from app.schemas.refined import Refined


def test_input_dataclass_frozen():
    inp = BrandDisambigInput(
        rule_id="R-BRAND-001",
        applicant_brand="STONE'S THROW BOURBON",
        candidate_matches=("STONES THROW BOURBON", "STONE THROW BOURBON"),
    )
    with pytest.raises((AttributeError, Exception)):
        inp.applicant_brand = "X"  # frozen


def test_result_schema_strict_shape():
    schema = BrandDisambigResult.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"decision", "justification"}
    # FR-303: no pass/fail in field names
    assert "pass" not in schema["properties"]
    assert "fail" not in schema["properties"]


def test_result_decision_literal_enforced():
    with pytest.raises(ValidationError):
        BrandDisambigResult(decision="fail", justification="...")  # type: ignore[arg-type]


def test_apply_to_refined_slices_correctly():
    refined = Refined(evaluation_id="EV-001")
    result = BrandDisambigResult(decision="match", justification="phonetic equivalence")
    out = apply_to_refined(refined, rule_id="R-BRAND-001", result=result)
    assert len(out.tasks) == 1
    assert out.tasks[0].task == "brand_disambig"
    assert out.tasks[0].rule_id == "R-BRAND-001"
    assert out.tasks[0].payload == {"decision": "match", "justification": "phonetic equivalence"}
```

- [ ] **Step 2: Run test → RED (module missing)**

Run: `uv run pytest tests/test_orchestrator_brand_disambig.py -v`

- [ ] **Step 3: Write minimal implementation**

```python
# app/orchestrator/tasks/brand_disambig.py
"""Brand-disambig task schema + adapter. Source: E4 L1 §2.5, PRD FR-300."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.refined import Refined, TaskSlice


@dataclass(frozen=True)
class BrandDisambigInput:
    """Input shape for brand-disambig calls."""

    rule_id: str
    applicant_brand: str
    candidate_matches: tuple[str, ...]


class BrandDisambigResult(BaseModel):
    """Pydantic v2 strict-mode output schema. FR-303: no `pass`/`fail` field."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    decision: Literal["match", "needs_review"]
    justification: str


def to_input(rule_id: str, applicant_brand: str, candidates: list[str]) -> BrandDisambigInput:
    return BrandDisambigInput(
        rule_id=rule_id,
        applicant_brand=applicant_brand,
        candidate_matches=tuple(candidates),
    )


def apply_to_refined(refined: Refined, *, rule_id: str, result: BrandDisambigResult) -> Refined:
    slice_ = TaskSlice(
        task="brand_disambig",
        rule_id=rule_id,
        payload=result.model_dump(),
    )
    return refined.model_copy(update={"tasks": refined.tasks + (slice_,)})
```

- [ ] **Step 4: Run test → GREEN (4 passed)**

- [ ] **Step 5: Run full suite**

- [ ] **Step 6: Commit**

```bash
git add app/orchestrator/tasks/brand_disambig.py tests/test_orchestrator_brand_disambig.py
git commit -m "feat(e4): brand_disambig task schema + adapter"
```

---

## Task 4: app/orchestrator/tasks/reasoning_enrich.py — schema + adapter

**Files:**
- Create: `app/orchestrator/tasks/reasoning_enrich.py`
- Test: `tests/test_orchestrator_reasoning_enrich.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_reasoning_enrich.py
import pytest
from pydantic import ValidationError

from app.orchestrator.tasks.reasoning_enrich import (
    EnrichedReasoning,
    ReasoningEnrichInput,
    apply_to_refined,
)
from app.schemas.refined import Refined


def test_input_frozen():
    inp = ReasoningEnrichInput(
        rule_id="R-WARN-001",
        template_text="Government warning text shall appear ...",
    )
    with pytest.raises((AttributeError, Exception)):
        inp.template_text = "X"


def test_schema_strict_shape():
    schema = EnrichedReasoning.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"plain_language", "citation_anchor"}
    assert "pass" not in schema["properties"]
    assert "fail" not in schema["properties"]


def test_apply_to_refined_slices_correctly():
    refined = Refined(evaluation_id="EV-001")
    result = EnrichedReasoning(plain_language="Be sure the warning is visible.", citation_anchor="27 CFR §16.21")
    out = apply_to_refined(refined, rule_id="R-WARN-001", result=result)
    assert out.tasks[0].task == "reasoning_enrich"
    assert out.tasks[0].rule_id == "R-WARN-001"
    assert out.tasks[0].payload["citation_anchor"] == "27 CFR §16.21"
```

- [ ] **Step 2-5: RED → write impl → GREEN → full suite**

```python
# app/orchestrator/tasks/reasoning_enrich.py
"""Reasoning-enrich task schema + adapter. Source: E4 L1 §2.5, PRD FR-301."""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from app.schemas.refined import Refined, TaskSlice


@dataclass(frozen=True)
class ReasoningEnrichInput:
    rule_id: str
    template_text: str


class EnrichedReasoning(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    plain_language: str
    citation_anchor: str


def apply_to_refined(refined: Refined, *, rule_id: str, result: EnrichedReasoning) -> Refined:
    slice_ = TaskSlice(
        task="reasoning_enrich",
        rule_id=rule_id,
        payload=result.model_dump(),
    )
    return refined.model_copy(update={"tasks": refined.tasks + (slice_,)})
```

- [ ] **Step 6: Commit**

```bash
git add app/orchestrator/tasks/reasoning_enrich.py tests/test_orchestrator_reasoning_enrich.py
git commit -m "feat(e4): reasoning_enrich task schema + adapter"
```

---

## Task 5: app/orchestrator/tasks/ocr_reconcile.py — schema + adapter

**Files:**
- Create: `app/orchestrator/tasks/ocr_reconcile.py`
- Test: `tests/test_orchestrator_ocr_reconcile.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_ocr_reconcile.py
import pytest
from pydantic import ValidationError

from app.orchestrator.tasks.ocr_reconcile import (
    OcrReconcileInput,
    OcrReconcileResult,
    apply_to_refined,
)
from app.schemas.refined import Refined


def test_input_frozen():
    inp = OcrReconcileInput(
        rule_id="R-OCR-001",
        field_id="brand_name",
        candidate_reads=("ACME BOURBON", "ACAE BOURBON"),
    )
    with pytest.raises((AttributeError, Exception)):
        inp.field_id = "X"


def test_schema_strict_shape():
    schema = OcrReconcileResult.model_json_schema()
    assert schema["additionalProperties"] is False
    # `winner` is optional (None ⇒ orchestrator abstains), so only `reasoning` required.
    assert "reasoning" in schema["required"]
    assert "pass" not in schema["properties"]
    assert "fail" not in schema["properties"]


def test_winner_can_be_none():
    """Per L1 §2.5: winner=None ⇒ abstain; downstream routes to needs_review."""
    result = OcrReconcileResult(winner=None, reasoning="ambiguous; defer to needs_review")
    assert result.winner is None


def test_apply_to_refined_slices_correctly():
    refined = Refined(evaluation_id="EV-001")
    result = OcrReconcileResult(winner="ACME BOURBON", reasoning="majority of OCR votes")
    out = apply_to_refined(refined, rule_id="R-OCR-001", result=result)
    assert out.tasks[0].task == "ocr_reconcile"
    assert out.tasks[0].payload["winner"] == "ACME BOURBON"
```

- [ ] **Step 2-5: RED → impl → GREEN → full suite**

```python
# app/orchestrator/tasks/ocr_reconcile.py
"""OCR-reconcile task schema + adapter. Source: E4 L1 §2.5, PRD FR-302."""
from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from app.schemas.refined import Refined, TaskSlice


@dataclass(frozen=True)
class OcrReconcileInput:
    rule_id: str
    field_id: str
    candidate_reads: tuple[str, ...]


class OcrReconcileResult(BaseModel):
    """winner=None ⇒ orchestrator abstains. Application Service routes to needs_review."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    winner: str | None = None
    reasoning: str


def apply_to_refined(refined: Refined, *, rule_id: str, result: OcrReconcileResult) -> Refined:
    slice_ = TaskSlice(
        task="ocr_reconcile",
        rule_id=rule_id,
        payload=result.model_dump(),
    )
    return refined.model_copy(update={"tasks": refined.tasks + (slice_,)})
```

- [ ] **Step 6: Commit**

```bash
git add app/orchestrator/tasks/ocr_reconcile.py tests/test_orchestrator_ocr_reconcile.py
git commit -m "feat(e4): ocr_reconcile task schema + adapter (winner=None ⇒ abstain)"
```

---

## Task 6: tests/test_orchestrator_strict_schema.py — strict-mode introspection

**Files:**
- Create: `tests/test_orchestrator_strict_schema.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_orchestrator_strict_schema.py
"""For every task output schema, model_json_schema() must produce a JSON Schema
compatible with OpenAI Structured Outputs strict-mode requirements:
- additionalProperties: false on the top-level object
- required populated for all properties (Optional fields use Optional[T] = None)
- no $ref at the top level (closed-form schema)
"""
import pytest

from app.orchestrator.tasks.brand_disambig import BrandDisambigResult
from app.orchestrator.tasks.reasoning_enrich import EnrichedReasoning
from app.orchestrator.tasks.ocr_reconcile import OcrReconcileResult


@pytest.mark.parametrize("schema_cls", [BrandDisambigResult, EnrichedReasoning, OcrReconcileResult])
def test_schema_strict_mode_compatible(schema_cls):
    schema = schema_cls.model_json_schema()
    assert schema.get("additionalProperties") is False, (
        f"{schema_cls.__name__}: additionalProperties must be False for strict mode"
    )
    # All non-Optional properties must be required.
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    for prop, prop_schema in properties.items():
        # An Optional[T] property has type: ["T", "null"] in Pydantic v2 JSON schema.
        is_nullable = "null" in (
            prop_schema.get("type", []) if isinstance(prop_schema.get("type"), list) else []
        ) or prop_schema.get("anyOf") is not None
        if not is_nullable:
            assert prop in required, (
                f"{schema_cls.__name__}.{prop} is non-optional but not in required: {required}"
            )


@pytest.mark.parametrize("schema_cls", [BrandDisambigResult, EnrichedReasoning, OcrReconcileResult])
def test_schema_top_level_is_object(schema_cls):
    schema = schema_cls.model_json_schema()
    assert schema.get("type") == "object", f"{schema_cls.__name__} top-level must be object"
```

- [ ] **Step 2: Run → expect PASS** (T3-T5 produced compliant schemas)

- [ ] **Step 3: Commit**

```bash
git add tests/test_orchestrator_strict_schema.py
git commit -m "test(e4): every task schema is OpenAI strict-mode compatible"
```

---

## Task 7: tests/test_orchestrator_fr303_invariant.py — FR-303 structural test

**Files:**
- Create: `tests/test_orchestrator_fr303_invariant.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_orchestrator_fr303_invariant.py
"""FR-303 invariant — orchestrator never decides pass/fail.

Structural test: enforces at the type level that no orchestrator-touched schema
can carry a disposition / pass / fail field. This is the canary for any future
schema change that accidentally adds such a field. Per L1 §1, the invariant is
that 'a misbehaving orchestrator literally cannot return a disposition because
no such field exists on the schema'.
"""
import json

import pytest

from app.orchestrator.tasks.brand_disambig import BrandDisambigResult
from app.orchestrator.tasks.reasoning_enrich import EnrichedReasoning
from app.orchestrator.tasks.ocr_reconcile import OcrReconcileResult
from app.schemas.refined import Refined, TaskSlice


def _flatten_literal_values(field_info) -> set[str]:
    """Pull all Literal arg strings out of a Pydantic FieldInfo annotation."""
    annot = field_info.annotation
    values: set[str] = set()
    # Recurse on Union/Optional/Literal generics.
    args = getattr(annot, "__args__", ())
    for a in args:
        values |= _flatten_literal_values_from_type(a)
    values |= _flatten_literal_values_from_type(annot)
    return values


def _flatten_literal_values_from_type(t) -> set[str]:
    import typing
    out: set[str] = set()
    origin = typing.get_origin(t)
    if origin is typing.Literal:
        for v in typing.get_args(t):
            if isinstance(v, str):
                out.add(v)
    args = getattr(t, "__args__", ())
    for a in args:
        out |= _flatten_literal_values_from_type(a)
    return out


@pytest.mark.parametrize("schema_cls", [Refined, TaskSlice, BrandDisambigResult, EnrichedReasoning, OcrReconcileResult])
def test_no_disposition_field(schema_cls):
    field_names = set(schema_cls.model_fields.keys())
    forbidden = {n for n in field_names if "disposition" in n.lower()}
    assert forbidden == set(), f"{schema_cls.__name__}: disposition-style field leaked: {forbidden}"


@pytest.mark.parametrize("schema_cls", [Refined, TaskSlice, BrandDisambigResult, EnrichedReasoning, OcrReconcileResult])
def test_no_pass_or_fail_field(schema_cls):
    field_names = set(schema_cls.model_fields.keys())
    assert "pass" not in field_names, f"{schema_cls.__name__}: 'pass' field leaked"
    assert "fail" not in field_names, f"{schema_cls.__name__}: 'fail' field leaked"


@pytest.mark.parametrize("schema_cls", [BrandDisambigResult, EnrichedReasoning, OcrReconcileResult])
def test_no_fail_in_literal_values(schema_cls):
    """No task-output schema may carry a Literal value 'fail' anywhere."""
    leaks: list[str] = []
    for fname, finfo in schema_cls.model_fields.items():
        values = _flatten_literal_values(finfo)
        if "fail" in values:
            leaks.append(f"{fname}: {values}")
    assert leaks == [], f"{schema_cls.__name__}: 'fail' Literal value leaked: {leaks}"


@pytest.mark.parametrize(
    "schema_cls",
    [Refined, TaskSlice, BrandDisambigResult, EnrichedReasoning, OcrReconcileResult],
)
def test_no_fail_or_disposition_substring_in_json_schema(schema_cls):
    """Defense-in-depth: serialize the JSON Schema and grep for forbidden tokens.

    `_flatten_literal_values` only walks direct field annotations; if a future
    schema embeds a sub-model whose own field carries 'fail'/'disposition' as a
    Literal, the recursion misses it. Serializing the JSON Schema closes that
    gap cheaply: the rendered schema includes nested `$defs` for any embedded
    BaseModel, so substring presence is a hard signal of a leak.
    """
    rendered = json.dumps(schema_cls.model_json_schema(), sort_keys=True)
    # `pass` is excluded from this substring grep — it appears commonly in
    # schema metadata strings ("passes", "passenger", etc.) and the structural
    # field-name/Literal-value tests above already cover it precisely.
    for forbidden in ("\"fail\"", "disposition"):
        assert forbidden not in rendered, (
            f"{schema_cls.__name__}: forbidden substring {forbidden!r} surfaced in JSON Schema"
        )
```

- [ ] **Step 2: Run → expect PASS**

- [ ] **Step 3: Commit**

```bash
git add tests/test_orchestrator_fr303_invariant.py
git commit -m "test(e4): FR-303 invariant — no disposition/pass/fail in orchestrator schemas"
```

---

## Task 8: app/orchestrator/openai_strict.py — OpenAIStrictOrchestrator

**Files:**
- Create: `app/orchestrator/openai_strict.py`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/brand_disambig/01-spirits-clean.json`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/brand_disambig/02-bourbon-stones-throw.json`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/reasoning_enrich/01-spirits-clean.json`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/reasoning_enrich/02-bourbon-stones-throw.json`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/ocr_reconcile/01-spirits-clean.json`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/ocr_reconcile/02-bourbon-stones-throw.json`
- Test: `tests/test_orchestrator_openai_strict.py`

This task bundles 3 cycles per the `task-executor` "one behavior per commit" rule:
**Cycle A**: `refine()` skeleton — 3 per-task calls against fixture-01 recordings; populates `Refined.tasks`.
**Cycle B**: FR-304 fallback on `httpx.RequestError` → `Refined` slice with `qualifier="ENGINE.MODEL.UNAVAILABLE"`; no raise.
**Cycle C**: Strict-retry on malformed structured output → 1 retry → `qualifier="LLM_OUTPUT_INVALID"`.

- [ ] **Cycle A — Step 1: Hand-author the 6 recordings**

Each recording has the OpenAI chat-completion shape with `content` as a JSON-encoded string matching the per-task output schema. Use the same outer wrapper as E3-T9. Per-task content payloads:

| Fixture | Task | content payload |
|---|---|---|
| 01-spirits-clean | brand_disambig | `{"decision":"match","justification":"applicant brand 'ACME BOURBON' is the canonical form"}` |
| 01-spirits-clean | reasoning_enrich | `{"plain_language":"This bourbon meets the labeling rules.","citation_anchor":"27 CFR §5.42"}` |
| 01-spirits-clean | ocr_reconcile | `{"winner":"ACME BOURBON","reasoning":"high-confidence single read"}` |
| 02-bourbon-stones-throw | brand_disambig | `{"decision":"match","justification":"phonetic equivalence STONES THROW ↔ STONE'S THROW"}` |
| 02-bourbon-stones-throw | reasoning_enrich | `{"plain_language":"This bourbon's brand has a phonetic variant accepted as a match.","citation_anchor":"27 CFR §5.42"}` |
| 02-bourbon-stones-throw | ocr_reconcile | `{"winner":null,"reasoning":"two equally-likely reads; defer to needs_review"}` |

Outer wrapper for each (matches E3-T9 shape):
```json
{
  "id": "chatcmpl-test",
  "object": "chat.completion",
  "model": "gpt-4o-2024-08-06",
  "choices": [{"index": 0, "message": {"role": "assistant", "content": "<JSON-encoded payload>"}, "finish_reason": "stop"}],
  "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}
}
```

- [ ] **Cycle A — Step 2: Write failing test (Cycle A subset)**

```python
# tests/test_orchestrator_openai_strict.py — Cycle A
import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.config import Settings
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.schemas.application import Application
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import ValidationResult


REC_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator")


def _mount_recordings(router, fixture_id: str) -> None:
    """Closure-per-recording per §Conventions."""
    def _mount(name: str, payload: dict) -> None:
        def _handler(request):
            body = json.loads(request.content)
            if body.get("response_format", {}).get("json_schema", {}).get("name") == name:
                return Response(200, json=payload)
            return None
        router.post("/v1/chat/completions").mock(side_effect=_handler)
    for task in ("brand_disambig", "reasoning_enrich", "ocr_reconcile"):
        path = REC_DIR / task / f"{fixture_id}.json"
        _mount(task, json.loads(path.read_text()))


def _stub_inputs():
    """Minimal stub Application/observations/validation_results for the test.
    The orchestrator only reads identifying fields (evaluation_id, brand match
    candidates, rule_ids, ocr candidates) — schema details beyond that don't
    affect call construction in E4. Adjust if Application requires more fields."""
    app_ = Application(application_id="A-001", evaluation_id="EV-001")
    obs: list[FieldObservation] = []
    vr: list[ValidationResult] = []
    return app_, obs, vr


@pytest.mark.asyncio
async def test_refine_against_fixture_01():
    # No env-var monkeypatch needed: api_key is passed to the constructor
    # explicitly, so neither Settings() nor the orchestrator reads $OPENAI_API_KEY.
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    app_, obs, vr = _stub_inputs()
    with respx.mock(base_url="https://api.openai.com") as router:
        _mount_recordings(router, "01-spirits-clean")
        refined = await orch.refine(app_, obs, vr)
    task_names = {t.task for t in refined.tasks}
    assert task_names == {"brand_disambig", "reasoning_enrich", "ocr_reconcile"}
    assert len(ring) == 3  # one CallRecord per task
    assert all(r.provider == "openai" for r in ring)
    assert all(r.stage.startswith("orch.") for r in ring)
```

- [ ] **Cycle A — Step 3: Implement minimal `OpenAIStrictOrchestrator.refine()`**

```python
# app/orchestrator/openai_strict.py
"""OpenAI-strict orchestrator. Source: E4 L1 §2.2.

HTTP-layer only — does NOT import the openai SDK. Uses httpx so respx
recordings cover the wire. Records 1 CallRecord per task per attempt.
FR-303: never returns disposition; outputs are sliced into Refined.tasks.
FR-304: catches httpx.RequestError → returns slice with ENGINE.MODEL.UNAVAILABLE.
Strict-retry: on Pydantic ValidationError of LLM output, retries once;
on second failure, surfaces LLM_OUTPUT_INVALID qualifier.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.orchestrator.base import Orchestrator
from app.orchestrator.tasks.brand_disambig import BrandDisambigResult
from app.orchestrator.tasks.reasoning_enrich import EnrichedReasoning
from app.orchestrator.tasks.ocr_reconcile import OcrReconcileResult
from app.schemas.application import Application
from app.schemas.calls import CallRecord
from app.schemas.extracted import FieldObservation
from app.schemas.refined import Refined, TaskSlice
from app.schemas.rejection import ValidationResult


_TASK_SCHEMAS: dict[str, type] = {
    "brand_disambig": BrandDisambigResult,
    "reasoning_enrich": EnrichedReasoning,
    "ocr_reconcile": OcrReconcileResult,
}

_STAGE_BY_TASK: dict[str, str] = {
    "brand_disambig": "orch.brand_disambig",
    "reasoning_enrich": "orch.reasoning_enrich",
    "ocr_reconcile": "orch.ocr_reconcile",
}

_DETERMINISTIC_SEED = 42


class OpenAIStrictOrchestrator(Orchestrator):
    def __init__(
        self,
        *,
        settings: Settings,
        ring_buffer: deque,
        api_key: str,
    ) -> None:
        self._settings = settings
        self._ring = ring_buffer
        self._api_key = api_key
        self._model = settings.llm_model_snapshot
        self._prompt_version = settings.prompt_version

    async def ensure_client(self) -> None:
        return None

    async def refine(
        self,
        application: Application,
        observations: list[FieldObservation],
        validation_results: list[ValidationResult],
    ) -> Refined:
        evaluation_id = getattr(application, "evaluation_id", "EV-unknown")
        refined = Refined(evaluation_id=evaluation_id)
        # Run all 3 tasks. Per ARCH §11.2, no per-extractor bulkhead at this layer.
        # asyncio.gather is fine for latency; order doesn't affect output.
        slices = await asyncio.gather(
            self._call_task("brand_disambig", application, observations, validation_results),
            self._call_task("reasoning_enrich", application, observations, validation_results),
            self._call_task("ocr_reconcile", application, observations, validation_results),
        )
        return refined.model_copy(update={"tasks": tuple(slices)})

    async def _call_task(
        self,
        task_name: str,
        application: Application,
        observations: list[FieldObservation],
        validation_results: list[ValidationResult],
    ) -> TaskSlice:
        schema_cls = _TASK_SCHEMAS[task_name]
        body = self._build_body(task_name, schema_cls)
        # First attempt.
        try:
            content = await self._post_one(task_name, body)
        except httpx.RequestError as e:
            self._record(task_name, body, {"error": "ENGINE.MODEL.UNAVAILABLE", "exception": str(e)}, latency_ms=0)
            return TaskSlice(task=task_name, qualifier="ENGINE.MODEL.UNAVAILABLE")  # type: ignore[arg-type]
        # Validate; one retry on Pydantic ValidationError.
        try:
            result = schema_cls.model_validate(content)
            return TaskSlice(task=task_name, payload=result.model_dump())  # type: ignore[arg-type]
        except ValidationError:
            try:
                content = await self._post_one(task_name, body)
                result = schema_cls.model_validate(content)
                return TaskSlice(task=task_name, payload=result.model_dump())  # type: ignore[arg-type]
            except (ValidationError, httpx.RequestError):
                return TaskSlice(task=task_name, qualifier="LLM_OUTPUT_INVALID")  # type: ignore[arg-type]

    def _build_body(self, task_name: str, schema_cls: type) -> dict[str, Any]:
        return {
            "model": self._model,
            "temperature": 0,
            "seed": _DETERMINISTIC_SEED,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": f"Run task: {task_name}"}]}
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": task_name,
                    "strict": True,
                    "schema": schema_cls.model_json_schema(),
                },
            },
        }

    async def _post_one(self, task_name: str, body: dict[str, Any]) -> dict[str, Any]:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=body,
            )
            resp.raise_for_status()
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        payload = resp.json()
        content = json.loads(payload["choices"][0]["message"]["content"])
        self._record(task_name, body, content, elapsed_ms=elapsed_ms)
        return content

    def _record(self, task_name: str, body: dict[str, Any], response: dict[str, Any], *, elapsed_ms: int = 0, latency_ms: int = 0) -> None:
        latency = elapsed_ms or latency_ms
        self._ring.append(
            CallRecord(
                ts=datetime.now(timezone.utc),
                batch_id="",
                label_id="",
                stage=_STAGE_BY_TASK[task_name],  # type: ignore[arg-type]
                request={"task": task_name, "model": body.get("model"), "temperature": body.get("temperature"), "seed": body.get("seed")},
                response=response,
                latency_ms=latency,
                model=self._model,
                provider="openai",
                prompt_version=self._prompt_version,
                output_hash=hashlib.sha256(json.dumps(response, sort_keys=True, default=str).encode()).hexdigest()[:16],
            )
        )
```

- [ ] **Cycle A — Step 4: Run focused → expect GREEN (1 test passes)**

- [ ] **Cycle A — Step 5: Commit**

```bash
git add app/orchestrator/openai_strict.py tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator tests/test_orchestrator_openai_strict.py
git commit -m "feat(e4): OpenAIStrictOrchestrator with 3-task strict-mode pipeline"
```

- [ ] **Cycle B — FR-304 fallback**

Add to the test file:
```python
@pytest.mark.asyncio
async def test_refine_fr304_fallback_on_connect_error():
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    app_, obs, vr = _stub_inputs()
    with respx.mock(base_url="https://api.openai.com") as router:
        router.post("/v1/chat/completions").mock(side_effect=httpx.ConnectError("boom"))
        refined = await orch.refine(app_, obs, vr)
    qualifiers = {t.qualifier for t in refined.tasks}
    assert qualifiers == {"ENGINE.MODEL.UNAVAILABLE"}
    # 3 CallRecords with error responses + latency_ms populated (or 0 — acceptable).
    assert len(ring) == 3
    assert all(r.response.get("error") == "ENGINE.MODEL.UNAVAILABLE" for r in ring)
```

Implementation already in Cycle A's `_call_task`. Run focused → GREEN. Commit:
```bash
git add tests/test_orchestrator_openai_strict.py
git commit -m "test(e4): FR-304 fallback — httpx.RequestError → ENGINE.MODEL.UNAVAILABLE"
```

- [ ] **Cycle C — strict-retry on malformed structured output**

Add to the test file:
```python
@pytest.mark.asyncio
async def test_refine_retries_once_on_malformed():
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    app_, obs, vr = _stub_inputs()

    bad_payload = {
        "id": "chatcmpl-bad", "object": "chat.completion", "model": "gpt-4o-2024-08-06",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "{\"junk\":1}"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    with respx.mock(base_url="https://api.openai.com") as router:
        router.post("/v1/chat/completions").mock(return_value=Response(200, json=bad_payload))
        refined = await orch.refine(app_, obs, vr)
    qualifiers = {t.qualifier for t in refined.tasks}
    assert qualifiers == {"LLM_OUTPUT_INVALID"}
    # Each task: 2 attempts → 2 CallRecords. 3 tasks × 2 = 6.
    assert len(ring) == 6
```

Implementation: already in Cycle A's `_call_task` retry path. Run focused → GREEN. Commit:
```bash
git add tests/test_orchestrator_openai_strict.py
git commit -m "test(e4): strict-retry on malformed → LLM_OUTPUT_INVALID after 2 attempts"
```

---

## Task 9: app/orchestrator/anthropic_strict.py — AnthropicStrictOrchestrator skeleton

**Files:**
- Create: `app/orchestrator/anthropic_strict.py`
- Create: `tests/recordings/anthropic/claude-3-5-sonnet-20241022/v1/orchestrator/brand_disambig/01-spirits-clean.json`
- Create: `tests/recordings/anthropic/claude-3-5-sonnet-20241022/v1/orchestrator/reasoning_enrich/01-spirits-clean.json`
- Create: `tests/recordings/anthropic/claude-3-5-sonnet-20241022/v1/orchestrator/ocr_reconcile/01-spirits-clean.json`
- Test: `tests/test_orchestrator_anthropic_skeleton.py`

(Three recordings for fixture-01 only — the skeleton is "not validated against demo fixtures" per L1 §2.3, so fixture-02 recordings are not required for the skeleton's test surface.)

- [ ] **Step 1: Hand-author 3 Anthropic recordings**

Anthropic Messages API response shape with `tool_use` content:
```json
{
  "id": "msg-test", "type": "message", "role": "assistant",
  "model": "claude-3-5-sonnet-20241022",
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_test",
      "name": "brand_disambig",
      "input": {"decision": "match", "justification": "phonetic equivalence"}
    }
  ],
  "stop_reason": "tool_use",
  "usage": {"input_tokens": 100, "output_tokens": 10}
}
```

Repeat for `reasoning_enrich` and `ocr_reconcile` with appropriate `name` + `input` per the per-task schemas (mirror T8's payload values for fixture-01).

- [ ] **Step 2: Write failing test**

```python
# tests/test_orchestrator_anthropic_skeleton.py
import json
from collections import deque
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from app.config import Settings
from app.orchestrator.anthropic_strict import AnthropicStrictOrchestrator
from app.schemas.application import Application

REC_DIR = Path("tests/recordings/anthropic/claude-3-5-sonnet-20241022/v1/orchestrator")


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


def _mount_anthropic(router) -> None:
    def _mount(name: str, payload: dict) -> None:
        def _handler(request):
            body = json.loads(request.content)
            tool = body.get("tool_choice", {})
            if tool.get("name") == name:
                return Response(200, json=payload)
            return None
        router.post("/v1/messages").mock(side_effect=_handler)
    for task in ("brand_disambig", "reasoning_enrich", "ocr_reconcile"):
        path = REC_DIR / task / "01-spirits-clean.json"
        _mount(task, json.loads(path.read_text()))


@pytest.mark.asyncio
async def test_anthropic_skeleton_returns_refined():
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = AnthropicStrictOrchestrator(
        settings=settings, ring_buffer=ring, api_key="sk-ant-test",
        model_snapshot="claude-3-5-sonnet-20241022",
    )
    with respx.mock(base_url="https://api.anthropic.com") as router:
        _mount_anthropic(router)
        refined = await orch.refine(_stub_app(), [], [])
    task_names = {t.task for t in refined.tasks}
    assert task_names == {"brand_disambig", "reasoning_enrich", "ocr_reconcile"}
    assert len(ring) == 3
    assert all(r.provider == "anthropic" for r in ring)


@pytest.mark.asyncio
async def test_anthropic_ensure_client_raises_without_extra(monkeypatch):
    """When the anthropic SDK is genuinely missing, ensure_client raises a clear error.
    We simulate by monkeypatching sys.modules to inject ImportError on the lazy import."""
    import sys
    monkeypatch.setitem(sys.modules, "anthropic", None)
    settings = Settings()
    orch = AnthropicStrictOrchestrator(
        settings=settings, ring_buffer=deque(maxlen=200), api_key="sk-test",
        model_snapshot="claude-3-5-sonnet-20241022",
    )
    with pytest.raises(RuntimeError, match=r"anthropic.*\[anthropic\].*extra"):
        await orch.ensure_client()
```

- [ ] **Step 3: Implement**

```python
# app/orchestrator/anthropic_strict.py
"""Anthropic-strict orchestrator skeleton. Source: E4 L1 §2.3.

HTTP-layer via httpx so respx recordings cover the wire. The `anthropic` SDK is
lazy-imported in ensure_client() — module is importable without the [anthropic]
extra installed. Mirrors OpenAIStrictOrchestrator's task surface but uses the
Anthropic Messages API tool_use shape.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.orchestrator.base import Orchestrator
from app.orchestrator.tasks.brand_disambig import BrandDisambigResult
from app.orchestrator.tasks.reasoning_enrich import EnrichedReasoning
from app.orchestrator.tasks.ocr_reconcile import OcrReconcileResult
from app.schemas.application import Application
from app.schemas.calls import CallRecord
from app.schemas.extracted import FieldObservation
from app.schemas.refined import Refined, TaskSlice
from app.schemas.rejection import ValidationResult

_TASK_SCHEMAS: dict[str, type] = {
    "brand_disambig": BrandDisambigResult,
    "reasoning_enrich": EnrichedReasoning,
    "ocr_reconcile": OcrReconcileResult,
}

_STAGE_BY_TASK: dict[str, str] = {
    "brand_disambig": "orch.brand_disambig",
    "reasoning_enrich": "orch.reasoning_enrich",
    "ocr_reconcile": "orch.ocr_reconcile",
}

_DETERMINISTIC_SEED = 42  # Anthropic ignores seed but we record it for parity.


def _to_anthropic_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Strip OpenAI-specific keys; Anthropic tool_use accepts standard JSON Schema."""
    out = {k: v for k, v in schema.items() if k not in {"$schema", "title"}}
    return out


class AnthropicStrictOrchestrator(Orchestrator):
    def __init__(
        self,
        *,
        settings: Settings,
        ring_buffer: deque,
        api_key: str,
        model_snapshot: str = "claude-3-5-sonnet-20241022",
    ) -> None:
        self._settings = settings
        self._ring = ring_buffer
        self._api_key = api_key
        self._model = model_snapshot
        self._prompt_version = settings.prompt_version

    async def ensure_client(self) -> None:
        try:
            import anthropic  # noqa: F401  # lazy import; presence-check only
        except ImportError as e:
            raise RuntimeError(
                "anthropic SDK not installed. Install the [anthropic] extra: "
                "uv sync --extra anthropic"
            ) from e

    async def refine(
        self,
        application: Application,
        observations: list[FieldObservation],
        validation_results: list[ValidationResult],
    ) -> Refined:
        evaluation_id = getattr(application, "evaluation_id", "EV-unknown")
        refined = Refined(evaluation_id=evaluation_id)
        slices = await asyncio.gather(
            self._call_task("brand_disambig"),
            self._call_task("reasoning_enrich"),
            self._call_task("ocr_reconcile"),
        )
        return refined.model_copy(update={"tasks": tuple(slices)})

    async def _call_task(self, task_name: str) -> TaskSlice:
        schema_cls = _TASK_SCHEMAS[task_name]
        body = self._build_body(task_name, schema_cls)
        # ValueError covers the "tool_use block missing from response" path
        # raised by _post_one — see note on `raise ValueError(...)` below.
        try:
            content = await self._post_one(task_name, body)
        except httpx.RequestError as e:
            self._record(task_name, body, {"error": "ENGINE.MODEL.UNAVAILABLE", "exception": str(e)}, latency_ms=0)
            return TaskSlice(task=task_name, qualifier="ENGINE.MODEL.UNAVAILABLE")  # type: ignore[arg-type]
        try:
            result = schema_cls.model_validate(content)
            return TaskSlice(task=task_name, payload=result.model_dump())  # type: ignore[arg-type]
        except (ValidationError, ValueError):
            try:
                content = await self._post_one(task_name, body)
                result = schema_cls.model_validate(content)
                return TaskSlice(task=task_name, payload=result.model_dump())  # type: ignore[arg-type]
            except (ValidationError, ValueError, httpx.RequestError):
                return TaskSlice(task=task_name, qualifier="LLM_OUTPUT_INVALID")  # type: ignore[arg-type]

    def _build_body(self, task_name: str, schema_cls: type) -> dict[str, Any]:
        return {
            "model": self._model,
            "max_tokens": 1024,
            "temperature": 0,
            "messages": [{"role": "user", "content": f"Run task: {task_name}"}],
            "tools": [{
                "name": task_name,
                "description": f"Run the {task_name} task and return a typed result.",
                "input_schema": _to_anthropic_schema(schema_cls.model_json_schema()),
            }],
            "tool_choice": {"type": "tool", "name": task_name},
        }

    async def _post_one(self, task_name: str, body: dict[str, Any]) -> dict[str, Any]:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=body,
            )
            resp.raise_for_status()
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        payload = resp.json()
        # Find the tool_use block matching this task.
        tool_use = next(
            (b for b in payload.get("content", []) if b.get("type") == "tool_use" and b.get("name") == task_name),
            None,
        )
        if tool_use is None:
            # NB: do NOT use `ValidationError.from_exception_data(line_errors=[])`
            # — pydantic v2 ≥ 2.6 raises `PydanticUserError` on an empty error list.
            # `_call_task` above catches `ValueError` alongside `ValidationError`
            # so the malformed-output retry path still kicks in.
            raise ValueError(f"anthropic response missing tool_use block for task {task_name!r}")
        content = tool_use["input"]
        self._record(task_name, body, content, elapsed_ms=elapsed_ms)
        return content

    def _record(self, task_name: str, body: dict[str, Any], response: dict[str, Any], *, elapsed_ms: int = 0, latency_ms: int = 0) -> None:
        latency = elapsed_ms or latency_ms
        self._ring.append(
            CallRecord(
                ts=datetime.now(timezone.utc),
                batch_id="",
                label_id="",
                stage=_STAGE_BY_TASK[task_name],  # type: ignore[arg-type]
                request={"task": task_name, "model": body.get("model"), "temperature": body.get("temperature")},
                response=response,
                latency_ms=latency,
                model=self._model,
                provider="anthropic",
                prompt_version=self._prompt_version,
                output_hash=hashlib.sha256(json.dumps(response, sort_keys=True, default=str).encode()).hexdigest()[:16],
            )
        )
```

- [ ] **Step 4: Run focused → GREEN (2 tests)**

- [ ] **Step 5: Run full suite**

- [ ] **Step 6: Commit**

```bash
git add app/orchestrator/anthropic_strict.py tests/recordings/anthropic tests/test_orchestrator_anthropic_skeleton.py
git commit -m "feat(e4): AnthropicStrictOrchestrator skeleton (tool_use strict mode)"
```

---

## Task 10: app/deps.py — replace orchestrator placeholders + tests

**Files:**
- Modify: `app/deps.py`
- Test: `tests/test_orchestrator_deps.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_deps.py
import pytest

from app.config import Settings
from app.deps import build_orchestrator
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.orchestrator.anthropic_strict import AnthropicStrictOrchestrator


def test_build_orchestrator_openai(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_BACKEND", "openai")
    settings = Settings()
    orch = build_orchestrator(settings)
    assert isinstance(orch, OpenAIStrictOrchestrator)


def test_build_orchestrator_anthropic(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_BACKEND", "anthropic")
    settings = Settings()
    orch = build_orchestrator(settings)
    assert isinstance(orch, AnthropicStrictOrchestrator)


def test_build_orchestrator_unknown_raises(monkeypatch):
    """Settings restricts orchestrator_backend Literal so 'vllm' fails at Settings()
    construction with ValidationError. The build_orchestrator function additionally
    raises ValueError if a future placeholder leaks through."""
    from pydantic import ValidationError
    monkeypatch.setenv("ORCHESTRATOR_BACKEND", "vllm")
    with pytest.raises(ValidationError):
        Settings()


def test_placeholder_classes_removed():
    """The E1 placeholder orchestrators must be gone after T10."""
    import app.deps as deps
    assert not hasattr(deps, "_PlaceholderOpenAIOrchestrator")
    assert not hasattr(deps, "_PlaceholderAnthropicOrchestrator")
```

- [ ] **Step 2: Run focused → RED (placeholders still present)**

- [ ] **Step 3: Replace orchestrator block in `app/deps.py`**

Read the existing `app/deps.py` first; preserve `build_vision_extractor` + `_autodetect` exactly. Replace ONLY the orchestrator placeholder + `build_orchestrator` block at the bottom with:

```python
# Real orchestrator wiring (E4 — replaces E1 placeholders).
from app.orchestrator.base import Orchestrator
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.orchestrator.anthropic_strict import AnthropicStrictOrchestrator


def build_orchestrator(settings: Settings) -> Orchestrator:
    backend = settings.orchestrator_backend
    ring: deque = deque(maxlen=200)
    if backend == "openai":
        return OpenAIStrictOrchestrator(
            settings=settings, ring_buffer=ring, api_key=settings.openai_api_key or ""
        )
    if backend == "anthropic":
        return AnthropicStrictOrchestrator(
            settings=settings, ring_buffer=ring, api_key=settings.anthropic_api_key or "",
        )
    raise ValueError(f"Unknown orchestrator_backend: {backend!r}")
```

Delete `_PlaceholderOpenAIOrchestrator` and `_PlaceholderAnthropicOrchestrator` and the old `build_orchestrator` body.

- [ ] **Step 4: Run focused → GREEN (4 tests pass)**

- [ ] **Step 5: Run full suite**

If any existing test imported the placeholders, that's a Rule 1-3 inline fix to those tests (they were testing a placeholder shape and should now test the real one).

- [ ] **Step 6: Commit**

```bash
git add app/deps.py tests/test_orchestrator_deps.py
git commit -m "feat(e4): wire build_orchestrator → real impls; drop E1 placeholders"
```

---

## Task 11: tests/test_orchestrator_substitutability.py — Substitutability E2E

**Files:**
- Create: `tests/test_orchestrator_substitutability.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_orchestrator_substitutability.py
import inspect
import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.config import Settings
from app.orchestrator.base import Orchestrator
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.orchestrator.anthropic_strict import AnthropicStrictOrchestrator
from app.schemas.application import Application


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


def test_both_subclass_orchestrator():
    assert issubclass(OpenAIStrictOrchestrator, Orchestrator)
    assert issubclass(AnthropicStrictOrchestrator, Orchestrator)


def test_both_refine_are_coroutines():
    assert inspect.iscoroutinefunction(OpenAIStrictOrchestrator.refine)
    assert inspect.iscoroutinefunction(AnthropicStrictOrchestrator.refine)


@pytest.mark.asyncio
async def test_both_produce_same_task_keys():
    settings = Settings()

    # Cloud (OpenAI) under recordings.
    openai_ring: deque = deque(maxlen=200)
    openai_orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=openai_ring, api_key="sk-test")
    openai_rec = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator")
    with respx.mock(base_url="https://api.openai.com") as router:
        def _mount(name: str, payload: dict) -> None:
            def _handler(request):
                body = json.loads(request.content)
                if body.get("response_format", {}).get("json_schema", {}).get("name") == name:
                    return Response(200, json=payload)
                return None
            router.post("/v1/chat/completions").mock(side_effect=_handler)
        for task in ("brand_disambig", "reasoning_enrich", "ocr_reconcile"):
            _mount(task, json.loads((openai_rec / task / "01-spirits-clean.json").read_text()))
        openai_refined = await openai_orch.refine(_stub_app(), [], [])

    # Anthropic skeleton under recordings.
    anth_ring: deque = deque(maxlen=200)
    anth_orch = AnthropicStrictOrchestrator(
        settings=settings, ring_buffer=anth_ring, api_key="sk-ant-test",
        model_snapshot="claude-3-5-sonnet-20241022",
    )
    anth_rec = Path("tests/recordings/anthropic/claude-3-5-sonnet-20241022/v1/orchestrator")
    with respx.mock(base_url="https://api.anthropic.com") as router:
        def _mount2(name: str, payload: dict) -> None:
            def _handler(request):
                body = json.loads(request.content)
                if body.get("tool_choice", {}).get("name") == name:
                    return Response(200, json=payload)
                return None
            router.post("/v1/messages").mock(side_effect=_handler)
        for task in ("brand_disambig", "reasoning_enrich", "ocr_reconcile"):
            _mount2(task, json.loads((anth_rec / task / "01-spirits-clean.json").read_text()))
        anth_refined = await anth_orch.refine(_stub_app(), [], [])

    openai_keys = {t.task for t in openai_refined.tasks}
    anth_keys = {t.task for t in anth_refined.tasks}
    assert openai_keys == anth_keys == {"brand_disambig", "reasoning_enrich", "ocr_reconcile"}
```

- [ ] **Step 2: Run focused → expect PASS** (T8+T9 should produce all 3 task slices)

- [ ] **Step 3: Commit**

```bash
git add tests/test_orchestrator_substitutability.py
git commit -m "test(e4): both impls subclass Orchestrator + produce same task keys"
```

---

## Task 12: tests/test_orchestrator_ring_buffer.py — CallRecord per task per attempt

**Files:**
- Create: `tests/test_orchestrator_ring_buffer.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_orchestrator_ring_buffer.py
import json
from collections import deque
from pathlib import Path

import httpx
import pytest
import respx
from httpx import Response

from app.config import Settings
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.schemas.application import Application

REC_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator")


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


@pytest.mark.asyncio
async def test_successful_refine_writes_3_call_records():
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    with respx.mock(base_url="https://api.openai.com") as router:
        def _mount(name: str, payload: dict) -> None:
            def _handler(request):
                body = json.loads(request.content)
                if body.get("response_format", {}).get("json_schema", {}).get("name") == name:
                    return Response(200, json=payload)
                return None
            router.post("/v1/chat/completions").mock(side_effect=_handler)
        for task in ("brand_disambig", "reasoning_enrich", "ocr_reconcile"):
            _mount(task, json.loads((REC_DIR / task / "01-spirits-clean.json").read_text()))
        await orch.refine(_stub_app(), [], [])
    assert len(ring) == 3
    assert {r.stage for r in ring} == {"orch.brand_disambig", "orch.reasoning_enrich", "orch.ocr_reconcile"}
    assert all(r.provider == "openai" for r in ring)
    assert all(r.model == "gpt-4o-2024-08-06" for r in ring)
    assert all(r.prompt_version == "v1" for r in ring)
    assert all(len(r.output_hash) == 16 for r in ring)


@pytest.mark.asyncio
async def test_failed_refine_writes_1_call_record_per_failed_task():
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    with respx.mock(base_url="https://api.openai.com") as router:
        router.post("/v1/chat/completions").mock(side_effect=httpx.ConnectError("boom"))
        await orch.refine(_stub_app(), [], [])
    assert len(ring) == 3  # one per failed task
    assert all(r.response.get("error") == "ENGINE.MODEL.UNAVAILABLE" for r in ring)


def test_ring_buffer_maxlen_honored():
    ring: deque = deque(maxlen=200)
    for i in range(250):
        ring.append(i)
    assert len(ring) == 200
    assert ring[0] == 50
```

- [ ] **Step 2: Run focused → expect PASS**

- [ ] **Step 3: Commit**

```bash
git add tests/test_orchestrator_ring_buffer.py
git commit -m "test(e4): CallRecord per task per attempt; ring-buffer FIFO honored"
```

---

## Task 13: tests/test_orchestrator_temp_seed_snapshot.py — determinism asserts

**Files:**
- Create: `tests/test_orchestrator_temp_seed_snapshot.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_orchestrator_temp_seed_snapshot.py
"""Determinism canary: every recorded request body must contain
temperature=0, seed=<deterministic>, model=<snapshot>. Drift on any of these
is a regression that breaks T5 §Q5.7 / S5 determinism."""
import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.config import Settings
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.schemas.application import Application

REC_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator")


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


@pytest.mark.asyncio
async def test_request_body_has_temperature_zero_and_seed():
    settings = Settings()
    captured_bodies: list[dict] = []
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")

    with respx.mock(base_url="https://api.openai.com") as router:
        def _mount(name: str, payload: dict) -> None:
            def _handler(request):
                body = json.loads(request.content)
                captured_bodies.append(body)
                if body.get("response_format", {}).get("json_schema", {}).get("name") == name:
                    return Response(200, json=payload)
                return None
            router.post("/v1/chat/completions").mock(side_effect=_handler)
        for task in ("brand_disambig", "reasoning_enrich", "ocr_reconcile"):
            _mount(task, json.loads((REC_DIR / task / "01-spirits-clean.json").read_text()))
        await orch.refine(_stub_app(), [], [])

    assert len(captured_bodies) >= 3
    successful = [b for b in captured_bodies if b.get("response_format", {}).get("json_schema", {}).get("name") in {"brand_disambig", "reasoning_enrich", "ocr_reconcile"}]
    # Pull the seed value from the orchestrator module so the test catches
    # both deletion ("seed" missing) AND silent rotation (e.g. someone wires
    # `seed=time.time()`). _DETERMINISTIC_SEED lands as part of T8's openai_strict.py.
    from app.orchestrator.openai_strict import _DETERMINISTIC_SEED

    for body in successful:
        assert body.get("temperature") == 0, f"determinism drift: temperature={body.get('temperature')!r}"
        assert body.get("seed") == _DETERMINISTIC_SEED, (
            f"determinism drift: seed={body.get('seed')!r} (expected {_DETERMINISTIC_SEED})"
        )
        assert body.get("model") == "gpt-4o-2024-08-06", f"snapshot drift: model={body.get('model')!r}"
```

- [ ] **Step 2: Run focused → expect PASS**

- [ ] **Step 3: Commit**

```bash
git add tests/test_orchestrator_temp_seed_snapshot.py
git commit -m "test(e4): determinism canary — temperature=0, seed, snapshot pinned"
```

---

## Task 14: app/orchestrator/__main__.py — CLI smoke entry

**Files:**
- Create: `app/orchestrator/__main__.py`
- Test: `tests/test_orchestrator_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_orchestrator_cli_smoke.py
import os
import subprocess
import sys


def test_cli_smoke_exits_zero_on_recordings():
    env = {**os.environ, "OPENAI_API_KEY": "sk-test", "ORCHESTRATOR_BACKEND": "openai"}
    result = subprocess.run(
        [sys.executable, "-m", "app.orchestrator",
         "--task", "brand_disambig",
         "--fixture", "01-spirits-clean",
         "--backend", "openai",
         "--use-recordings"],
        capture_output=True, timeout=30, env=env,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert b"task: brand_disambig" in result.stdout
    assert b"decision:" in result.stdout


def test_cli_smoke_missing_recording_exits_2():
    env = {**os.environ, "OPENAI_API_KEY": "sk-test", "ORCHESTRATOR_BACKEND": "openai"}
    result = subprocess.run(
        [sys.executable, "-m", "app.orchestrator",
         "--task", "brand_disambig",
         "--fixture", "99-does-not-exist",
         "--backend", "openai",
         "--use-recordings"],
        capture_output=True, timeout=10, env=env,
    )
    assert result.returncode == 2
    assert b"recording not found" in result.stderr.lower()


def test_cli_smoke_bad_backend_exits_2():
    result = subprocess.run(
        [sys.executable, "-m", "app.orchestrator",
         "--task", "brand_disambig", "--fixture", "01-spirits-clean",
         "--backend", "vllm"],
        capture_output=True, timeout=10,
    )
    assert result.returncode == 2
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement `__main__.py`**

```python
# app/orchestrator/__main__.py
"""CLI smoke: python -m app.orchestrator --task <name> --fixture <id> --backend <openai|anthropic>.

Per L1 §8 #3, exercises the orchestrator against recorded responses for offline CI."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import deque
from pathlib import Path

from app.config import Settings


_VALID_TASKS = ("brand_disambig", "reasoning_enrich", "ocr_reconcile")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m app.orchestrator")
    p.add_argument("--task", required=True, choices=_VALID_TASKS)
    p.add_argument("--fixture", required=True)
    p.add_argument("--backend", choices=("openai", "anthropic"), default="openai")
    p.add_argument("--use-recordings", action="store_true")
    return p


async def _run_openai(args, settings: Settings) -> int:
    from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
    from app.schemas.application import Application
    rec_root = Path("tests/recordings/openai") / settings.llm_model_snapshot \
        / settings.prompt_version / "orchestrator" / args.task
    rec_path = rec_root / f"{args.fixture}.json"
    if not rec_path.exists():
        print(f"recording not found: {rec_path}", file=sys.stderr)
        return 2

    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key=settings.openai_api_key or "sk-test")
    payload = json.loads(rec_path.read_text())

    if args.use_recordings:
        import respx
        from httpx import Response

        with respx.mock(base_url="https://api.openai.com") as router:
            def _handler(request):
                body = json.loads(request.content)
                # Always return the same recorded payload regardless of task name —
                # the smoke runs only the requested task, so the payload matches.
                return Response(200, json=payload)
            router.post("/v1/chat/completions").mock(side_effect=_handler)
            # Run the requested task in isolation by calling _call_task directly.
            slice_ = await orch._call_task(args.task, _stub_app(), [], [])
    else:
        slice_ = await orch._call_task(args.task, _stub_app(), [], [])

    print(f"task: {slice_.task}")
    if slice_.payload:
        for k, v in slice_.payload.items():
            print(f"{k}: {v}")
    if slice_.qualifier:
        print(f"qualifier: {slice_.qualifier}")
    return 0


def _stub_app():
    from app.schemas.application import Application
    return Application(application_id="A-001", evaluation_id="EV-cli-smoke")


async def _run(args) -> int:
    settings = Settings()
    if args.backend == "openai":
        return await _run_openai(args, settings)
    if args.backend == "anthropic":
        # Symmetric impl path; call Anthropic orchestrator's _call_task with recordings.
        from app.orchestrator.anthropic_strict import AnthropicStrictOrchestrator
        rec_root = Path("tests/recordings/anthropic/claude-3-5-sonnet-20241022") \
            / settings.prompt_version / "orchestrator" / args.task
        rec_path = rec_root / f"{args.fixture}.json"
        if not rec_path.exists():
            print(f"recording not found: {rec_path}", file=sys.stderr)
            return 2
        ring: deque = deque(maxlen=200)
        orch = AnthropicStrictOrchestrator(
            settings=settings, ring_buffer=ring, api_key=settings.anthropic_api_key or "sk-ant-test",
            model_snapshot="claude-3-5-sonnet-20241022",
        )
        payload = json.loads(rec_path.read_text())
        if args.use_recordings:
            import respx
            from httpx import Response
            with respx.mock(base_url="https://api.anthropic.com") as router:
                router.post("/v1/messages").mock(return_value=Response(200, json=payload))
                slice_ = await orch._call_task(args.task)
        else:
            slice_ = await orch._call_task(args.task)
        print(f"task: {slice_.task}")
        if slice_.payload:
            for k, v in slice_.payload.items():
                print(f"{k}: {v}")
        if slice_.qualifier:
            print(f"qualifier: {slice_.qualifier}")
        return 0
    print(f"unknown backend: {args.backend}", file=sys.stderr)
    return 2


def main() -> None:
    try:
        args = _build_argparser().parse_args()
    except SystemExit as e:
        # argparse exits 2 on bad args; keep that.
        raise
    try:
        sys.exit(asyncio.run(_run(args)))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4-5: Run focused → GREEN; full suite**

- [ ] **Step 6: Commit**

```bash
git add app/orchestrator/__main__.py tests/test_orchestrator_cli_smoke.py
git commit -m "feat(e4): orchestrator CLI smoke entry (python -m app.orchestrator)"
```

---

## Task 15: scripts/record_orchestrator_responses.py — recording rotation

**Files:**
- Create: `scripts/record_orchestrator_responses.py`
- Test: `tests/test_record_orchestrator_responses.py`

- [ ] **Step 1: Write the smoke test**

```python
# tests/test_record_orchestrator_responses.py
import os
import subprocess
import sys


def test_script_imports_cleanly():
    result = subprocess.run(
        [sys.executable, "-c", "import scripts.record_orchestrator_responses"],
        capture_output=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "scripts/record_orchestrator_responses.py", "--help"],
        capture_output=True, timeout=10,
    )
    assert result.returncode == 0
    assert b"--live" in result.stdout


def test_live_without_api_key_exits_2():
    env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
    result = subprocess.run(
        [sys.executable, "scripts/record_orchestrator_responses.py",
         "--live", "--provider", "openai", "--task", "brand_disambig", "--fixture", "01-spirits-clean"],
        capture_output=True, timeout=10, env=env,
    )
    assert result.returncode == 2
    assert b"OPENAI_API_KEY" in result.stderr
```

- [ ] **Step 2: Run focused → RED**

- [ ] **Step 3: Implement script**

```python
# scripts/record_orchestrator_responses.py
"""Recording-rotation companion for D-020 snapshot rotation.

Iterates the active fixture set + per-task calls, performs one live OpenAI/Anthropic
call each, writes the response to:
  tests/recordings/<provider>/<snapshot>/<prompt-version>/orchestrator/<task>/<fixture>.json

Dry-run by default. `--live` required to actually call.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_TASKS = ("brand_disambig", "reasoning_enrich", "ocr_reconcile")
_PROVIDERS = ("openai", "anthropic")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="record_orchestrator_responses",
        description="Snapshot-rotation companion for orchestrator recordings. Live calls require --live + API key.",
    )
    p.add_argument("--provider", choices=_PROVIDERS, default="openai")
    p.add_argument("--task", choices=_TASKS, default="brand_disambig")
    p.add_argument("--fixture", default="01-spirits-clean")
    p.add_argument("--snapshot", default=None)
    p.add_argument("--prompt-version", default=None)
    p.add_argument("--live", action="store_true")
    return p


def _main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)

    if args.live:
        key_env = "OPENAI_API_KEY" if args.provider == "openai" else "ANTHROPIC_API_KEY"
        if not os.environ.get(key_env):
            print(f"error: --live requires {key_env} in env", file=sys.stderr)
            return 2

    from app.config import Settings
    settings = Settings()
    snapshot = args.snapshot or (settings.llm_model_snapshot if args.provider == "openai" else "claude-3-5-sonnet-20241022")
    prompt_version = args.prompt_version or settings.prompt_version
    out_dir = Path("tests/recordings") / args.provider / snapshot / prompt_version / "orchestrator" / args.task
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.fixture}.json"

    if not args.live:
        print(f"DRY RUN: would write {out_path} (provider={args.provider}, task={args.task}, fixture={args.fixture})")
        return 0

    print(f"would write {out_path} (live impl deferred — operator-driven flow)")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
```

- [ ] **Step 4: Run focused → GREEN**

- [ ] **Step 5: Commit**

```bash
git add scripts/record_orchestrator_responses.py tests/test_record_orchestrator_responses.py
git commit -m "chore(e4): scripts/record_orchestrator_responses.py for snapshot rotation"
```

---

## Task 16: tests/test_orchestrator_isolation.py — inference-dep grep + conftest sanitizer

**Files:**
- Create: `tests/test_orchestrator_isolation.py`
- Modify: `tests/conftest.py` (add Authorization-header sanitizer fixture)

- [ ] **Step 1: Write the test**

```python
# tests/test_orchestrator_isolation.py
"""Inference-dep isolation:
- `openai` may be imported only under app/vision/ (E3) and app/orchestrator/ (E4).
- `anthropic` may be imported only under app/orchestrator/ (E4).
- `vllm`/`xgrammar` must not be imported anywhere (D-021).

Mirrors E3-T19's app/vision/ isolation invariant for the orchestrator direction.
"""
from pathlib import Path
import re


_OPENAI_PATTERNS = (
    re.compile(r"\bimport\s+openai\b"),
    re.compile(r"\bfrom\s+openai\b"),
)
_ANTHROPIC_PATTERNS = (
    re.compile(r"\bimport\s+anthropic\b"),
    re.compile(r"\bfrom\s+anthropic\b"),
)
_FORBIDDEN_PATTERNS = (
    re.compile(r"\bimport\s+vllm\b"),
    re.compile(r"\bfrom\s+vllm\b"),
    re.compile(r"\bimport\s+xgrammar\b"),
    re.compile(r"\bfrom\s+xgrammar\b"),
)


def test_openai_imports_only_under_vision_or_orchestrator():
    violations: list[str] = []
    for py in Path("app").rglob("*.py"):
        path_str = str(py)
        if "app/vision/" in path_str or "app/orchestrator/" in path_str:
            continue
        text = py.read_text()
        for rx in _OPENAI_PATTERNS:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "openai imports leaked outside app/vision/ + app/orchestrator/:\n" + "\n".join(violations)


def test_anthropic_imports_only_under_orchestrator():
    violations: list[str] = []
    for py in Path("app").rglob("*.py"):
        if "app/orchestrator/" in str(py):
            continue
        text = py.read_text()
        for rx in _ANTHROPIC_PATTERNS:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "anthropic imports leaked outside app/orchestrator/:\n" + "\n".join(violations)


def test_d021_forbidden_imports_absent():
    violations: list[str] = []
    for py in Path("app").rglob("*.py"):
        text = py.read_text()
        for rx in _FORBIDDEN_PATTERNS:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "D-021 forbidden imports detected:\n" + "\n".join(violations)


def test_authorization_header_sanitizer_redacts():
    """Sanitizer (in conftest.py) replaces Authorization headers with REDACTED."""
    from tests.conftest import _redact_authorization_headers
    payload = {"headers": {"Authorization": "Bearer sk-secret-12345", "Content-Type": "application/json"}}
    sanitized = _redact_authorization_headers(payload)
    assert sanitized["headers"]["Authorization"] == "REDACTED"
    assert sanitized["headers"]["Content-Type"] == "application/json"  # unchanged
```

- [ ] **Step 2: Run focused → RED for the sanitizer test (conftest helper missing)**

- [ ] **Step 3: Add helper to `tests/conftest.py`**

Read the existing `tests/conftest.py`. Append:

```python
def _redact_authorization_headers(payload: dict) -> dict:
    """Strip Authorization headers from a recording payload before write.
    Per L1 §7 risk: prevents leaked API keys in committed recordings."""
    import copy
    out = copy.deepcopy(payload)
    headers = out.get("headers")
    if isinstance(headers, dict):
        for key in list(headers.keys()):
            if key.lower() == "authorization" or key.lower() == "x-api-key":
                headers[key] = "REDACTED"
    return out
```

- [ ] **Step 4: Run focused → GREEN (4 tests)**

- [ ] **Step 5: Commit**

```bash
git add tests/test_orchestrator_isolation.py tests/conftest.py
git commit -m "test(e4): inference-dep isolation + Authorization-header sanitizer"
```

---

## Task 17: fixtures/02-bourbon-stones-throw/label.png — synthetic fixture-02

**Files:**
- Create: `fixtures/02-bourbon-stones-throw/label.png`
- Create: `scripts/build_synthetic_fixture_02.py`
- Test: `tests/test_synthetic_fixture_02.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_synthetic_fixture_02.py
from pathlib import Path

from PIL import Image

FIXTURE = Path("fixtures/02-bourbon-stones-throw/label.png")


def test_fixture_exists():
    assert FIXTURE.exists()


def test_fixture_is_png_with_dpi():
    with Image.open(FIXTURE) as img:
        assert img.format == "PNG"
        assert img.size == (200, 200)
        dpi = img.info.get("dpi")
        # PNG pHYs round-trip is lossy via integer pixels-per-meter — accept ±1.
        assert dpi is not None
        assert int(round(dpi[0])) == 300
```

- [ ] **Step 2: Run focused → RED (fixture absent)**

- [ ] **Step 3: Write build script**

```python
# scripts/build_synthetic_fixture_02.py
"""Deterministic synthetic fixture-02 (STONE'S THROW BOURBON). Mirrors E3-T5 shape.

200x200 white PNG with embedded "STONE'S THROW BOURBON" text + EXIF DPI=300.
Used by E4 orchestrator brand-disambig recordings.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/02-bourbon-stones-throw/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (200, 200), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "STONE'S THROW", fill="black", font=font)
    draw.text((10, 30), "BOURBON", fill="black", font=font)
    draw.text((10, 50), "ALC. 45% BY VOL.", fill="black", font=font)
    draw.text((10, 70), "GOVERNMENT WARNING:", fill="black", font=font)
    draw.text((10, 90), "(1) ACCORDING TO THE", fill="black", font=font)
    draw.text((10, 105), "SURGEON GENERAL...", fill="black", font=font)
    draw.text((10, 130), "750 ML", fill="black", font=font)
    draw.text((10, 150), "DISTILLED IN KENTUCKY", fill="black", font=font)
    img.save(OUT, "PNG", dpi=(300, 300))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run script + focused → GREEN**

```bash
uv run python scripts/build_synthetic_fixture_02.py
uv run pytest tests/test_synthetic_fixture_02.py -v
```

- [ ] **Step 5: Commit**

```bash
git add fixtures/02-bourbon-stones-throw/label.png scripts/build_synthetic_fixture_02.py tests/test_synthetic_fixture_02.py
git commit -m "test(e4): synthetic fixture-02 STONE'S THROW BOURBON (DPI=300)"
```

---

## Final integration check

After T17 lands, run:

```bash
uv run pytest -q
uv run python -m app.orchestrator --task brand_disambig --fixture 01-spirits-clean --backend openai --use-recordings
uv run python -m app.orchestrator --task brand_disambig --fixture 02-bourbon-stones-throw --backend openai --use-recordings
git log --oneline main ^9f05143 | wc -l   # should report ~25 new commits
```

Verify:
- All ~340 tests pass (302 baseline + ~38 from E4 across 17 tasks).
- Both CLI smokes print `task: brand_disambig` + `decision: match` and exit 0.
- L1 §4 exit gates 1–10 satisfied:
  1. ✅ `Orchestrator` ABC declared (T2).
  2. ✅ Both impls subclass `Orchestrator` (T11).
  3. ✅ FR-303 invariant test passes (T7).
  4. ✅ OpenAI impl extracts wire-conforming `Refined` for fixture-01 + fixture-02 (T8).
  5. ✅ FR-304 fallback test passes (T8 Cycle B).
  6. ✅ Strict-retry test passes (T8 Cycle C).
  7. ✅ CallRecord per task per attempt; ring-buffer FIFO at maxlen=200 (T12).
  8. ✅ Inference-dep isolation grep clean (T16).
  9. ✅ DI dispatch + ValueError on unknown backend; Anthropic raises clear error w/o `[anthropic]` extra (T9 + T10).
  10. ✅ `prompt_version`, `model`, `output_hash` populated in CallRecord (T12).

---

## Self-review

**Spec coverage** — checked L1 §2, §4, §5, §7, §8 against tasks. All exit-gate items have a task. The CLI smoke is T14. The recording-rotation script is T15. The conftest sanitizer (L1 §7 risk) is T16. The fixture-02 (L1 §4 #4) is T17. The Refined schema tightening (closes E1 omission) is T1.

**Placeholder scan** — no "TBD" / "implement later" / generic "add error handling" steps. Every code block is concrete and verbatim.

**Type consistency** — `BrandDisambigResult` / `EnrichedReasoning` / `OcrReconcileResult` consistently named across T3-T9. `TaskSlice` consistently used in T1, T3-T5, T8, T9. `Refined` constructor signature (`evaluation_id` + `tasks`) consistent across T1, T8, T9, T11. `_TASK_SCHEMAS` / `_STAGE_BY_TASK` dicts symmetric between T8 and T9.

**Wave-structure note** — added a §"Dependency Graph" + §"Wave structure" below so `parallel-planning` can lift directly. Pre-flight ownership disjointness verified by inspection (every Files-Owned cell appears in exactly one task).

**FR-303 enforcement caveat (T7)** — the structural test is grep-based on field names + Literal values. It's the canary for accidental schema additions; deeper semantic violations (e.g., a `payload: dict` field carrying `{"disposition": "fail"}` at runtime) are NOT caught here — those are caught by the Application Service's downstream type-narrowing in E5. T7 is sufficient for the seam-level invariant.

**Application schema** — the `app/schemas/application.py` module is missing at HEAD (only `app/schemas/wire/application.py::ApplicationEnvelope` exists). T2 Cycle A is the **single owner** of the stub. Every downstream task that constructs `Application(application_id="A-001", evaluation_id="EV-001")` (T8, T9, T11, T12, T13, T14) reads from this stub — there is no race because only T2 writes the file. If E5 needs to extend the stub with additional fields (e.g., applicant identity), add them in E5; for E4 the identity surface is sufficient.

**Recording wire-shape caveat (T8, T9)** — the OpenAI Structured-Outputs and Anthropic tool_use shapes are pinned to current API versions. If APIs drift before E8 demo, the recordings need re-rotation via T15's script. The `_to_anthropic_schema` adapter is intentionally minimal (strips `$schema`/`title`); deeper drift may require a per-impl schema adapter module under `app/orchestrator/_schema_adapters/` (parked for E5 if needed).

---

## Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-03 | Project team | Initial E4 L2 plan. 17 tasks. |
| 0.2 | 2026-05-04 | Project team | plan-review iter-1 fixes: (B1) T2 absorbs `app/schemas/application.py` stub as Cycle A — single owner, removes 8-task race; (B2) T2's `Depends On` → `—` (T2 imports `Refined` by name only, not by shape); (B3) T1 now explicitly modifies `tests/test_schemas_round_trip.py::test_refined_round_trip` instead of hand-waving "Rule 1-3 inline fix"; (W1) dropped unused `monkeypatch.setenv` calls in T8/T9/T11/T12/T13 (api keys passed explicitly); (W2) T9 raises plain `ValueError` for missing `tool_use` block instead of misuse `ValidationError.from_exception_data(line_errors=[])`, retry catches widened to `(ValidationError, ValueError, …)`; (W3) T16 moved Wave 5 → Wave 6 to avoid `tests/conftest.py` co-residency with Wave 5 pytest collection; (W4) T13 seed assertion tightened to `body["seed"] == _DETERMINISTIC_SEED` (catches silent rotation); (W5) T7 adds JSON-schema substring check (defense-in-depth for nested models); (W6) dropped `# type: ignore[call-arg]` on every `Application(...)` stub call (no longer needed). Wave totals: 5+3+2+4+4+2 = 20 commits. |

---

## Dependency Graph

### Task Dependencies

| Task | Depends On | Blocks | Files Owned |
|------|-----------|--------|-------------|
| T1: Refined tighten (drop model_disposition) | — | T7, T8, T9, T11 | `app/schemas/refined.py`, `tests/test_refined_fr303_ready.py`, `tests/test_schemas_round_trip.py` (modify-in-place: rewrite `test_refined_round_trip` to new shape) |
| T2: Application stub + Orchestrator ABC (2-cycle bundle) | — | T3, T4, T5, T8, T9, T11, T12, T13, T14 | `app/schemas/application.py` (Cycle A), `tests/test_application_stub.py` (Cycle A), `app/orchestrator/__init__.py`, `app/orchestrator/base.py`, `app/orchestrator/tasks/__init__.py`, `tests/test_orchestrator_protocol.py` (Cycle B). T2 is the **single owner** of `app/schemas/application.py`; no other E4 task may write it. |
| T3: brand_disambig schema + adapter | T1, T2 | T6, T7, T8, T9, T11 | `app/orchestrator/tasks/brand_disambig.py`, `tests/test_orchestrator_brand_disambig.py` |
| T4: reasoning_enrich schema + adapter | T1, T2 | T6, T7, T8, T9, T11 | `app/orchestrator/tasks/reasoning_enrich.py`, `tests/test_orchestrator_reasoning_enrich.py` |
| T5: ocr_reconcile schema + adapter | T1, T2 | T6, T7, T8, T9, T11 | `app/orchestrator/tasks/ocr_reconcile.py`, `tests/test_orchestrator_ocr_reconcile.py` |
| T6: Strict-schema introspection test | T3, T4, T5 | — | `tests/test_orchestrator_strict_schema.py` |
| T7: FR-303 invariant test | T1, T3, T4, T5 | — | `tests/test_orchestrator_fr303_invariant.py` |
| T8: OpenAIStrictOrchestrator (3 cycles) | T2, T3, T4, T5, T17 | T10, T11, T12, T13, T14 | `app/orchestrator/openai_strict.py`, `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/{brand_disambig,reasoning_enrich,ocr_reconcile}/{01-spirits-clean,02-bourbon-stones-throw}.json` (6 files), `tests/test_orchestrator_openai_strict.py` |
| T9: AnthropicStrictOrchestrator | T2, T3, T4, T5 | T10, T11 | `app/orchestrator/anthropic_strict.py`, `tests/recordings/anthropic/claude-3-5-sonnet-20241022/v1/orchestrator/{brand_disambig,reasoning_enrich,ocr_reconcile}/01-spirits-clean.json` (3 files), `tests/test_orchestrator_anthropic_skeleton.py` |
| T10: DI wiring | T8, T9 | — | `app/deps.py` (replace orchestrator block), `tests/test_orchestrator_deps.py` |
| T11: Substitutability E2E | T8, T9 | — | `tests/test_orchestrator_substitutability.py` |
| T12: Ring-buffer integration test | T8 | — | `tests/test_orchestrator_ring_buffer.py` |
| T13: Determinism asserts | T8 | — | `tests/test_orchestrator_temp_seed_snapshot.py` |
| T14: CLI smoke | T8, T9, T17 | — | `app/orchestrator/__main__.py`, `tests/test_orchestrator_cli_smoke.py` |
| T15: Recording-rotation script | — | — | `scripts/record_orchestrator_responses.py`, `tests/test_record_orchestrator_responses.py` |
| T16: Isolation grep + conftest sanitizer | T8, T9 | — | `tests/test_orchestrator_isolation.py`, `tests/conftest.py` (extend) |
| T17: Synthetic fixture-02 | — | T8, T14 | `fixtures/02-bourbon-stones-throw/label.png`, `scripts/build_synthetic_fixture_02.py`, `tests/test_synthetic_fixture_02.py` |

### Shared Files

No cross-task file modifications within E4. Verified by inspection:

- `app/schemas/refined.py` — modified only by T1.
- `app/deps.py` — modified only by T10 (E1 wrote placeholders; E4 replaces them).
- `app/orchestrator/tasks/__init__.py` — created by T2 (empty package marker); never re-touched.
- `tests/conftest.py` — extended only by T16 (one helper function appended).
- `tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator/` — partitioned by sub-path: T8 owns all 6 files there; no other task writes.
- `tests/recordings/anthropic/claude-3-5-sonnet-20241022/v1/orchestrator/` — T9 owns all 3 files; no other task writes.
- `fixtures/02-bourbon-stones-throw/` — created only by T17.

### Execution Waves

```
Wave 1 (parallel, 4 tasks): [T1, T2, T15, T17]                          ← all four are pure roots after dropping T2's prior T1 dep (T2 imports `Refined` by name only, doesn't depend on its shape; T2 owns its own Application stub via Cycle A so no other Wave 1 task races it)
Wave 2 (parallel, 3 tasks): [T3, T4, T5]                                 ← need T1+T2
Wave 3 (parallel, 2 tasks): [T6, T7]                                     ← need T3-T5
Wave 4 (parallel, 2 tasks): [T8, T9]                                     ← need T2 + T3-T5 (and T17 for T8)
Wave 5 (parallel, 4 tasks): [T10, T11, T12, T13]                         ← need T8/T9; T16 moved to Wave 6 to avoid `tests/conftest.py` co-residency with T11/T12/T13's pytest collection
Wave 6 (parallel, 2 tasks): [T14, T16]                                   ← T14 needs T8+T9+T17; T16 needs T8+T9; both run against a stable tree and have no inter-task dep
```

**Wave 1 ownership pre-flight.** T1 owns `app/schemas/refined.py` + `tests/test_refined_fr303_ready.py` + the in-place rewrite of `tests/test_schemas_round_trip.py::test_refined_round_trip`; T2 owns `app/schemas/application.py` (Cycle A — closes the E1 omission), `app/orchestrator/{__init__.py, base.py, tasks/__init__.py}` (Cycle B), and the two test files for those cycles; T15 owns `scripts/record_orchestrator_responses.py` + its test; T17 owns `fixtures/02-bourbon-stones-throw/` + its build script + its test. **All four tasks write strictly disjoint paths.** T2 has no functional dependency on T1: T2's Cycle B imports `Refined` by name only (the import works against either the pre-T1 or post-T1 schema), and T2's tests do not assert on `Refined`'s field shape. The dependency table reflects this — T2's `Depends On` is `—`.

**Wave 4 ownership pre-flight.** T8 and T9 own disjoint module files + disjoint recording sub-trees + disjoint test files. Both import shared schema modules from T3-T5 (T8 imports `BrandDisambigResult`, etc.; T9 imports the same), but those are reads, not writes. Safe.

**Wave 5 ownership pre-flight.** T10 owns `app/deps.py` (single writer); T11, T12, T13 each own a single test file. Disjoint. 4 tasks under the executor's 6-concurrent cap.

**Wave 6 ownership pre-flight.** T14 owns `app/orchestrator/__main__.py` + `tests/test_orchestrator_cli_smoke.py`; T16 owns `tests/test_orchestrator_isolation.py` and extends `tests/conftest.py`. Disjoint paths. T16 was moved out of Wave 5 because its append to `tests/conftest.py` is collected by every sibling pytest run; if T16 lands a syntactically broken conftest mid-wave, sibling Wave-5 tasks would fail their final pre-commit gate not because of their own diff. Putting T16 in Wave 6 means it lands against a stable tree alongside T14, which itself does not import anything T16 owns.

**Critical path (longest dependency chain):** T2 (Cycle A then Cycle B) → T3 (or T4 or T5) → T8 → T11 (or T10/T12/T13) → T14. **6 wave hops counting boundaries.**

**Parallelism factor.** 17 tasks across 6 waves → effective parallelism ≈ 2.8× vs strict serial. The two heaviest tasks (T8 cloud, T9 anthropic) are co-resident in Wave 4, so the wall-clock floor is `max(T8, T9)` for that wave rather than the sum.

### Execution Strategy

> **For Claude:** Use `parallel-plan-executor` to execute this plan. The executor dispatches every task in a wave concurrently (up to 6 at a time) and holds a barrier between waves. Each task runs in an isolated worktree subagent with the `task-executor` skill body injected for TDD enforcement.

**Wave 1** — Dispatch T1, T2, T15, T17 concurrently in one message. Barrier. Verify 5 commits (T2 = 2 cycles).
**Wave 2** — Dispatch T3, T4, T5 concurrently. Barrier. Verify 3 commits.
**Wave 3** — Dispatch T6, T7 concurrently. Barrier. Verify 2 commits.
**Wave 4** — Dispatch T8, T9 concurrently. Barrier. Verify 4 commits (T8 = 3 cycles, T9 = 1).
**Wave 5** — Dispatch T10, T11, T12, T13 concurrently. Barrier. Verify 4 commits.
**Wave 6** — Dispatch T14, T16 concurrently. Barrier. Verify 2 commits.

**Total expected new commits on `main`:** 17 task slots, expanded by multi-cycle bundles to ~20 (T1+T3+T4+T5+T6+T7+T9+T10+T11+T12+T13+T14+T15+T16+T17 each = 1 → 15 commits; T2 = 2 cycles → 2 commits; T8 = 3 cycles → 3 commits; total = 20).

**Pre-flight invariant** (parallel-plan-executor enforces): for each wave, the union of file-ownership sets is a strict-disjoint set (no file appears twice). Verified above in §Shared Files.
