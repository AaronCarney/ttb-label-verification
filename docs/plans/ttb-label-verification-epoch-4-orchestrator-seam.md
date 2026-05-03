# Epoch 4 — AI Orchestrator Seam (D-004 #2)

> **Parent:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **Tier:** L1 (epoch-level).
> **Substitutability seam owned:** **D-004 swap point #2** — `Orchestrator` `ABC` at `app/orchestrator/base.py`. Two concrete implementations per D-021 prototype-tier scope: one validated default and one alternate-hosted-provider swap-path skeleton. (vLLM/XGrammar federal-on-prem skeleton scoped out of MVP — the ABC permits future re-introduction without rework.)
> **Depends on:** **E1** (`Refined`, `FieldObservation`, `ValidationResult`, `Application`).

---

## 1. Goal

Land the second substitutability seam. The orchestrator performs **three** tasks per T5 / PRD §5.4:

1. **Brand-name borderline disambiguation** (FR-300) — invoked when E2 brand-match Stage B emits `needs_review`.
2. **Reasoning-text enrichment** (FR-301) — paraphrases template reasoning into plain language for the C-AISuggestionBlock UI; original template text is preserved in audit.
3. **OCR multi-reading reconciliation** (FR-302) — invoked when the Vision Extractor surfaces multiple plausible reads of a single field.

The structural FR-303 invariant — **the orchestrator never decides pass/fail** — is enforced at the type level: the `Refined` schema (declared in E1) has no `disposition` field, so a misbehaving orchestrator literally cannot return one. FR-304 fallback (LLM unavailable → `needs_review` with `ENGINE.MODEL.UNAVAILABLE`) is enforced in E5; this epoch ships the orchestrator's own error pathways (timeout, schema-validation failure after retry).

After E4, every orchestrator implementation can be selected by `ORCHESTRATOR_BACKEND={openai,anthropic}` (per D-021) and produces a wire-compatible `Refined` for the same input.

---

## 2. Components delivered

### 2.1 Seam interface (`app/orchestrator/base.py`)

```python
from abc import ABC, abstractmethod
from app.schemas.application import Application
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import ValidationResult
from app.schemas.refined import Refined

class Orchestrator(ABC):
    @abstractmethod
    async def refine(
        self,
        application: Application,
        observations: list[FieldObservation],
        validation_results: list[ValidationResult],
    ) -> Refined: ...

    @abstractmethod
    async def ensure_client(self) -> None: ...
```

### 2.2 Default — `OpenAIStrictOrchestrator` (`app/orchestrator/openai_strict.py`)

The validated default per ARCH §4.2.6 / §8.2:

- OpenAI Structured Outputs `strict:true`.
- `temperature=0`, fixed `seed`, snapshot-pinned model (`LLM_MODEL_SNAPSHOT` env var; default `gpt-4o-2024-08-06`).
- Single-shot pattern only — no ReAct, no multi-step (T5 §Recommendation #1).
- One Pydantic v2 schema per task; the SDK's `responses.create(text_format=Schema)` returns a typed object.
- Records every call into the `CallRecord` ring buffer (`provider="openai"`, `model_version`, `prompt_version`, `output_hash`).

### 2.3 Skeleton — `AnthropicStrictOrchestrator` (`app/orchestrator/anthropic_strict.py`)

Swap-path skeleton per ARCH §4.2.6:

- Anthropic `tool_use` strict mode equivalent.
- Implements `refine()` end-to-end against the Anthropic SDK; unit-tested with recordings.
- **Not** validated against demo fixtures — exists to prove the seam holds.

Gated by `[anthropic]` optional dependency group; `ensure_client()` raises a clear error if the SDK is not installed.

### 2.4 Scoped out of MVP — `VllmXgrammarOrchestrator`

Per D-021 prototype-tier scope reduction, the federal-on-prem-trajectory vLLM/XGrammar skeleton is dropped from MVP. The `Orchestrator` ABC is preserved so future re-introduction is a new module against the existing seam — no architectural change. ARCH §9.4 (production-trajectory deployment topology) is updated to reflect that on-prem orchestrator landing is a future module, not a shipped skeleton.

### 2.5 Task implementations (`app/orchestrator/tasks/`)

Each task is a small Pydantic schema + a prompt template + a per-task adapter that converts `(application, observations, validation_results)` into the per-task input and the per-task output back into a slice of `Refined`:

- `app/orchestrator/tasks/brand_disambig.py` — input: brand-match Stage B borderline candidate set; output: `BrandDisambigResult { decision: "match" | "needs_review", justification: str }`. Tagged to a specific `ValidationResult.rule_id` so the Application Service can patch the right rule's reasoning. **No `pass | fail` field in the schema** (FR-303 invariant test).
- `app/orchestrator/tasks/reasoning_enrich.py` — input: per-rule template reasoning; output: `EnrichedReasoning { plain_language: str, citation_anchor: str }`.
- `app/orchestrator/tasks/ocr_reconcile.py` — input: multiple candidate reads from a single field; output: `OcrReconcileResult { winner: str | None, reasoning: str }`. `winner=None` ⇒ orchestrator abstains; the Application Service routes to `needs_review` with `ENGINE.OBSERVATION.AMBIGUOUS` (FR-903).

### 2.6 DI wiring (`app/deps.py` updated)

```python
def get_orchestrator(settings: Settings) -> Orchestrator:
    match settings.orchestrator_backend:
        case "openai":    return OpenAIStrictOrchestrator(settings)
        case "anthropic": return AnthropicStrictOrchestrator(settings)
        case _: raise ValueError(...)
```

Per D-021, `vllm` is not a supported value in MVP. Future re-introduction is a one-line addition to the match statement after the new module lands.

### 2.7 Test surface

- `tests/test_orchestrator_substitutability.py` — runtime check: both impls (OpenAI + Anthropic, per D-021) subclass `Orchestrator` ABC; `inspect.iscoroutinefunction(impl.refine)` is True; `refine()` signatures match.
- `tests/test_orchestrator_strict_schema.py` — for every task schema, `Schema.model_json_schema()` produces a JSON Schema with `additionalProperties: false` and the OpenAI-strict-mode required-fields invariant.
- `tests/test_orchestrator_fr303_invariant.py` — **structural test** that asserts `"disposition" not in Refined.model_fields` and `"pass" not in <every task output schema field set>` and `"fail" not in <same>`. This test must pass for **every** task schema.
- `tests/test_orchestrator_fr304_fallback.py` — `OpenAIStrictOrchestrator.refine()` with the HTTP client patched to raise `httpx.ConnectError` returns a `Refined` carrying `ENGINE.MODEL.UNAVAILABLE` qualifiers on every task slice; **does not raise**.
- `tests/test_orchestrator_strict_retry.py` — when the LLM returns a malformed structured response, the orchestrator retries once; on second failure, surfaces `LLM_OUTPUT_INVALID` qualifier on the task-specific reason code (per T5 task malformed-output behavior).
- `tests/test_orchestrator_ring_buffer.py` — every successful `refine()` call writes one `CallRecord` per task per attempt; failed calls also record (with `latency_ms` populated).
- `tests/test_orchestrator_temp_seed_snapshot.py` — recorded test asserts the request body contains `temperature=0`, `seed=<deterministic>`, `model=<snapshot>` — drift on any of these is a regression.
- `tests/test_orchestrator_anthropic_skeleton.py` — skeleton-validity smoke (implements `refine()`, returns a `Refined`-shaped object against mocked SDK responses). Per D-021, no `test_orchestrator_vllm_skeleton.py` ships in MVP.

---

## 3. Wire / data contracts owned by this epoch

E4 owns:

- The three task **input** Pydantic schemas (consumed by the orchestrator implementations from the Application Service).
- The three task **output** Pydantic schemas (slices of `Refined`).
- The `Refined` envelope shape (declared in E1 schemas, populated here).
- The OpenAI Structured Outputs schema invariants (`strict:true`, `additionalProperties:false`, `required` populated for every property).

After E4, no later epoch may add a task type without an L1 revision (because tasks couple the orchestrator to specific call sites in E5).

---

## 4. Exit gate

The epoch lands when **all of these pass**:

1. `app/orchestrator/base.py` declares `Orchestrator` as an `abc.ABC` with `refine()` and `ensure_client()`.
2. Both concrete impls (OpenAI + Anthropic, per D-021) subclass `Orchestrator` and pass `tests/test_orchestrator_substitutability.py`.
3. `tests/test_orchestrator_fr303_invariant.py` passes — no `disposition` / `pass` / `fail` field in `Refined` or in any task-output schema.
4. `OpenAIStrictOrchestrator` produces a wire-conforming `Refined` against recorded responses for fixture-01 (clean spirits) and fixture-02 (STONE'S THROW Bourbon — exercises the brand-disambig path even though Stage A normalizes; the recording captures the orchestrator being invoked-but-not-needed signal).
5. FR-304 fallback test passes: simulated `httpx.ConnectError` → `Refined` with `ENGINE.MODEL.UNAVAILABLE` qualifiers; no raised exception.
6. Strict-retry test passes: malformed response → 1 retry → `LLM_OUTPUT_INVALID` qualifier.
7. Every successful and failed `refine()` writes the right `CallRecord` count and shape; ring-buffer FIFO eviction at `maxlen=200` is honored.
8. `grep -rn 'openai\|anthropic' app/ | grep -v 'app/orchestrator/'` returns no hits — orchestrator deps are isolated to the seam directory. (Per D-021: `vllm` import is scoped out of MVP entirely.)
9. `ORCHESTRATOR_BACKEND=openai uv run task demo` boots; `ORCHESTRATOR_BACKEND=anthropic uv run task demo` boots **iff** `[anthropic]` extra is installed (else clear error). `ORCHESTRATOR_BACKEND=vllm` raises a `ValueError` at startup with a clear message (per D-021).
10. Both impls populate `prompt_version`, `model_version`, and `output_hash` in `CallRecord` per ARCH §8.2.

---

## 5. TDD strategy

**Mockable** —

- Both SDKs (`openai`, `anthropic`) at the HTTP layer via `respx` — both use `httpx` under the hood, so HTTP-level recordings work for both. (Per D-021, vLLM is scoped out of MVP — its mocking strategy is a future concern.)
- Pydantic schema introspection — pure Python, no mock needed.

**Real** —

- Pydantic v2 schema generation (`Model.model_json_schema()`) — used to assert `strict:true` invariants.
- Async `httpx` ConnectError simulation for FR-304.

**Recording strategy.** Same as E3: HTTP-level recordings under `tests/recordings/<provider>/<snapshot>/<task>/<fixture>.json`. A regression in the strict schema is caught by the introspection tests; a regression in the orchestrator's behavior against a real SDK call is caught by the recordings.

**Determinism asserts.** Every recorded request body must include `temperature=0` and the pinned `seed`. The test that asserts this is the canary for any regression that breaks T5 §Q5.7 / S5 determinism.

---

## 6. Out of scope for this epoch

- Live LLM calls in CI — strictly recorded.
- Multi-step agents (ReAct, LangGraph) — D-002 forbids; T5 §Recommendation #1 forbids.
- Per-tenant API key rotation — single-key prototype tier (BRD §8.2).
- Cost / token-usage budgets — out of MVP; recorded responses pin token counts for tests.
- Anthropic full validation against demo fixtures — accepted (parent §6 R-7); skeleton exists to prove the seam. (Per D-021, vLLM/XGrammar is out of MVP entirely.)
- The Application Service triggering logic (when to invoke the orchestrator) — **E5**.

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenAI SDK breaking change between snapshot rotations | Medium | Medium | Pin `openai >= 1.50` (ARCH §19.3); HTTP-level recordings survive minor SDK bumps; major bumps require re-recording but the test surface catches it loudly |
| `strict:true` rejects an edge schema (e.g., a `Union[str, None]` that doesn't translate cleanly to JSON Schema) | Medium | Medium | All task schemas use `Optional[T]` rendered as `T \| null` per OpenAI strict-mode rules; the schema-introspection test (item 3 in §4) catches violations at test time |
| The Anthropic skeleton drifts from the OpenAI default and breaks the seam | Medium | Medium | Substitutability test runs both through the same fixture set; signature drift fails type-check; behavior drift fails the contract test |
| Recordings leak API keys | Low | High | HTTP fixture sanitizer in `tests/conftest.py` redacts `Authorization` headers before writing recordings |
| Anthropic `tool_use` strict mode has a different schema dialect than OpenAI's `additionalProperties:false` | Medium | Medium | Per-impl schema adapter under `app/orchestrator/_schema_adapters/` (one tiny module per provider); tested for shape-equivalence |

---

## 8. L2 hand-off notes

When E4 lands:

1. Decompose into ~7 tasks (per D-021 trimmed surface): `base.py` ABC → 3 task schemas (parallel) → `OpenAIStrictOrchestrator` → `AnthropicStrictOrchestrator` skeleton → DI wiring → ring-buffer integration → fallback/retry tests.
2. **Wave structure:** base.py → task schemas (parallel) → orchestrator impls (parallel after task schemas) → DI + ring-buffer integration (sequential after impls).
3. The L2 plan **must** include a task that runs `python -m app.orchestrator.openai_strict --task brand_disambig --fixture 02-bourbon-stones-throw` as a CLI smoke against the recorded responses.
4. The L2 plan **must** include a task that asserts the FR-303 invariant via Python introspection — this is the canary for any future schema change that accidentally adds a disposition field.

---

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial epoch-4 L1 doc. |
| 0.2 | 2026-05-03 | Project team | Applied D-021 prototype-tier scope reduction: dropped `VllmXgrammarOrchestrator` skeleton from MVP (kept OpenAI default + Anthropic skeleton); updated header seam summary, §1 goal, §2.4 (replaced with "scoped out" note), §2.6 DI wiring, §2.7 test surface, §4 exit gate items 8/9/10, §5 mockable list, §6 out-of-scope, §7 risks, §8 L2 hand-off. Substitutability seam unchanged. |
