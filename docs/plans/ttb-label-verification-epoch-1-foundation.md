# Epoch 1 — Foundation & Boot

> **Parent:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **Tier:** L1 (epoch-level). The L2 plan that decomposes this into file-level TDD tasks lives at `docs/plans/2026-MM-DD-ttb-epoch-1-foundation.md` (written immediately before implementation).
> **Substitutability seam owned:** none — but DI container shape (`app/deps.py`) is established here so later seams plug in without re-architecting.

---

## 1. Goal

Stand up the FastAPI single-process app skeleton with all internal data models, environment-driven configuration, structured logging, the DI container, and a stub `/healthz` endpoint — such that `uv run task demo` boots in ≤30 seconds (cloud profile, ARCH §9.1) and every subsequent epoch has a typed, validated foundation to build on. **No vision, no rule logic, no orchestrator wired yet** — those slot in at E2/E3/E4 behind the protocols and ABCs declared here.

This epoch is the only epoch that does not consume any other epoch's output.

---

## 2. Components delivered (paths from ARCH §14.1)

### 2.1 Project setup

- `pyproject.toml` (uv-managed) with **runtime deps only** (FastAPI, uvicorn, pydantic, pydantic-settings, jinja2, python-multipart, pyyaml, rapidfuzz, pillow, openai, httpx, sse-starlette, paddleocr, paddlepaddle, opencv-python-headless, numpy) per ARCH §19.3, plus `[project.optional-dependencies]` `gpu`, `anthropic` (the `vllm` extra was removed per D-021 — see ARCH §19.3), and `[tool.taskipy.tasks]` `demo`, `demo-prod`, `eval-smoke`, `eval-full`, `eval-dashboard`.
- `uv.lock` (committed).
- `Dockerfile` (CPU/cloud-mode) and `Dockerfile.gpu` (CUDA 12.6).
- `docker-compose.yml`, `docker-compose.gpu.yml`.
- `.env.example` (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `VISION_MODE`, `ORCHESTRATOR_BACKEND`, `LOOKAHEAD_K`, `DEV_MODE`, `LLM_MODEL_SNAPSHOT`, `PROMPT_VERSION`, `OTEL_EXPORTER_OTLP_ENDPOINT`).
- `README.md` updates: one-command setup for reviewer profiles A/B/C per ARCH §9.1.

### 2.2 App skeleton

- `app/main.py` — FastAPI app factory; mounts UI static dir; registers the route modules from `app/api/*` that exist by end of E1 (`healthz` only); reads settings; runs the startup hook (currently no-op besides logging).
- `app/config.py` — Pydantic Settings model (single source of truth for the env-var inventory in ARCH §12.2); `Settings.from_env()` factory.
- `app/deps.py` — DI container; declares the lazy provider functions for `VisionExtractor` and `Orchestrator` (returning `NotImplementedError("E3")`/`NotImplementedError("E4")` placeholders that fail loudly at request time but allow the app to boot for E1 acceptance); reads `VISION_MODE`, `ORCHESTRATOR_BACKEND` from settings.
- `app/api/healthz.py` — `GET /healthz` returns 200 with `{"status": "ok", "version": <app_version>, "mode": {vision, orchestrator}}` after E1; full warm-up sentinel pipeline lands in E5.

### 2.3 Internal data models (`app/schemas/`)

The internal Pydantic v2 types from ARCH §6 — every model uses `model_config = ConfigDict(extra="forbid", frozen=True)` per S5 §9:

- `app/schemas/extracted.py` — `FieldObservation`, `Evidence`, `EvidenceSource`, `MatchKind`, `BBox`.
- `app/schemas/expected.py` — `ExpectedValue`, `BeverageClass`.
- `app/schemas/rejection.py` — `ValidationResult`, `Outcome`, `Severity`, `ReasonCode` (plain string + grammar regex), `EngineMeta`.
- `app/schemas/refined.py` — `Refined` (orchestrator output, schema **without** `disposition` field — FR-303 invariant declared at the type level).
- `app/schemas/audit.py` — `AuditRecord`, `PerRuleTraceEntry`, `OverrideEntry` (D-018: per-rule durations live on the sibling `metrics` block, not on audit entries).
- `app/schemas/metrics.py` — `Metrics`, `PerRuleDurationEntry` (per D-018).
- `app/schemas/rules.py` — `RuleSet`, `RuleDefinition`, `MatchPolicy`, `ReasonCodeEntry`, `AssetRef`, `DecisionTable` (loaded by E2; declared here so types are referenceable).
- `app/schemas/batch.py` — `BatchInFlightState`, `BatchItem`, `ItemState` enum.
- `app/schemas/calls.py` — `CallRecord`.
- `app/schemas/wire/application.py` — PRD §6.1 inbound application envelope (rev. 04/2023 Form 5100.31 items 1–18 + `labels[]`); `extra="forbid"` for NFR-SEC-003.
- `app/schemas/wire/disposition.py` — PRD §6.2 outbound envelope (`disposition`, `disposition_confidence`, `fields[]`, `audit_trail`, `metrics`).
- `app/schemas/wire/batch.py` — PRD §6.3 batch envelope.
- `app/schemas/wire/error.py` — PRD §6.4 error envelope (`error_kind`, `reason_code`, `message`, `details`).

### 2.4 Logging subsystem

- `app/logging/otel_genai.py` — JSON-line formatter using OpenTelemetry GenAI semantic-convention attribute names (`gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, etc.); wires Python `logging` to stdout in JSONL.
- `app/logging/redaction.py` — redaction filter for NFR-SEC-004 (drops application content, label bytes, and verbatim extracted values; preserves `evaluation_id`, `batch_id`, `label_id`, `reason_code`, `duration_ms`, `rule_set_version`, `model_version`, `prompt_version`, `error_class`).
- `app/logging/ring_buffer.py` — `CallRecord` deque scaffolding (`maxlen=200`); the actual recording is wired in E3/E4 when the seams produce records.
- `app/logging/__init__.py` — `configure_logging(settings)` called from `app/main.py` startup.

### 2.5 Test infrastructure

- `tests/conftest.py` — fixtures for `Settings` overrides, an in-memory `app.state` factory, a `TestClient` factory, `PIL.Image` synthetic-image fixtures.
- `tests/wire_fixtures/` — golden JSON files for PRD §6.1, §6.2, §6.3, §6.4 envelopes (drawn from ARCH §6.x examples).
- `tests/test_schemas_round_trip.py` — every wire and internal model loads, dumps, and re-loads to byte-identical JSON.
- `tests/test_config_load.py` — settings load from env vars with the documented defaults; missing-required surfaces a clear error.
- `tests/test_logging_emission.py` — JSON-line emission contains the cross-cutting field schema; redaction filter strips configured fields.
- `tests/test_healthz_stub.py` — `GET /healthz` returns 200 with the documented payload shape.
- `pytest.ini` (or `[tool.pytest.ini_options]` in `pyproject.toml`) with markers, asyncio mode `auto`, `testpaths = ["tests"]`.

---

## 3. Wire / data contracts owned by this epoch

E1 owns every Pydantic v2 model that materializes the **PRD §6.1, §6.2, §6.3, §6.4 wire contracts** and every internal type from **ARCH §6.1 through §6.10**. After E1, no later epoch may add a top-level field to those wire envelopes without an L1 revision (per the backtracking rule in §1 of the parent doc). New fields *inside* nested objects (e.g., a new per-field-finding key) are L2 changes.

D-017 confidence aggregation (`min`) is encoded as a method on the disposition envelope's `disposition_confidence` builder, not as a free-floating utility — this keeps the algorithm next to the type that carries it.

D-018 audit/metrics split is encoded structurally: `AuditRecord.per_rule_trace` has only `{rule_id, disposition, evidence_ref}`; `Metrics.per_rule_durations_ms` is a sibling type. The Web layer assembles both blocks from one `EngineMeta` source — the assembly point lands in E5 but the *types* are settled here.

---

## 4. Exit gate (epoch-level acceptance criteria)

The epoch lands when **all of these pass**:

1. `uv sync` (cloud profile, no `--extra gpu`) completes from a clean checkout in ≤90 s on a 5 Mbps connection.
2. `uv run task demo` boots `uvicorn app.main:app` and the process exits 0 on `Ctrl+C` cleanly.
3. `curl http://localhost:8000/healthz` returns 200 with `{"status": "ok", "version": <semver>, "mode": {"vision": "<env-resolved>", "orchestrator": "<env-resolved>"}}`. The endpoint does **not** invoke any seam yet — full warm-up lands in E5.
4. `pytest tests/ -v` passes ≥ the test surface listed in §2.5 (≥ 4 test files, ≥ 25 assertions). Coverage is not a gate at E1 — the goal is type-level correctness, not behavior coverage.
5. Every PRD §6.1/§6.2/§6.3/§6.4 wire envelope round-trips a representative golden JSON byte-identically (`json.dumps(Model.model_validate(json.loads(s)).model_dump()) == json.dumps(json.loads(s))` modulo key order).
6. Every NFR-SEC-002 secret name in ARCH §12.2 is read by `app/config.py` and **only** `app/config.py` (`grep -rn 'os.environ' app/ | grep -v 'config.py'` returns no hits).
7. The structured log emits a single JSON line on `GET /healthz` containing at minimum `{evaluation_id|null, ts, level, msg}` plus the OpenTelemetry GenAI attribute conventions for any LLM calls (none in E1, but the formatter is exercised).
8. `app/deps.py` providers raise `NotImplementedError("seam not wired in E1")` on any path that would invoke `VisionExtractor.extract()` or `Orchestrator.refine()` — proving the DI shape is right without committing to a real implementation.
9. `RuleSet`, `RuleDefinition`, `MatchPolicy`, `ReasonCodeEntry`, `AssetRef`, `DecisionTable` are canonically declared in `app/schemas/rules.py` (E1); `app/rules/models.py` (E2) re-exports them for namespace ergonomics. Asserted by an import-path test: `from app.schemas.rules import RuleSet` and `from app.rules.models import RuleSet` resolve to the same class object (`is` identity, not just structural equality).

---

## 5. TDD strategy

**Test surface** (per §5 in the parent doc):

| Test file | What it asserts |
|---|---|
| `tests/test_schemas_round_trip.py` | Every schema in §2.3 round-trips a golden fixture JSON byte-identically |
| `tests/test_config_load.py` | `Settings.from_env()` honors every documented default and raises on missing required fields with a clear message |
| `tests/test_logging_emission.py` | One log call → one JSON line on stdout; redaction filter drops configured fields; OTel GenAI attribute names match `gen_ai.*` |
| `tests/test_healthz_stub.py` | `GET /healthz` returns 200 with the documented payload shape; the endpoint is registered when `app/main.py` boots |
| `tests/test_dependency_injection.py` | `app/deps.py` providers return correct types per `VISION_MODE` / `ORCHESTRATOR_BACKEND`; calling `extract()` / `refine()` raises `NotImplementedError("E3")`/`("E4")` |

**Mockable** — everything (no upstream deps yet). **Real** — no live external services.

**Fixture style.** Wire envelopes are JSON files committed under `tests/wire_fixtures/`; internal models test against parametrized in-Python fixtures. This keeps the wire contracts version-controllable and reviewable.

---

## 6. Out of scope for this epoch (deferred to later epochs)

- Rule loading, validator registry, brand match — **E2**.
- Vision extractor implementations — **E3**.
- AI orchestrator implementations — **E4**.
- Full `/healthz` warm-up (model load + sentinel pipeline) — **E5**.
- Single-label `POST /labels` endpoint — **E5**.
- Batch processor and SSE — **E6**.
- UI templates and React island — **E7**.
- Eval harness and `/eval` route — **E8**.

The DI container's provider functions and the Settings model **do** declare every env var these later epochs need, so adding a real implementation is a one-line provider swap.

---

## 7. Risk register (epoch-local)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Pydantic v2 + FastAPI version conflict on a fresh `uv sync` | Low | Medium | Pin `pydantic >= 2.9` and `fastapi >= 0.115` per ARCH §19.3; CI runs `uv sync` on a clean image |
| Wire-envelope JSON shape diverges from ARCH §6.x examples (typo in golden fixtures) | Medium | Medium | Golden fixtures are reviewed against the ARCH document line-by-line during the L2 plan-review pass |
| `extra="forbid"` rejects keys the take-home reviewer adds in ad-hoc test inputs | Low | Low | Documented in `README.md`: the wire contract is strict by design (NFR-SEC-003); reviewer uploads route through fixture endpoints |
| `model_config = ConfigDict(frozen=True)` on internal types breaks downstream code that expects mutability | Low | Medium | The frozen choice is per S5 §9 and is the correct posture; later epochs use replace-by-construction (Pydantic's `model_copy`) where needed |
| Circular imports between `app/schemas/wire/*` and `app/schemas/*` | Medium | Low | Wire schemas import internal types only via deferred `TYPE_CHECKING`; the boundary is asserted by an import-graph test |

---

## 8. L2 hand-off notes

When E1 is the next epoch to land, the L2 plan needs to:

- Decompose §2.3 into one task per Pydantic model (≈12 tasks), each with a write-failing-test → write-implementation → run-test → commit cycle. A single per-file commit is appropriate granularity given each file is a few types.
- Decompose §2.4 into `formatter` → `redaction` → `ring_buffer scaffolding` → `__init__.configure_logging` (4 tasks).
- One task for `app/main.py` factory; one for `app/config.py` Settings; one for `app/deps.py` providers; one for `app/api/healthz.py`.
- One task for `pyproject.toml` and `uv.lock` (a single `uv sync` run lands the lock).
- One task to populate `tests/wire_fixtures/` with the four golden JSONs (drawn from ARCH §6.1, §6.2, §6.3, §6.4 examples).
- Wave structure: pyproject.toml → schemas (parallelizable) → logging (parallelizable with schemas) → config + deps + main + healthz (sequential because they import schemas) → tests (parallelizable across files).

The L2 plan **must** include a final task that runs the full epoch exit-gate checklist (§4 of this doc) as an integration-style assertion suite — this is the AC that closes the epoch.

---

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial epoch-1 L1 doc. |
| 0.2 | 2026-05-03 | Project team | D-021 cascade clean-up: dropped `vllm` from the §2.1 `pyproject.toml` extras list (ARCH §19.3 already removed it). No exit-gate change. |
| 0.3 | 2026-05-03 | Project team | **Epoch 1 implementation complete.** L2 plan executed via `parallel-plan-executor` over 17 waves; all 28 tasks landed. Commit range `0bdd0f7..402a26f` (28 atomic commits, fast-forward on `main`, no squash). Final test surface: 62 tests passing (≥25 AC #4 minimum, ≥4 test files). Off-band smoke: `uv run task demo` boots; `curl /healthz` returns `{"status":"ok","version":"0.1.0","mode":{"vision":"auto","orchestrator":"openai"}}`. Deviations from L1: (a) `paddlepaddle-gpu` pin softened from `== 3.0.0` to `>= 2.6` in T1 — `3.0.0` is not on PyPI; (b) `ApplicationEnvelope.serial_number` `max_length` 6→7 in T14 — TTB rev. 04/2023 fixture uses 7-char `YY-NNNN` format; (c) cross-epoch AC #9 `is`-identity assertion is partial — canonical declaration of `RuleSet` ships in `app/schemas/rules.py` (T11) per plan, full identity check vs `app/rules/models.py` re-export deferred to E2 as documented. All other ACs hold without deviation. |
