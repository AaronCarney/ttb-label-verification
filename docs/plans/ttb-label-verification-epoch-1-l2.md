# TTB Label Verification — Epoch 1 (Foundation & Boot) — L2 Implementation Plan

> **For agentic workers:** REQUIRED EXECUTOR: `parallel-plan-executor`. (Per olorin CLAUDE.md: `superpowers:subagent-driven-development` is obsolete and fully replaced by `parallel-plan-executor`. The executor runs each task in an isolated worktree subagent with the `task-executor` skill body injected for TDD enforcement.)
>
> **Parent L1:** [`ttb-label-verification-epoch-1-foundation.md`](./ttb-label-verification-epoch-1-foundation.md) (v0.2)
> **L1 index:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md) (v0.4)
> **Wire contracts:** PRD §6.1, §6.2, §6.3, §6.4 (`docs/PRD.md` v0.6)
> **Internal model contracts:** ARCH §6.1–§6.11 (`docs/ARCHITECTURE.md` v0.3)
> **ADRs in scope:** D-014 (rule data format), D-015 (`VISION_MODE` selection), D-017 (min-aggregation confidence), D-018 (audit/metrics split), D-021 (prototype-tier scope)

**Goal.** Stand up the FastAPI single-process app skeleton with all internal Pydantic v2 data models, environment-driven configuration, structured logging (OTel GenAI semantic-convention attribute names), the DI container with placeholder seam providers, and a stub `GET /healthz` endpoint — such that `uv run task demo` boots and every E1 exit-gate AC in the parent L1 §4 holds.

**Architecture.** Single process, single package (`app/`). Pure declarative Pydantic v2 types under `app/schemas/` (internal) and `app/schemas/wire/` (PRD §6.x boundary envelopes). DI container in `app/deps.py` wires the two seam protocols (`VisionExtractor`, `Orchestrator`) to `NotImplementedError` placeholders that fail loudly on invocation but allow `/healthz` to boot. Logging in `app/logging/` is JSON-line stdout with OTel GenAI attribute conventions and an NFR-SEC-004 redaction filter.

**Tech stack.** Python 3.12, FastAPI ≥ 0.115, Pydantic v2 ≥ 2.9, pydantic-settings ≥ 2.6, uv (lockfile committed), pytest + pytest-asyncio (auto mode), `httpx.AsyncClient` for in-process FastAPI tests via `TestClient`. No vision libs, no LLM SDK calls, no rule evaluation logic at this epoch — those land at E2/E3/E4 behind the seams declared here.

**TDD posture.** Every task is a single Red→Green→Commit cycle on one file (or one tightly coupled file group: schema + golden fixture, or formatter + filter). No omnibus tasks. Each commit is atomic and conventional (`feat:`/`test:`/`chore:`/`docs:`). No `--amend`. No squash on merge. Pre-existing main is fast-forwarded after each task.

**Hard scope boundary.** This plan does NOT touch `app/rules/`, `app/vision/`, `app/orchestrator/`, `app/services/`, `app/batch/`, `app/ui/`, `frontend/`, `rules/*.yaml`, `assets/`, `fixtures/01-07/`, `demo/`, `eval/`, `Dockerfile*`, `docker-compose*.yml` — those belong to E2–E8. The L1 sub-doc lists Dockerfiles in §2.1 but the exit gate (§4) does not test them; deferring to E8 keeps E1 honest. **Cross-epoch import-identity AC** (parent §4 #9: `from app.rules.models import RuleSet is from app.schemas.rules import RuleSet`) is partially satisfied here — E1 establishes the canonical declaration in `app/schemas/rules.py`; the `is`-identity assertion lands in E2 when `app/rules/models.py` re-exports.

---

## File map

| Path | Created by task | Responsibility |
|---|---|---|
| `pyproject.toml` | T1 | Project metadata, runtime deps, optional `[gpu]`/`[anthropic]`, `[tool.taskipy.tasks]`, pytest config |
| `uv.lock` | T1 | Resolved lockfile (committed) |
| `.gitignore` (existing) | — | Already in repo; not modified |
| `.env.example` | T2 | Documented env-var inventory matching ARCH §12.2 |
| `tests/conftest.py` | T3 | Settings override factory, TestClient factory, PIL fixture helper |
| `tests/wire_fixtures/application.json` | T4 | PRD §6.1 golden fixture |
| `tests/wire_fixtures/disposition.json` | T4 | PRD §6.2 golden fixture (with D-018 metrics block) |
| `tests/wire_fixtures/batch.json` | T4 | PRD §6.3 golden fixture |
| `tests/wire_fixtures/error.json` | T4 | PRD §6.4 golden fixture |
| `app/__init__.py` | T1 | Package marker |
| `app/schemas/__init__.py` | T6 (post plan-review swap) | Package marker |
| `app/schemas/expected.py` | T6 | `ExpectedValue`, `BeverageClass` |
| `app/schemas/extracted.py` | T5 (depends on T6 for `BeverageClass`) | `FieldObservation`, `Evidence`, `EvidenceSource`, `MatchKind`, `BBox` |
| `app/schemas/rejection.py` | T7 | `ValidationResult`, `Outcome`, `Severity`, `ReasonCode`, `EngineMeta` |
| `app/schemas/refined.py` | T8 | `Refined` (FR-303 invariant: no `disposition` field) |
| `app/schemas/audit.py` | T9 | `AuditRecord`, `PerRuleTraceEntry`, `OverrideEntry` (D-018: no `duration_ms` in audit) |
| `app/schemas/metrics.py` | T10 | `Metrics`, `PerRuleDurationEntry` (D-018 sibling of audit) |
| `app/schemas/rules.py` | T11 | Canonical declaration of `RuleSet`, `RuleDefinition`, `MatchPolicy`, `ReasonCodeEntry`, `AssetRef`, `DecisionTable` |
| `app/schemas/batch.py` | T12 | `BatchInFlightState`, `BatchItem`, `ItemState` |
| `app/schemas/calls.py` | T13 | `CallRecord` |
| `app/schemas/wire/__init__.py` | T14 | Package marker |
| `app/schemas/wire/application.py` | T14 | PRD §6.1 inbound envelope |
| `app/schemas/wire/disposition.py` | T15 | PRD §6.2 outbound envelope (audit_trail + metrics blocks) |
| `app/schemas/wire/batch.py` | T16 | PRD §6.3 batch envelope |
| `app/schemas/wire/error.py` | T17 | PRD §6.4 error envelope |
| `app/logging/__init__.py` | T21 | `configure_logging(settings)` entry point |
| `app/logging/otel_genai.py` | T18 | JSON-line formatter using `gen_ai.*` attribute names |
| `app/logging/redaction.py` | T19 | NFR-SEC-004 redaction filter |
| `app/logging/ring_buffer.py` | T20 | `CallRecord` `deque(maxlen=200)` scaffolding |
| `app/config.py` | T22 | `Settings` Pydantic Settings model — single source of truth for env vars |
| `app/deps.py` | T23 | DI container with `VisionExtractor`/`Orchestrator` placeholder providers |
| `app/api/__init__.py` | T24 | Package marker |
| `app/api/healthz.py` | T24 | `GET /healthz` route handler |
| `app/main.py` | T25 | FastAPI app factory; wires startup hook + healthz route |
| `tests/test_schemas_round_trip.py` | T5–T17 (one assertion added per schema) | One round-trip assertion per internal/wire model |
| `tests/test_logging_emission.py` | T18–T21 | Formatter + redaction + configure_logging integration |
| `tests/test_config_load.py` | T22 | Settings env-var loading |
| `tests/test_dependency_injection.py` | T23 | DI providers raise `NotImplementedError("E3")`/`("E4")` |
| `tests/test_healthz_stub.py` | T24 | `/healthz` returns 200 with documented payload shape |
| `tests/test_main_app_factory.py` | T25 | App factory registers `/healthz` route |
| `tests/test_secrets_grep.py` | T26 | NFR-SEC-002: `os.environ` only read by `app/config.py` |
| `tests/test_e1_exit_gate.py` | T27 | Integration suite asserting all 9 ACs from L1 §4 |
| `README.md` | T28 | Reviewer-profile setup instructions per ARCH §9.1 |

---

## Conventions used in this plan

- **Frozen Pydantic models.** Every internal schema sets `model_config = ConfigDict(extra="forbid", frozen=True)` per ARCH §6 / S5 §9. Wire envelopes set `extra="forbid"` (frozen optional but not required since they are inbound parse targets).
- **Round-trip assertion.** A wire/internal model is asserted to "round-trip" iff `Model.model_validate(json.loads(s)).model_dump_json() == canonical_json` modulo key order. The test helper canonicalizes by sorting keys.
- **Failing-test verification.** Every task's Step 2 runs the test and confirms the expected failure mode (file/symbol not found, assertion error). If the test passes accidentally on Step 2, the task is wrong — re-author the test.
- **Commit message style.** Conventional Commits with subject ≤ 72 chars. Body lines ≤ 100 chars, optional. No co-authored trailers (per project convention).
- **Reading order for an executor subagent.** The L1 sub-doc (`docs/plans/ttb-label-verification-epoch-1-foundation.md`) and ARCH §6 are the contract; this plan lifts the exact field shapes — but if any cell here disagrees with ARCH §6, ARCH §6 wins and the task should flag the divergence in its commit message.

---

## Task 1: pyproject.toml + uv.lock + app package marker

**Files:**
- Create: `pyproject.toml`
- Create: `uv.lock` (generated by `uv sync`)
- Create: `app/__init__.py`
- Test: `tests/test_bootstrap.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_bootstrap.py`:

```python
"""Bootstrap-level smoke tests: dependencies install, app package importable."""
from __future__ import annotations


def test_fastapi_importable() -> None:
    import fastapi  # noqa: F401


def test_pydantic_v2() -> None:
    import pydantic
    assert pydantic.VERSION.startswith("2."), pydantic.VERSION


def test_pydantic_settings_importable() -> None:
    import pydantic_settings  # noqa: F401


def test_app_package_importable() -> None:
    import app  # noqa: F401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bootstrap.py -v`
Expected: FAIL — `uv` cannot resolve project / `app` not importable.

- [ ] **Step 3: Write the minimal pyproject.toml**

Create `pyproject.toml`:

```toml
[project]
name = "ttb-label-prototype"
version = "0.1.0"
description = "TTB AI-powered alcohol label verification prototype."
requires-python = ">=3.12"
dependencies = [
    "fastapi >= 0.115",
    "uvicorn[standard] >= 0.32",
    "pydantic >= 2.9",
    "pydantic-settings >= 2.6",
    "jinja2 >= 3.1",
    "python-multipart >= 0.0.12",
    "pyyaml >= 6.0",
    "rapidfuzz >= 3.10",
    "pillow >= 11.0",
    "openai >= 1.50",
    "httpx >= 0.27",
    "sse-starlette >= 2.1",
    "paddleocr >= 3.0",
    "paddlepaddle >= 3.0",
    "opencv-python-headless >= 4.10",
    "numpy >= 2.0",
]

[project.optional-dependencies]
gpu = [
    "paddlepaddle-gpu == 3.0.0",
    "torch >= 2.5",
]
anthropic = ["anthropic >= 0.39"]

[dependency-groups]
dev = [
    "pytest >= 8.3",
    "pytest-asyncio >= 0.24",
    "taskipy >= 1.13",
]

[tool.taskipy.tasks]
demo = "uvicorn app.main:app --port 8000 --reload"
demo-prod = "uvicorn app.main:app --port 8000"
eval-smoke = "python -m eval.harness --subset smoke"
eval-full = "python -m eval.harness --subset full"
eval-dashboard = "python -m eval.dashboard --history eval/history/"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

Create `app/__init__.py` (empty):

```python
```

- [ ] **Step 4: Generate the lockfile**

Run: `uv sync`
Expected: PASS — resolves the dependency tree and writes `uv.lock`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_bootstrap.py -v`
Expected: 4 PASSED.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock app/__init__.py tests/test_bootstrap.py
git commit -m "chore(e1): bootstrap pyproject, uv.lock, app package, smoke tests"
```

---

## Task 2: .env.example

**Files:**
- Create: `.env.example`
- Test: `tests/test_env_example.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_env_example.py`:

```python
"""Assert .env.example documents every env var listed in ARCH §12.2."""
from __future__ import annotations

from pathlib import Path

REQUIRED_KEYS = {
    "VISION_MODE",
    "ORCHESTRATOR_BACKEND",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "LLM_MODEL_SNAPSHOT",
    "PROMPT_VERSION",
    "LOOKAHEAD_K",
    "DEV_MODE",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
}


def _parse_env_example(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        keys.add(line.split("=", 1)[0].strip())
    return keys


def test_env_example_documents_all_required_keys() -> None:
    path = Path(__file__).parents[1] / ".env.example"
    assert path.exists(), ".env.example must exist at repo root"
    keys = _parse_env_example(path)
    missing = REQUIRED_KEYS - keys
    assert not missing, f"missing env-var entries in .env.example: {sorted(missing)}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_env_example.py -v`
Expected: FAIL — file not found.

- [ ] **Step 3: Create .env.example**

Create `.env.example`:

```bash
# === TTB Label Verification — environment-variable inventory ===
# Source of truth: ARCH §12.2; loaded by app/config.py (Pydantic Settings).
# Copy to .env and fill secrets locally; .env is gitignored.

# Vision-extractor selection (D-015). Values: local | cloud | auto.
# `auto` probes nvidia-smi at process start and falls back to cloud.
VISION_MODE=auto

# Orchestrator backend (D-021). Values: openai | anthropic.
ORCHESTRATOR_BACKEND=openai

# Required when ORCHESTRATOR_BACKEND=openai or VISION_MODE in {cloud, auto-fallback}.
OPENAI_API_KEY=

# Required when ORCHESTRATOR_BACKEND=anthropic.
ANTHROPIC_API_KEY=

# Pinned model snapshot (T5 Recommendation #6). Drift triggers cache regeneration (D-020).
LLM_MODEL_SNAPSHOT=gpt-4o-2024-08-06

# Versioned prompt identifier (D-020).
PROMPT_VERSION=v1

# Batch lookahead window (PRD §1.4 / FR-400 series).
LOOKAHEAD_K=3

# Truthy gates /eval and /batches/{id}/labels/{lid}/calls routes (D-019).
DEV_MODE=

# Future OTel collector endpoint; unset = JSON-line stdout (S3 Q13).
OTEL_EXPORTER_OTLP_ENDPOINT=

# Optional logging level (default INFO). One of DEBUG/INFO/WARNING/ERROR/CRITICAL.
# (Not in ARCH §12.2 — added in E1 L2; flag for ARCH amendment as a follow-up.)
LOG_LEVEL=INFO
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_env_example.py -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add .env.example tests/test_env_example.py
git commit -m "feat(e1): document env-var inventory in .env.example"
```

---

## Task 3: tests/conftest.py — shared fixtures

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/__init__.py` (empty package marker)
- Test: `tests/test_conftest.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_conftest.py`:

```python
"""Conftest fixtures must be importable and produce the documented helpers."""
from __future__ import annotations


def test_synthetic_image_fixture(synthetic_jpeg_bytes: bytes) -> None:
    assert synthetic_jpeg_bytes[:3] == b"\xff\xd8\xff"  # JPEG SOI marker
    assert len(synthetic_jpeg_bytes) > 100


def test_wire_fixtures_dir_path(wire_fixtures_dir) -> None:
    assert wire_fixtures_dir.is_dir()
    assert wire_fixtures_dir.name == "wire_fixtures"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_conftest.py -v`
Expected: FAIL — fixtures `synthetic_jpeg_bytes` / `wire_fixtures_dir` not found.

- [ ] **Step 3: Create conftest**

Create `tests/__init__.py` (empty):

```python
```

Create `tests/conftest.py`:

```python
"""Shared pytest fixtures for the TTB Label Verification test suite."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def wire_fixtures_dir() -> Path:
    return Path(__file__).parent / "wire_fixtures"


@pytest.fixture
def synthetic_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_conftest.py -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add tests/__init__.py tests/conftest.py tests/test_conftest.py
git commit -m "test(e1): add conftest with synthetic-image and fixtures-dir fixtures"
```

---

## Task 4: tests/wire_fixtures/ — PRD §6.x golden JSONs

**Files:**
- Create: `tests/wire_fixtures/application.json`
- Create: `tests/wire_fixtures/disposition.json`
- Create: `tests/wire_fixtures/batch.json`
- Create: `tests/wire_fixtures/error.json`
- Test: `tests/test_wire_fixtures.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_wire_fixtures.py`:

```python
"""Wire fixtures must exist, parse as JSON, and carry the canonical top-level keys."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

EXPECTED_TOP_LEVEL_KEYS: dict[str, set[str]] = {
    "application.json": {
        "permit_number", "source_of_product", "serial_number",
        "type_of_product", "brand_name", "applicant", "phone",
        "type_of_application", "date_of_application", "applicant_print_name",
        "perjury_attested", "labels",
    },
    "disposition.json": {
        "evaluation_id", "label_ref", "disposition", "disposition_confidence",
        "fields", "audit_trail", "metrics",
    },
    "batch.json": {"batch_id", "agent_id", "submitted_at", "items"},
    "error.json": {"error_kind", "reason_code", "message", "details"},
}


@pytest.mark.parametrize("name,keys", list(EXPECTED_TOP_LEVEL_KEYS.items()))
def test_fixture_exists_parses_and_has_required_keys(
    wire_fixtures_dir: Path, name: str, keys: set[str]
) -> None:
    path = wire_fixtures_dir / name
    assert path.exists(), f"missing fixture: {name}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert keys.issubset(data.keys()), f"{name} missing keys: {keys - data.keys()}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_wire_fixtures.py -v`
Expected: 4 FAILED — fixtures missing.

- [ ] **Step 3: Create the four golden fixtures**

Create `tests/wire_fixtures/application.json`:

```json
{
  "rep_id": null,
  "permit_number": "DSP-CA-12345",
  "source_of_product": "domestic",
  "serial_number": "26-0042",
  "type_of_product": "distilled_spirits",
  "brand_name": "Stone's Throw",
  "fanciful_name": null,
  "applicant": {
    "name": "Stone's Throw Distilling LLC",
    "address": {
      "street": "100 Main St",
      "city": "Napa",
      "state": "CA",
      "zip": "94559",
      "country": "USA"
    },
    "mailing_address": null
  },
  "formula": null,
  "grape_varietals": null,
  "wine_appellation": null,
  "phone": "+1-707-555-0100",
  "email": "labels@stonesthrow.example",
  "type_of_application": {
    "cola": true,
    "exemption": false,
    "exemption_state": null,
    "distinctive_bottle": false,
    "bottle_capacity": null,
    "resubmission": false,
    "prior_ttb_id": null
  },
  "blown_branded_embossed_text": null,
  "date_of_application": "2026-04-01",
  "applicant_signature": "e-filed",
  "applicant_print_name": "Jane Doe",
  "perjury_attested": true,
  "labels": [
    {
      "image_ref": "label-front-001",
      "face_tag": "front",
      "dimensions": {"width_px": 1200, "height_px": 1800, "dpi": 300}
    }
  ]
}
```

Create `tests/wire_fixtures/disposition.json`:

```json
{
  "evaluation_id": "00000000-0000-4000-8000-000000000001",
  "label_ref": "label-front-001",
  "disposition": "pass",
  "disposition_confidence": {"band": "high", "numeric": 0.94},
  "fields": [
    {
      "field_name": "brand_name",
      "extracted_value": "Stone's Throw",
      "expected_value": "Stone's Throw",
      "evidence": {
        "bbox": [120, 240, 800, 120],
        "crop_ref": "crop-brand-001",
        "extraction_confidence": 0.96
      },
      "rule_findings": [
        {
          "rule_id": "common.brand.exact_or_normalized",
          "cfr_citation": "27 CFR §4.33(a)",
          "disposition": "pass",
          "reason_code": "BRAND.NAME.MATCH",
          "plain_language_explanation": "Brand name matches application after normalization."
        }
      ],
      "ai_suggestion": {
        "present": false,
        "task": null,
        "text": null,
        "model_disposition": null
      },
      "field_confidence": {"band": "high", "numeric": 0.94}
    }
  ],
  "audit_trail": {
    "evaluation_id": "00000000-0000-4000-8000-000000000001",
    "rule_set_version": "0.1.0",
    "model_version": "gpt-4o-2024-08-06",
    "prompt_version": "v1",
    "input_hash": "0000000000000000000000000000000000000000000000000000000000000001",
    "output_hash": "0000000000000000000000000000000000000000000000000000000000000002",
    "started_at": "2026-04-01T12:00:00.000Z",
    "completed_at": "2026-04-01T12:00:01.230Z",
    "per_rule_trace": [
      {
        "rule_id": "common.brand.exact_or_normalized",
        "disposition": "pass",
        "evidence_ref": "crop-brand-001"
      }
    ],
    "overrides": []
  },
  "metrics": {
    "total_duration_ms": 1230,
    "per_rule_durations_ms": [
      {"rule_id": "common.brand.exact_or_normalized", "duration_ms": 8}
    ],
    "vision_duration_ms": 720,
    "orchestrator_duration_ms": 480
  }
}
```

Create `tests/wire_fixtures/batch.json`:

```json
{
  "batch_id": "00000000-0000-4000-8000-00000000b001",
  "agent_id": "session-abc123",
  "submitted_at": "2026-04-01T12:00:00.000Z",
  "items": [
    {"label_ref": "label-front-001", "application_ref": "app-001"},
    {"label_ref": "label-front-002", "application_ref": "app-002"}
  ]
}
```

Create `tests/wire_fixtures/error.json`:

```json
{
  "error_kind": "rejected_input",
  "reason_code": "ENGINE.INPUT.APPLICATION_MISSING",
  "message": "Application envelope missing required field: brand_name.",
  "details": {
    "expected_inputs": ["brand_name"],
    "received_inputs": []
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_wire_fixtures.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add tests/wire_fixtures/ tests/test_wire_fixtures.py
git commit -m "test(e1): add PRD §6.1–§6.4 golden wire fixtures"
```

---

## Task 5: app/schemas/extracted.py — FieldObservation + Evidence + supporting enums

**Order note (post plan-review revision):** This task runs **after T6** because `extracted.py` real-imports `BeverageClass` from `app.schemas.expected`. T6 owns `app/schemas/__init__.py` creation; T5 only adds `extracted.py` and the schema-test file.

**Files:**
- Create: `app/schemas/extracted.py`
- Test: `tests/test_schemas_round_trip.py` (new file; subsequent schema tasks add cases to it)

- [ ] **Step 1: Write the failing test**

Create `tests/test_schemas_round_trip.py`:

```python
"""Internal & wire schemas round-trip a representative payload byte-identically."""
from __future__ import annotations

import json

import pytest


def test_extracted_field_observation_round_trip() -> None:
    from app.schemas.expected import BeverageClass
    from app.schemas.extracted import (
        BBox,
        Evidence,
        EvidenceSource,
        FieldObservation,
        MatchKind,
    )

    obs = FieldObservation(
        field_id="brand",
        beverage_class=BeverageClass.SPIRITS,
        observed_value="Stone's Throw",
        evidence=(
            Evidence(
                field_id="brand",
                source=EvidenceSource.OCR,
                page_id=None,
                panel="front",
                image_uri=None,
                bbox=(120, 240, 800, 120),
                extracted_text="Stone's Throw",
                normalized_text="stones throw",
                matched_against_value="Stone's Throw",
                match_kind=MatchKind.NORMALIZED,
                match_score=None,
                confidence=0.96,
                notes=None,
            ),
        ),
        timestamp_ms=1714579200000,
        upstream_meta={"engine": "paddleocr-3.0", "snapshot": "v1"},
    )
    obs2 = FieldObservation.model_validate_json(obs.model_dump_json())
    assert obs2 == obs


def test_extracted_models_are_frozen() -> None:
    from app.schemas.extracted import BBox, Evidence, EvidenceSource, MatchKind

    ev = Evidence(
        field_id="brand",
        source=EvidenceSource.OCR,
        page_id=None,
        panel=None,
        image_uri=None,
        bbox=(0, 0, 1, 1),
        extracted_text=None,
        normalized_text=None,
        matched_against_value=None,
        match_kind=MatchKind.NONE,
        match_score=None,
        confidence=0.5,
        notes=None,
    )
    with pytest.raises(Exception):  # ValidationError or FrozenInstanceError-like
        ev.confidence = 0.9  # type: ignore[misc]


def test_extracted_models_forbid_extra_fields() -> None:
    from pydantic import ValidationError

    from app.schemas.extracted import Evidence, EvidenceSource, MatchKind

    with pytest.raises(ValidationError):
        Evidence(
            field_id="brand",
            source=EvidenceSource.OCR,
            page_id=None,
            panel=None,
            image_uri=None,
            bbox=None,
            extracted_text=None,
            normalized_text=None,
            matched_against_value=None,
            match_kind=MatchKind.NONE,
            match_score=None,
            confidence=0.5,
            notes=None,
            unexpected_extra="bad",  # type: ignore[call-arg]
        )
```

(T5 runs after T6 — `extracted.py` real-imports `BeverageClass` from `expected.py`. The wave graph below places T6 in Wave 3, T5 in Wave 4.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_extracted_models_forbid_extra_fields -v`
Expected: FAIL — `app.schemas.extracted` import error.

- [ ] **Step 3: Implement the file**

Create `app/schemas/extracted.py`:

```python
"""Vision-extractor output models. Source: ARCH §6.1, §6.2."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.expected import BeverageClass


BBox = tuple[int, int, int, int]


class EvidenceSource(str, Enum):
    OCR = "ocr"
    LAYOUT = "layout"
    CLASSIFIER = "classifier"
    DERIVED = "derived"
    METADATA = "metadata"


class MatchKind(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    HASH = "hash"
    NUMERIC_BAND = "numeric_band"
    LOOKUP = "lookup"
    REGEX = "regex"
    LAYOUT = "layout"
    NONE = "none"


class Evidence(BaseModel):
    """A single piece of evidence supporting (or contradicting) a rule outcome.

    Source: ARCH §6.2.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_id: str
    source: EvidenceSource
    page_id: str | None = None
    panel: str | None = None
    image_uri: str | None = None
    bbox: BBox | None = None
    extracted_text: str | None = None
    normalized_text: str | None = None
    matched_against_value: str | None = None
    match_kind: MatchKind
    match_score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    notes: str | None = None


class FieldObservation(BaseModel):
    """What the Vision Extractor produces for one extracted field on one label.

    Source: ARCH §6.1.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_id: str
    beverage_class: BeverageClass
    observed_value: Any | None = None
    evidence: tuple[Evidence, ...]
    timestamp_ms: int | None = None
    upstream_meta: dict[str, Any] = Field(default_factory=dict)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py -v`
Expected: 3 PASSED (round-trip + frozen + forbid). T6 has already shipped `app.schemas.expected.BeverageClass`, so the full round-trip is exercisable.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/extracted.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add FieldObservation + Evidence + Match/Source enums"
```

---

## Task 6: app/schemas/expected.py — ExpectedValue + BeverageClass

**Order note (post plan-review revision):** T6 runs **before T5**. T6 owns the `app/schemas/__init__.py` package marker because `BeverageClass` is canonically declared here and `extracted.py` (T5) imports from it.

**Files:**
- Create: `app/schemas/__init__.py` (empty package marker)
- Create: `app/schemas/expected.py`
- Test: `tests/test_schemas_expected.py` (small per-module test; the shared `test_schemas_round_trip.py` is created by T5 once `extracted.py` lands)

- [ ] **Step 1: Write the failing test**

Create `tests/test_schemas_expected.py`:

```python
"""Round-trip tests for app.schemas.expected (T6 own test file)."""
from __future__ import annotations


def test_expected_value_round_trip() -> None:
    from decimal import Decimal

    from app.schemas.expected import BeverageClass, ExpectedValue

    ev = ExpectedValue(
        field_id="alcohol_content",
        value=None,
        aliases=(),
        abv_labeled_pct=Decimal("36.0"),
        abv_actual_pct=Decimal("35.9"),
        container_volume_ml=Decimal("750"),
        parameters={"is_import": False},
        source_cola="cola-001",
    )
    ev2 = ExpectedValue.model_validate_json(ev.model_dump_json())
    assert ev2 == ev
    assert BeverageClass("spirits") is BeverageClass.SPIRITS
```

(The cross-cutting `FieldObservation` round-trip lives in T5's `tests/test_schemas_round_trip.py` — T5 runs after T6 and exercises both modules together.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_expected.py -v`
Expected: FAIL — `app.schemas.expected` not found.

- [ ] **Step 3: Implement the files**

Create `app/schemas/__init__.py` (empty package marker; consumed by T5 and every later schema task):

```python
```

Create `app/schemas/expected.py`:

```python
"""Application-derived reference values. Source: ARCH §6.3."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BeverageClass(str, Enum):
    WINE = "wine"
    SPIRITS = "spirits"
    MALT = "malt"


class ExpectedValue(BaseModel):
    """What the application JSON says should be on the label.

    Constructed by the Application Service from the inbound application envelope
    (PRD §6.1) on each evaluation; held only for the call frame.

    Source: ARCH §6.3.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_id: str
    value: Any | None = None
    aliases: tuple[str, ...] = ()
    abv_labeled_pct: Decimal | None = None
    abv_actual_pct: Decimal | None = None
    container_volume_ml: Decimal | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    source_cola: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_expected.py -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/__init__.py app/schemas/expected.py tests/test_schemas_expected.py
git commit -m "feat(e1): add ExpectedValue + BeverageClass + schemas pkg marker"
```

---

## Task 7: app/schemas/rejection.py — ValidationResult + Outcome/Severity/ReasonCode + EngineMeta

**Files:**
- Create: `app/schemas/rejection.py`
- Modify: `tests/test_schemas_round_trip.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_reason_code_grammar() -> None:
    from app.schemas.rejection import ReasonCode

    assert ReasonCode.validate_grammar("BRAND.NAME.MATCH") == "BRAND.NAME.MATCH"
    assert (
        ReasonCode.validate_grammar("ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND")
        == "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND"
    )
    assert (
        ReasonCode.validate_grammar("ENGINE.MODEL.UNAVAILABLE.LLM_OUTPUT_INVALID")
        == "ENGINE.MODEL.UNAVAILABLE.LLM_OUTPUT_INVALID"
    )
    import pytest

    for bad in ["lower.case.code", "TOO.SHORT", "FIVE.PARTS.IS.TOO.MANY.NOPE", ""]:
        with pytest.raises(ValueError):
            ReasonCode.validate_grammar(bad)


def test_validation_result_round_trip() -> None:
    from app.schemas.expected import BeverageClass
    from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult

    vr = ValidationResult(
        rule_id="common.brand.exact_or_normalized",
        cfr_citation="27 CFR §4.33(a)",
        beverage_class=BeverageClass.SPIRITS,
        outcome=Outcome.PASS,
        severity=Severity.INFO,
        reason_code="BRAND.NAME.MATCH",
        aggregated_confidence=0.94,
        evidence=(),
        expected=None,
        observed=None,
        message="Brand name matches.",
        engine_meta=EngineMeta(
            engine_version="0.1.0",
            rule_pack_version="0.1.0",
            rule_pack="common",
            started_at_ms=1714579200000,
            elapsed_ms=8,
        ),
    )
    vr2 = ValidationResult.model_validate_json(vr.model_dump_json())
    assert vr2 == vr
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_reason_code_grammar tests/test_schemas_round_trip.py::test_validation_result_round_trip -v`
Expected: 2 FAILED — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/rejection.py`:

```python
"""Rule Engine outcome models. Source: ARCH §6.4, §6.5."""
from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.expected import BeverageClass, ExpectedValue
from app.schemas.extracted import Evidence, FieldObservation


REASON_CODE_GRAMMAR = re.compile(r"^[A-Z][A-Z0-9_]*(?:\.[A-Z][A-Z0-9_]*){2,3}$")


class Outcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_APPLICABLE = "not_applicable"
    TIMEOUT = "timeout"
    ERROR = "error"


class Severity(str, Enum):
    REJECT = "reject"
    WARN = "warn"
    INFO = "info"


class ReasonCode:
    """Reason-code grammar validator. The runtime type is `str`; we keep the
    validator as a static helper so YAML-loaded codes can be sanity-checked
    by the RuleLoader (E2) and at construction sites (E5).

    Grammar: ``BIN.SUB.SPECIFIC[.QUALIFIER]``. Source: ARCH §6.5.
    """

    @staticmethod
    def validate_grammar(value: str) -> str:
        if not isinstance(value, str) or not REASON_CODE_GRAMMAR.match(value):
            raise ValueError(f"reason_code does not match grammar: {value!r}")
        return value


class EngineMeta(BaseModel):
    """Per-rule engine metadata. Source: ARCH §6.4."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine_version: str
    rule_pack_version: str
    rule_pack: str
    started_at_ms: int
    elapsed_ms: int


class ValidationResult(BaseModel):
    """Single, immutable outcome of evaluating one rule on one application + one label.

    Source: ARCH §6.4. Per ADR D-017, ``aggregated_confidence`` is the **min**
    over evidence confidences (computed at construction by the engine).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    cfr_citation: str
    beverage_class: BeverageClass
    outcome: Outcome
    severity: Severity
    reason_code: str | None = None
    aggregated_confidence: float = Field(ge=0.0, le=1.0)
    evidence: tuple[Evidence, ...] = ()
    expected: ExpectedValue | None = None
    observed: FieldObservation | None = None
    message: str | None = None
    engine_meta: EngineMeta
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_reason_code_grammar tests/test_schemas_round_trip.py::test_validation_result_round_trip -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/rejection.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add ValidationResult + Outcome/Severity + ReasonCode grammar"
```

---

## Task 8: app/schemas/refined.py — FR-303 invariant (no `disposition` field)

**Files:**
- Create: `app/schemas/refined.py`
- Modify: `tests/test_schemas_round_trip.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_refined_round_trip() -> None:
    from app.schemas.refined import Refined

    r = Refined(
        evaluation_id="00000000-0000-4000-8000-000000000001",
        task="brand_borderline",
        text="Stone's Throw vs Stones Throw — punctuation only.",
        model_disposition="pass",
    )
    r2 = Refined.model_validate_json(r.model_dump_json())
    assert r2 == r


def test_refined_has_no_disposition_field_fr303() -> None:
    """FR-303 invariant: the orchestrator output schema must NOT carry a top-level
    ``disposition`` field — AI never decides pass/fail.
    ``model_disposition`` is permitted (it is the model's *suggestion*, not the
    deterministic verdict). The forbidden field is the bare ``disposition``.
    """
    from app.schemas.refined import Refined

    fields = Refined.model_fields
    assert "disposition" not in fields, (
        "FR-303 violation: Refined.disposition would let the AI decide pass/fail."
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_refined_round_trip tests/test_schemas_round_trip.py::test_refined_has_no_disposition_field_fr303 -v`
Expected: 2 FAILED — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/refined.py`:

```python
"""AI orchestrator output. Source: ARCH §4.2.6, PRD FR-303.

FR-303 invariant: this model declares **no top-level ``disposition`` field**.
The deterministic Rule Engine produces dispositions; the orchestrator only
enriches reasoning, disambiguates borderline brand matches, or reconciles OCR.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Refined(BaseModel):
    """Orchestrator output for one evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    task: Literal[
        "brand_borderline",
        "reasoning_enrichment",
        "ocr_reconciliation",
    ] | None = None
    text: str | None = None
    # NB: ``model_disposition`` is the model's *suggestion*, not the verdict.
    # Allowed values exclude ``fail`` so the model cannot recommend a fail flip.
    model_disposition: Literal["pass", "needs_review"] | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_refined_round_trip tests/test_schemas_round_trip.py::test_refined_has_no_disposition_field_fr303 -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/refined.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add Refined orchestrator schema with FR-303 invariant"
```

---

## Task 9: app/schemas/audit.py — AuditRecord + PerRuleTraceEntry + OverrideEntry (D-018)

**Files:**
- Create: `app/schemas/audit.py`
- Modify: `tests/test_schemas_round_trip.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_audit_record_round_trip() -> None:
    from datetime import datetime, timezone

    from app.schemas.audit import AuditRecord, OverrideEntry, PerRuleTraceEntry

    rec = AuditRecord(
        evaluation_id="00000000-0000-4000-8000-000000000001",
        rule_set_version="0.1.0",
        model_version="gpt-4o-2024-08-06",
        prompt_version="v1",
        input_hash="0" * 64,
        output_hash="1" * 64,
        started_at=datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 4, 1, 12, 0, 1, 230000, tzinfo=timezone.utc),
        per_rule_trace=(
            PerRuleTraceEntry(
                rule_id="common.brand.exact_or_normalized",
                disposition="pass",
                evidence_ref="crop-001",
            ),
        ),
        overrides=(),
    )
    rec2 = AuditRecord.model_validate_json(rec.model_dump_json())
    assert rec2 == rec


def test_per_rule_trace_entry_has_no_duration_ms_d018() -> None:
    """ADR D-018: per-rule durations live in metrics, not in audit."""
    from app.schemas.audit import PerRuleTraceEntry

    fields = PerRuleTraceEntry.model_fields
    assert "duration_ms" not in fields, (
        "D-018 violation: per-rule duration belongs in app.schemas.metrics, "
        "not in audit_trail.per_rule_trace[]."
    )
    assert set(fields.keys()) == {"rule_id", "disposition", "evidence_ref"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_audit_record_round_trip tests/test_schemas_round_trip.py::test_per_rule_trace_entry_has_no_duration_ms_d018 -v`
Expected: 2 FAILED.

- [ ] **Step 3: Implement the file**

Create `app/schemas/audit.py`:

```python
"""In-memory audit-trail models. Source: ARCH §6.8; ADR D-018.

D-018 split: per-rule durations live in ``app.schemas.metrics``;
``audit_trail.per_rule_trace[]`` carries only audit-relevant fields
(rule_id, disposition, evidence_ref).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PerRuleTraceEntry(BaseModel):
    """One entry in the audit-trail per-rule trace.

    D-018: contains audit-relevant fields only — no telemetry.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    disposition: Literal["pass", "fail", "needs_review", "not_applicable"]
    evidence_ref: str


class OverrideEntry(BaseModel):
    """Reviewer override recorded in the audit trail (FR-801)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    field_name: str
    original_disposition: Literal["pass", "fail", "needs_review"]
    applied_disposition: Literal["pass", "fail", "needs_review"]
    reason_code: str
    justification_text: str | None = None
    reviewer_id: str
    timestamp: datetime


class AuditRecord(BaseModel):
    """Audit-trail object surfaced in PRD §6.2 ``audit_trail``.

    Source: ARCH §6.8.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    rule_set_version: str
    model_version: str | None = None
    prompt_version: str | None = None
    input_hash: str
    output_hash: str
    started_at: datetime
    completed_at: datetime
    per_rule_trace: tuple[PerRuleTraceEntry, ...]
    overrides: tuple[OverrideEntry, ...] = ()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_audit_record_round_trip tests/test_schemas_round_trip.py::test_per_rule_trace_entry_has_no_duration_ms_d018 -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/audit.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add AuditRecord with D-018 audit/telemetry split"
```

---

## Task 10: app/schemas/metrics.py — Metrics + PerRuleDurationEntry

**Files:**
- Create: `app/schemas/metrics.py`
- Modify: `tests/test_schemas_round_trip.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_metrics_round_trip() -> None:
    from app.schemas.metrics import Metrics, PerRuleDurationEntry

    m = Metrics(
        total_duration_ms=1230,
        per_rule_durations_ms=(
            PerRuleDurationEntry(rule_id="common.brand.exact_or_normalized", duration_ms=8),
        ),
        vision_duration_ms=720,
        orchestrator_duration_ms=480,
    )
    m2 = Metrics.model_validate_json(m.model_dump_json())
    assert m2 == m
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_metrics_round_trip -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/metrics.py`:

```python
"""Per-evaluation telemetry. Sibling of audit_trail per ADR D-018.

Source: ARCH §6.8 note + §13.5 audit/telemetry split; PRD §6.2 ``metrics`` block.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PerRuleDurationEntry(BaseModel):
    """One per-rule wall-clock duration entry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    duration_ms: int


class Metrics(BaseModel):
    """Telemetry block on the disposition envelope (PRD §6.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_duration_ms: int
    per_rule_durations_ms: tuple[PerRuleDurationEntry, ...]
    vision_duration_ms: int
    orchestrator_duration_ms: int
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_metrics_round_trip -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/metrics.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add Metrics + PerRuleDurationEntry (D-018 sibling block)"
```

---

## Task 11: app/schemas/rules.py — RuleSet, RuleDefinition, MatchPolicy, ReasonCodeEntry, AssetRef, DecisionTable

**Files:**
- Create: `app/schemas/rules.py`
- Modify: `tests/test_schemas_round_trip.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_rule_set_round_trip() -> None:
    from app.schemas.expected import BeverageClass
    from app.schemas.rejection import Severity
    from app.schemas.rules import (
        AssetRef,
        DecisionTable,
        MatchPolicy,
        ReasonCodeEntry,
        RuleDefinition,
        RuleSet,
    )

    rule = RuleDefinition(
        rule_id="spirits.alcohol.tolerance_band",
        cfr_citation="27 CFR §5.65(c)",
        applies_to_classes=(BeverageClass.SPIRITS,),
        reason_code="ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND",
        severity=Severity.REJECT,
        match_policy=MatchPolicy.TOLERANCE,
        validator="abv_band",
        evidence_required=("abv",),
        confidence_floor=0.5,
        parameters={"tolerance_pp": 0.3, "arithmetic": "decimal"},
        tolerance=None,
        decision_table=None,
        decision_table_ref=None,
        asset=None,
        effective_date="2022-02-09",
        supersedes=(),
        rule_pack_version="0.1.0",
        rule_pack="spirits",
        test_fixtures=("F-SPIRITS-ALC-36-PASS-01",),
        disabled=False,
        notes=None,
    )

    rs = RuleSet(
        version="0.1.0",
        effective_date="2026-04-01",
        rules=(rule,),
        reason_codes={
            "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND": ReasonCodeEntry(
                description="ABV outside the regulatory tolerance band.",
                cfr_anchors=("27 CFR §5.65(c)",),
                severity=Severity.REJECT,
            ),
        },
        assets={
            "warning_16_21": AssetRef(
                path="assets/warnings/govt_warning_16_21.txt",
                sha256="0" * 64,
            ),
        },
        decision_tables={
            "cpi_16_22_a_4": DecisionTable(
                interpolation="none",
                entries=({"min_ml": 50, "max_ml": 100, "cpi": 0.4},),
            ),
        },
    )
    rs2 = RuleSet.model_validate_json(rs.model_dump_json())
    assert rs2 == rs


def test_match_policy_enum_values() -> None:
    from app.schemas.rules import MatchPolicy

    assert MatchPolicy("tolerance") is MatchPolicy.TOLERANCE
    assert MatchPolicy("verbatim_hash") is MatchPolicy.VERBATIM_HASH
    assert MatchPolicy("fuzzy") is MatchPolicy.FUZZY
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_rule_set_round_trip tests/test_schemas_round_trip.py::test_match_policy_enum_values -v`
Expected: 2 FAILED.

- [ ] **Step 3: Implement the file**

Create `app/schemas/rules.py`:

```python
"""Canonical declaration of rule-pack types. Source: ARCH §6.6; D-014.

These types live here (not in ``app/rules/models.py``) so they can be referenced
by the data-shape boundary used across epochs. ``app/rules/models.py`` (E2)
re-exports them for namespace ergonomics; the import-identity assertion that
``from app.schemas.rules import RuleSet is from app.rules.models import RuleSet``
lands with the E2 re-export, not in this epoch.

**E2 re-export contract (forward note):** ``app/rules/models.py`` MUST use
``from app.schemas.rules import RuleSet as RuleSet`` style (re-binding the
class object) — NOT a redeclaration — so the ``is``-identity AC #9 holds.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.expected import BeverageClass
from app.schemas.rejection import Severity


class MatchPolicy(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    TOLERANCE = "tolerance"
    VERBATIM_HASH = "verbatim_hash"
    LOOKUP = "lookup"
    REGEX = "regex"
    LAYOUT = "layout"


class ReasonCodeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    description: str
    cfr_anchors: tuple[str, ...]
    severity: Severity


class AssetRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str


class DecisionTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    interpolation: Literal["none", "linear"] = "none"
    entries: tuple[dict[str, Any], ...]


class RuleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    cfr_citation: str
    applies_to_classes: tuple[BeverageClass, ...]
    reason_code: str
    severity: Severity
    match_policy: MatchPolicy
    validator: str
    evidence_required: tuple[str, ...]
    confidence_floor: float = Field(default=0.5, ge=0.0, le=1.0)
    parameters: dict[str, Any] = Field(default_factory=dict)
    tolerance: dict[str, Any] | None = None
    decision_table: dict[str, Any] | None = None
    decision_table_ref: str | None = None
    asset: dict[str, Any] | None = None
    effective_date: str
    supersedes: tuple[str, ...] = ()
    rule_pack_version: str | None = None
    rule_pack: str | None = None
    test_fixtures: tuple[str, ...]
    disabled: bool = False
    notes: str | None = None


class RuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    effective_date: str
    rules: tuple[RuleDefinition, ...]
    reason_codes: dict[str, ReasonCodeEntry]
    assets: dict[str, AssetRef]
    decision_tables: dict[str, DecisionTable]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_rule_set_round_trip tests/test_schemas_round_trip.py::test_match_policy_enum_values -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/rules.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add canonical RuleSet/RuleDefinition + supporting types"
```

---

## Task 12: app/schemas/batch.py — BatchInFlightState + BatchItem + ItemState

**Files:**
- Create: `app/schemas/batch.py`
- Modify: `tests/test_schemas_round_trip.py` (add case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_batch_state_round_trip() -> None:
    from datetime import datetime, timezone

    from app.schemas.batch import BatchInFlightState, BatchItem, ItemState

    item = BatchItem(
        label_id="label-001",
        application_ref="app-001",
        state=ItemState.QUEUED,
        result=None,
        enqueued_at=datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    state = BatchInFlightState(
        batch_id="00000000-0000-4000-8000-00000000b001",
        agent_id="session-abc",
        items=(item,),
        current_index=0,
        lookahead_k=3,
    )
    s2 = BatchInFlightState.model_validate_json(state.model_dump_json())
    assert s2 == state


def test_item_state_transitions_documented() -> None:
    from app.schemas.batch import ItemState

    expected = {
        ItemState.QUEUED, ItemState.PROCESSING, ItemState.READY,
        ItemState.PRESENTED, ItemState.REVIEWED, ItemState.DISPOSED,
        ItemState.FAILED,
    }
    assert set(ItemState) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_batch_state_round_trip tests/test_schemas_round_trip.py::test_item_state_transitions_documented -v`
Expected: 2 FAILED.

- [ ] **Step 3: Implement the file**

Create `app/schemas/batch.py`:

```python
"""Batch-processor session-scoped state. Source: ARCH §6.7."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ItemState(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    PRESENTED = "presented"
    REVIEWED = "reviewed"
    DISPOSED = "disposed"
    FAILED = "failed"


class BatchItem(BaseModel):
    """Per-label state machine entry. Source: ARCH §6.7."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label_id: str
    application_ref: str
    state: ItemState
    result: dict[str, Any] | None = None
    enqueued_at: datetime
    failed_reason: str | None = None


class BatchInFlightState(BaseModel):
    """Session-scoped state for an in-progress batch.

    The actual ``recent_dispositions`` deque and ``calls`` ring buffer are
    in-memory mutable structures held outside the Pydantic envelope (E6 wires
    them); this model captures only the serializable subset.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    batch_id: str
    agent_id: str
    items: tuple[BatchItem, ...]
    current_index: int = 0
    lookahead_k: int = Field(default=3, ge=1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_batch_state_round_trip tests/test_schemas_round_trip.py::test_item_state_transitions_documented -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/batch.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add BatchInFlightState + BatchItem + ItemState enum"
```

---

## Task 13: app/schemas/calls.py — CallRecord

**Files:**
- Create: `app/schemas/calls.py`
- Modify: `tests/test_schemas_round_trip.py` (add case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_call_record_round_trip() -> None:
    from datetime import datetime, timezone

    from app.schemas.calls import CallRecord

    rec = CallRecord(
        ts=datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
        batch_id="b1",
        label_id="l1",
        stage="orch.brand_disambig",
        request={"prompt_hash": "abc", "params": {"temperature": 0}},
        response={"text": "match"},
        latency_ms=420,
        model="gpt-4o-2024-08-06",
        provider="openai",
        prompt_version="v1",
        output_hash="0" * 64,
    )
    rec2 = CallRecord.model_validate_json(rec.model_dump_json())
    assert rec2 == rec
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_call_record_round_trip -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/calls.py`:

```python
"""Per-LLM/vision-call ring-buffer entry. Source: ARCH §6.9."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


CallStage = Literal[
    "vision.paddleocr",
    "vision.swt",
    "vision.gpt4o_tiebreak",
    "rule.evaluate",
    "orch.brand_disambig",
    "orch.reasoning_enrich",
    "orch.ocr_reconcile",
]


class CallRecord(BaseModel):
    """Shape stored in ``BatchInFlightState.calls`` ring buffer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ts: datetime
    batch_id: str
    label_id: str
    stage: CallStage
    request: dict[str, Any]
    response: dict[str, Any]
    latency_ms: int
    model: str | None = None
    provider: Literal["openai", "anthropic", "local.paddleocr"] | None = None
    prompt_version: str | None = None
    output_hash: str
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_call_record_round_trip -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/calls.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add CallRecord ring-buffer entry"
```

---

## Task 14: app/schemas/wire/application.py — PRD §6.1 envelope (round-trip golden)

**Files:**
- Create: `app/schemas/wire/__init__.py` (empty)
- Create: `app/schemas/wire/application.py`
- Modify: `tests/test_schemas_round_trip.py` (add case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_application_envelope_round_trip(wire_fixtures_dir) -> None:
    import json

    from app.schemas.wire.application import ApplicationEnvelope

    raw = json.loads((wire_fixtures_dir / "application.json").read_text())
    env = ApplicationEnvelope.model_validate(raw)
    rt = json.loads(env.model_dump_json(exclude_none=False))
    # Compare on the keys present in the input — model_dump emits canonical order;
    # round-trip means input keys/values survive a parse + dump cycle.
    assert rt["permit_number"] == raw["permit_number"]
    assert rt["brand_name"] == raw["brand_name"]
    assert rt["labels"][0]["face_tag"] == raw["labels"][0]["face_tag"]


def test_application_envelope_rejects_extra_keys() -> None:
    import pytest
    from pydantic import ValidationError

    from app.schemas.wire.application import ApplicationEnvelope

    with pytest.raises(ValidationError):
        ApplicationEnvelope.model_validate({"permit_number": "x", "rogue_key": 1})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_application_envelope_round_trip tests/test_schemas_round_trip.py::test_application_envelope_rejects_extra_keys -v`
Expected: 2 FAILED — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/wire/__init__.py` (empty):

```python
```

Create `app/schemas/wire/application.py`:

```python
"""PRD §6.1 application-input envelope.

NFR-SEC-003: ``extra='forbid'`` — unknown keys are rejected at the boundary.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")

    street: str
    city: str
    state: str
    zip: str
    country: str


class Applicant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    address: Address
    mailing_address: Address | None = None


class Formula(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ttb_formula_id: str
    approval_date: date


class TypeOfApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cola: bool
    exemption: bool
    exemption_state: str | None = None
    distinctive_bottle: bool
    bottle_capacity: str | None = None
    resubmission: bool
    prior_ttb_id: str | None = None


class LabelDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width_px: int
    height_px: int
    dpi: int


class LabelRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_ref: str
    face_tag: Literal["front", "back", "neck", "side"]
    dimensions: LabelDimensions


class ApplicationEnvelope(BaseModel):
    """PRD §6.1 application-input contract.

    Source: TTB Form 5100.31 rev. 04/2023 items 1–18 + ``labels[]``.
    """

    model_config = ConfigDict(extra="forbid")

    rep_id: str | None = None
    permit_number: str
    source_of_product: Literal["domestic", "imported"]
    serial_number: str = Field(max_length=6)
    type_of_product: Literal["wine", "distilled_spirits", "malt_beverages"]
    brand_name: str
    fanciful_name: str | None = None
    applicant: Applicant
    formula: Formula | None = None
    grape_varietals: tuple[str, ...] | None = None
    wine_appellation: str | None = None
    phone: str
    email: str | None = None
    type_of_application: TypeOfApplication
    blown_branded_embossed_text: str | None = None
    date_of_application: date
    applicant_signature: str | None = None
    applicant_print_name: str
    perjury_attested: Literal[True]
    labels: tuple[LabelRef, ...]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_application_envelope_round_trip tests/test_schemas_round_trip.py::test_application_envelope_rejects_extra_keys -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/wire/__init__.py app/schemas/wire/application.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add PRD §6.1 ApplicationEnvelope wire schema"
```

---

## Task 15: app/schemas/wire/disposition.py — PRD §6.2 envelope

**Files:**
- Create: `app/schemas/wire/disposition.py`
- Modify: `tests/test_schemas_round_trip.py` (add case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_disposition_envelope_round_trip(wire_fixtures_dir) -> None:
    import json

    from app.schemas.wire.disposition import DispositionEnvelope

    raw = json.loads((wire_fixtures_dir / "disposition.json").read_text())
    env = DispositionEnvelope.model_validate(raw)
    dumped = json.loads(env.model_dump_json())
    assert dumped["disposition"] == raw["disposition"]
    assert dumped["audit_trail"]["evaluation_id"] == raw["audit_trail"]["evaluation_id"]
    # D-018: audit_trail.per_rule_trace[] entries must NOT carry duration_ms.
    for entry in dumped["audit_trail"]["per_rule_trace"]:
        assert "duration_ms" not in entry
    # D-018: durations live in the metrics block.
    assert "metrics" in dumped
    assert dumped["metrics"]["per_rule_durations_ms"][0]["duration_ms"] == 8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_disposition_envelope_round_trip -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/wire/disposition.py`:

```python
"""PRD §6.2 disposition-output envelope. ADR D-018: audit + metrics split.

**D-017 confidence aggregation note.** ARCH §6 + ADR D-017 specify that
``disposition_confidence.numeric`` is the **min** over per-field
``field_confidence.numeric``. The aggregation builder (a method on
``ConfidenceBand`` or a free helper) is **owned by E5** (Application Service
assembly). E1 only ships the type carrying the values; the algorithm fires
during disposition assembly, not at parse time.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.audit import AuditRecord
from app.schemas.metrics import Metrics


Band = Literal["high", "medium", "low"]
Disposition = Literal["pass", "fail", "needs_review"]


class ConfidenceBand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    band: Band
    numeric: float = Field(ge=0.0, le=1.0)


class FieldEvidenceWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bbox: tuple[int, int, int, int]
    crop_ref: str
    extraction_confidence: float = Field(ge=0.0, le=1.0)


class RuleFindingWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    cfr_citation: str
    disposition: Literal["pass", "fail", "needs_review"]
    reason_code: str
    plain_language_explanation: str


class AISuggestionWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    present: bool
    task: Literal[
        "brand_borderline",
        "reasoning_enrichment",
        "ocr_reconciliation",
    ] | None = None
    text: str | None = None
    model_disposition: Literal["pass", "needs_review"] | None = None


class FieldFindingWire(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: Literal[
        "brand_name",
        "class_type",
        "alcohol_content",
        "net_contents",
        "warning",
        "name_address",
        "country_of_origin",
    ]
    extracted_value: str
    expected_value: str
    evidence: FieldEvidenceWire
    rule_findings: tuple[RuleFindingWire, ...]
    ai_suggestion: AISuggestionWire
    field_confidence: ConfidenceBand


class DispositionEnvelope(BaseModel):
    """PRD §6.2 outbound envelope.

    D-018: ``audit_trail.per_rule_trace[]`` does NOT carry ``duration_ms``;
    per-rule durations live in the sibling ``metrics`` block.
    """

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str
    label_ref: str
    disposition: Disposition
    disposition_confidence: ConfidenceBand
    fields: tuple[FieldFindingWire, ...]
    audit_trail: AuditRecord
    metrics: Metrics
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_disposition_envelope_round_trip -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/wire/disposition.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add PRD §6.2 DispositionEnvelope (D-018 audit/metrics split)"
```

---

## Task 16: app/schemas/wire/batch.py — PRD §6.3 envelope

**Files:**
- Create: `app/schemas/wire/batch.py`
- Modify: `tests/test_schemas_round_trip.py` (add case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_batch_envelope_round_trip(wire_fixtures_dir) -> None:
    import json

    from app.schemas.wire.batch import BatchEnvelope

    raw = json.loads((wire_fixtures_dir / "batch.json").read_text())
    env = BatchEnvelope.model_validate(raw)
    dumped = json.loads(env.model_dump_json())
    assert dumped["batch_id"] == raw["batch_id"]
    assert len(dumped["items"]) == len(raw["items"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_batch_envelope_round_trip -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/wire/batch.py`:

```python
"""PRD §6.3 batch envelope contract."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BatchItemRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_ref: str
    application_ref: str


class BatchEnvelope(BaseModel):
    """PRD §6.3 batch envelope. ``agent_id`` is structurally present but
    single-agent in MVP per T6 §Q6.7."""

    model_config = ConfigDict(extra="forbid")

    batch_id: str
    agent_id: str
    submitted_at: datetime
    items: tuple[BatchItemRef, ...]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_batch_envelope_round_trip -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/wire/batch.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add PRD §6.3 BatchEnvelope wire schema"
```

---

## Task 17: app/schemas/wire/error.py — PRD §6.4 envelope

**Files:**
- Create: `app/schemas/wire/error.py`
- Modify: `tests/test_schemas_round_trip.py` (add case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_schemas_round_trip.py`:

```python
def test_error_envelope_round_trip(wire_fixtures_dir) -> None:
    import json

    from app.schemas.wire.error import ErrorEnvelope

    raw = json.loads((wire_fixtures_dir / "error.json").read_text())
    env = ErrorEnvelope.model_validate(raw)
    dumped = json.loads(env.model_dump_json())
    assert dumped["error_kind"] == raw["error_kind"]
    assert dumped["reason_code"] == raw["reason_code"]
    assert dumped["details"]["expected_inputs"] == ["brand_name"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_error_envelope_round_trip -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the file**

Create `app/schemas/wire/error.py`:

```python
"""PRD §6.4 error contract."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ErrorEnvelope(BaseModel):
    """PRD §6.4 boundary error envelope.

    Reason codes follow the T3 §Q3.10 taxonomy
    (``BIN.SUB.SPECIFIC[.QUALIFIER]`` grammar).
    """

    model_config = ConfigDict(extra="forbid")

    error_kind: Literal["rejected_input", "engine_failure", "partial_completion"]
    reason_code: str
    message: str
    details: dict[str, Any]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_schemas_round_trip.py::test_error_envelope_round_trip -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/wire/error.py tests/test_schemas_round_trip.py
git commit -m "feat(e1): add PRD §6.4 ErrorEnvelope wire schema"
```

---

## Task 18: app/logging/otel_genai.py — JSON-line formatter with OTel GenAI attribute names

**Files:**
- Create: `app/logging/__init__.py` (empty placeholder; T21 fills it)
- Create: `app/logging/otel_genai.py`
- Create: `tests/test_logging_emission.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_logging_emission.py`:

```python
"""Logging subsystem: formatter + redaction + configure_logging."""
from __future__ import annotations

import json
import logging


def test_otel_genai_formatter_emits_one_json_line() -> None:
    from app.logging.otel_genai import OtelGenAIFormatter

    formatter = OtelGenAIFormatter()
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="evaluation_complete",
        args=None,
        exc_info=None,
    )
    record.evaluation_id = "00000000-0000-4000-8000-000000000001"
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["msg"] == "evaluation_complete"
    assert parsed["level"] == "INFO"
    assert parsed["evaluation_id"] == "00000000-0000-4000-8000-000000000001"
    assert "ts" in parsed


def test_otel_genai_formatter_uses_gen_ai_attribute_names() -> None:
    """ARCH §13.1: LLM-call log lines use OpenTelemetry GenAI conventions."""
    from app.logging.otel_genai import OtelGenAIFormatter

    formatter = OtelGenAIFormatter()
    record = logging.LogRecord(
        name="app", level=logging.INFO, pathname=__file__, lineno=1,
        msg="llm_call", args=None, exc_info=None,
    )
    setattr(record, "gen_ai.request.model", "gpt-4o-2024-08-06")
    setattr(record, "gen_ai.response.model", "gpt-4o-2024-08-06")
    setattr(record, "gen_ai.usage.input_tokens", 1234)
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["gen_ai.request.model"] == "gpt-4o-2024-08-06"
    assert parsed["gen_ai.usage.input_tokens"] == 1234
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_logging_emission.py::test_otel_genai_formatter_emits_one_json_line tests/test_logging_emission.py::test_otel_genai_formatter_uses_gen_ai_attribute_names -v`
Expected: 2 FAILED — module missing.

- [ ] **Step 3: Implement the file**

Create `app/logging/__init__.py` (empty for now; T21 fills it):

```python
```

Create `app/logging/otel_genai.py`:

```python
"""JSON-line log formatter using OpenTelemetry GenAI semantic-convention
attribute names. Source: ARCH §13.1, S3 Q13.

Future ``OTEL_EXPORTER_OTLP_ENDPOINT`` env var flips emission to a real OTel
collector without code changes.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


# Cross-cutting fields per ARCH §13.1 + T3 §Q3.10.
CROSS_CUTTING_FIELDS = (
    "evaluation_id",
    "batch_id",
    "label_id",
    "reason_code",
    "duration_ms",
    "rule_set_version",
    "model_version",
    "prompt_version",
    "error_class",
)

# OpenTelemetry GenAI semantic-convention attribute names. Records may carry
# any subset of these via ``LogRecord`` attributes; the formatter passes them
# through verbatim so attribute names follow the OTel spec.
OTEL_GENAI_ATTRIBUTES = (
    "gen_ai.request.model",
    "gen_ai.response.model",
    "gen_ai.usage.input_tokens",
    "gen_ai.usage.output_tokens",
    "gen_ai.system",
    "gen_ai.operation.name",
)


class OtelGenAIFormatter(logging.Formatter):
    """Emit one JSON line per log record, with OTel GenAI attribute names."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        for attr in CROSS_CUTTING_FIELDS:
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value
        for attr in OTEL_GENAI_ATTRIBUTES:
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value
        if record.exc_info:
            payload["exc_class"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, separators=(",", ":"), default=str)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_logging_emission.py::test_otel_genai_formatter_emits_one_json_line tests/test_logging_emission.py::test_otel_genai_formatter_uses_gen_ai_attribute_names -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/logging/__init__.py app/logging/otel_genai.py tests/test_logging_emission.py
git commit -m "feat(e1): add OtelGenAIFormatter JSON-line log formatter"
```

---

## Task 19: app/logging/redaction.py — NFR-SEC-004 redaction filter

**Files:**
- Create: `app/logging/redaction.py`
- Modify: `tests/test_logging_emission.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_logging_emission.py`:

```python
def test_redaction_filter_strips_application_content_and_label_bytes() -> None:
    from app.logging.redaction import RedactionFilter

    filter_ = RedactionFilter()
    record = logging.LogRecord(
        name="app", level=logging.INFO, pathname=__file__, lineno=1,
        msg="leakage_attempt", args=None, exc_info=None,
    )
    record.application_content = {"brand_name": "secret"}
    record.label_bytes = b"\xff\xd8\xff..."
    record.extracted_text = "verbatim contents that should not log"
    record.evaluation_id = "00000000-0000-4000-8000-000000000001"
    record.reason_code = "ENGINE.OK.NONE"
    assert filter_.filter(record) is True  # filter does not drop the record
    assert not hasattr(record, "application_content") or record.application_content is None
    assert not hasattr(record, "label_bytes") or record.label_bytes is None
    assert not hasattr(record, "extracted_text") or record.extracted_text is None
    # Preserved fields
    assert record.evaluation_id == "00000000-0000-4000-8000-000000000001"
    assert record.reason_code == "ENGINE.OK.NONE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_logging_emission.py::test_redaction_filter_strips_application_content_and_label_bytes -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Implement the file**

Create `app/logging/redaction.py`:

```python
"""NFR-SEC-004 redaction filter. Source: ARCH §12.4.

Drops at emission time:
- Submitted application content (the JSON body in toto).
- Label artwork bytes.
- Extracted field values verbatim.

Preserves: evaluation_id, batch_id, label_id, reason_code, duration_ms,
rule_set_version, model_version, prompt_version, error_class.
"""
from __future__ import annotations

import logging


REDACTED_FIELDS = (
    "application_content",
    "application_body",
    "label_bytes",
    "image_bytes",
    "extracted_text",
    "extracted_value",
    "verbatim_text",
)


class RedactionFilter(logging.Filter):
    """Strip configured fields from every emitted record before formatting."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        for attr in REDACTED_FIELDS:
            if hasattr(record, attr):
                setattr(record, attr, None)
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_logging_emission.py::test_redaction_filter_strips_application_content_and_label_bytes -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/logging/redaction.py tests/test_logging_emission.py
git commit -m "feat(e1): add NFR-SEC-004 RedactionFilter for log-record fields"
```

---

## Task 20: app/logging/ring_buffer.py — CallRecord deque scaffolding

**Files:**
- Create: `app/logging/ring_buffer.py`
- Modify: `tests/test_logging_emission.py` (add cases)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_logging_emission.py`:

```python
def test_call_record_ring_buffer_default_maxlen_is_200() -> None:
    from app.logging.ring_buffer import new_call_ring_buffer

    rb = new_call_ring_buffer()
    assert rb.maxlen == 200
    assert len(rb) == 0


def test_call_record_ring_buffer_evicts_fifo_at_capacity() -> None:
    from app.logging.ring_buffer import new_call_ring_buffer

    rb = new_call_ring_buffer(maxlen=3)
    rb.append("a")
    rb.append("b")
    rb.append("c")
    rb.append("d")  # evicts "a"
    assert list(rb) == ["b", "c", "d"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_logging_emission.py::test_call_record_ring_buffer_default_maxlen_is_200 tests/test_logging_emission.py::test_call_record_ring_buffer_evicts_fifo_at_capacity -v`
Expected: 2 FAILED — module missing.

- [ ] **Step 3: Implement the file**

Create `app/logging/ring_buffer.py`:

```python
"""``CallRecord`` deque scaffolding. Source: ARCH §6.7 + §6.9.

The actual recording is wired in E3/E4 when seam producers exist; E1 only
ships the constructor so other layers can hold a reference at startup.
"""
from __future__ import annotations

from collections import deque
from typing import Any


DEFAULT_MAXLEN = 200


def new_call_ring_buffer(maxlen: int = DEFAULT_MAXLEN) -> deque[Any]:
    """Return an empty bounded deque for ``CallRecord`` entries (FIFO eviction)."""

    return deque(maxlen=maxlen)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_logging_emission.py::test_call_record_ring_buffer_default_maxlen_is_200 tests/test_logging_emission.py::test_call_record_ring_buffer_evicts_fifo_at_capacity -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/logging/ring_buffer.py tests/test_logging_emission.py
git commit -m "feat(e1): add new_call_ring_buffer (deque maxlen=200)"
```

---

## Task 21: app/logging/__init__.py — configure_logging entry point

**Files:**
- Modify: `app/logging/__init__.py`
- Modify: `tests/test_logging_emission.py` (add case)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_logging_emission.py`:

```python
def test_configure_logging_wires_formatter_and_redaction(capsys) -> None:
    import logging as stdlib_logging

    from app.logging import configure_logging

    # Caller-provided settings shim — config.py is created in T22.
    class _StubSettings:
        log_level: str = "INFO"

    configure_logging(_StubSettings())
    logger = stdlib_logging.getLogger("app.test")
    logger.info("healthz_invoked", extra={"evaluation_id": "evt-001"})
    captured = capsys.readouterr()
    assert captured.out.count("\n") == 1
    import json

    parsed = json.loads(captured.out.strip())
    assert parsed["msg"] == "healthz_invoked"
    assert parsed["evaluation_id"] == "evt-001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_logging_emission.py::test_configure_logging_wires_formatter_and_redaction -v`
Expected: FAIL — `configure_logging` not exported.

- [ ] **Step 3: Implement the file**

Replace `app/logging/__init__.py`:

```python
"""Logging package entry point. Source: ARCH §13.1."""
from __future__ import annotations

import logging
import sys
from typing import Any

from app.logging.otel_genai import OtelGenAIFormatter
from app.logging.redaction import RedactionFilter

__all__ = ["configure_logging"]


def configure_logging(settings: Any) -> None:
    """Wire Python ``logging`` to JSON-line stdout with redaction.

    Idempotent: re-invoking replaces the root handler set so test runs do not
    accumulate duplicate emissions.
    """

    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(OtelGenAIFormatter())
    handler.addFilter(RedactionFilter())
    level_name = getattr(settings, "log_level", "INFO")
    handler.setLevel(level_name)
    root.addHandler(handler)
    root.setLevel(level_name)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_logging_emission.py::test_configure_logging_wires_formatter_and_redaction -v`
Expected: 1 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/logging/__init__.py tests/test_logging_emission.py
git commit -m "feat(e1): add configure_logging() entry point wiring formatter+filter"
```

---

## Task 22: app/config.py — Pydantic Settings (single source of truth for env vars)

**Files:**
- Create: `app/config.py`
- Create: `tests/test_config_load.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config_load.py`:

```python
"""Settings: env-var loading, defaults, missing-required errors."""
from __future__ import annotations

import os
from contextlib import contextmanager

import pytest


@contextmanager
def _env(**overrides: str | None):
    original = {k: os.environ.get(k) for k in overrides}
    try:
        for k, v in overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_settings_defaults_when_only_required_provided() -> None:
    from app.config import Settings

    with _env(
        OPENAI_API_KEY="sk-test",
        ANTHROPIC_API_KEY=None,
        VISION_MODE=None,
        ORCHESTRATOR_BACKEND=None,
        LOOKAHEAD_K=None,
        DEV_MODE=None,
        OTEL_EXPORTER_OTLP_ENDPOINT=None,
        LLM_MODEL_SNAPSHOT=None,
        PROMPT_VERSION=None,
    ):
        s = Settings()
        assert s.vision_mode == "auto"
        assert s.orchestrator_backend == "openai"
        assert s.lookahead_k == 3
        assert s.dev_mode is False
        assert s.llm_model_snapshot == "gpt-4o-2024-08-06"
        assert s.prompt_version == "v1"


def test_settings_lookahead_k_int_coercion() -> None:
    from app.config import Settings

    with _env(OPENAI_API_KEY="sk-test", LOOKAHEAD_K="5"):
        s = Settings()
        assert s.lookahead_k == 5


def test_settings_dev_mode_truthy_strings() -> None:
    from app.config import Settings

    with _env(OPENAI_API_KEY="sk-test", DEV_MODE="1"):
        assert Settings().dev_mode is True
    with _env(OPENAI_API_KEY="sk-test", DEV_MODE="true"):
        assert Settings().dev_mode is True
    with _env(OPENAI_API_KEY="sk-test", DEV_MODE=""):
        assert Settings().dev_mode is False


def test_settings_rejects_invalid_vision_mode() -> None:
    from pydantic import ValidationError

    from app.config import Settings

    with _env(OPENAI_API_KEY="sk-test", VISION_MODE="banana"):
        with pytest.raises(ValidationError):
            Settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_config_load.py -v`
Expected: 4 FAILED — `app.config` missing.

- [ ] **Step 3: Implement the file**

Create `app/config.py`:

```python
"""Pydantic Settings — single source of truth for the env-var inventory.

ARCH §12.2: every secret name is read here and **only** here. The grep
enforcement test (``tests/test_secrets_grep.py``) asserts no other module
references ``os.environ`` directly.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_TRUTHY = frozenset({"1", "true", "yes", "on"})


class Settings(BaseSettings):
    """Process-level configuration loaded from environment variables.

    Source: ARCH §12.2 (env-var inventory).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Vision selection (D-015).
    vision_mode: Literal["local", "cloud", "auto"] = Field(default="auto", alias="VISION_MODE")

    # Orchestrator selection (D-021).
    orchestrator_backend: Literal["openai", "anthropic"] = Field(
        default="openai", alias="ORCHESTRATOR_BACKEND"
    )

    # Secrets — required at request time when the corresponding seam is invoked.
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Pinned model + prompt versions (D-020).
    llm_model_snapshot: str = Field(default="gpt-4o-2024-08-06", alias="LLM_MODEL_SNAPSHOT")
    prompt_version: str = Field(default="v1", alias="PROMPT_VERSION")

    # Batch lookahead window.
    lookahead_k: int = Field(default=3, ge=1, alias="LOOKAHEAD_K")

    # Dev-only routes (D-019). Empty string and unset both coerce to False.
    dev_mode: bool = Field(default=False, alias="DEV_MODE")

    # Future OTel collector endpoint (S3 Q13).
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )

    # Logging level (L2-added; flag for ARCH §12.2 amendment).
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("dev_mode", mode="before")
    @classmethod
    def _coerce_dev_mode(cls, value: object) -> bool:
        """Empty string / None / falsy strings → False; truthy strings → True."""
        if value is None or value == "":
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in _TRUTHY
        return bool(value)

    @classmethod
    def from_env(cls) -> "Settings":
        """Convenience factory mandated by L1 §2.2; equivalent to ``cls()``."""
        return cls()

    @property
    def app_version(self) -> str:
        return "0.1.0"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_config_load.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config_load.py
git commit -m "feat(e1): add Settings (Pydantic Settings) for env-var inventory"
```

---

## Task 23: app/deps.py — DI container with placeholder seam providers

**Files:**
- Create: `app/deps.py`
- Create: `tests/test_dependency_injection.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_dependency_injection.py`:

```python
"""DI container: VisionExtractor / Orchestrator placeholder providers.

Per L1 §4 AC #8: providers raise NotImplementedError("seam not wired in E1")
on any path that would invoke ``VisionExtractor.extract()`` or
``Orchestrator.refine()``.
"""
from __future__ import annotations

import os

import pytest


def _settings_with(**overrides: str | None):
    from app.config import Settings

    original = {k: os.environ.get(k) for k in overrides}
    try:
        for k, v in overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return Settings()
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_vision_extractor_provider_returns_object_when_called() -> None:
    from app.deps import build_vision_extractor

    s = _settings_with(OPENAI_API_KEY="sk", VISION_MODE="cloud")
    extractor = build_vision_extractor(s)
    assert extractor is not None


@pytest.mark.asyncio
async def test_vision_extractor_extract_raises_not_implemented_e3() -> None:
    from app.deps import build_vision_extractor

    s = _settings_with(OPENAI_API_KEY="sk", VISION_MODE="cloud")
    extractor = build_vision_extractor(s)
    with pytest.raises(NotImplementedError, match=r"seam not wired in E1 \(E3\)"):
        await extractor.extract(label=None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_orchestrator_refine_raises_not_implemented_e4() -> None:
    from app.deps import build_orchestrator

    s = _settings_with(OPENAI_API_KEY="sk", ORCHESTRATOR_BACKEND="openai")
    orch = build_orchestrator(s)
    with pytest.raises(NotImplementedError, match=r"seam not wired in E1 \(E4\)"):
        await orch.refine(payload=None)  # type: ignore[arg-type]


def test_orchestrator_provider_dispatches_on_backend() -> None:
    from app.deps import build_orchestrator

    s_o = _settings_with(OPENAI_API_KEY="sk", ORCHESTRATOR_BACKEND="openai")
    s_a = _settings_with(ANTHROPIC_API_KEY="sk", ORCHESTRATOR_BACKEND="anthropic")
    o_open = build_orchestrator(s_o)
    o_anth = build_orchestrator(s_a)
    assert type(o_open).__name__ != type(o_anth).__name__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dependency_injection.py -v`
Expected: 4 FAILED — `app.deps` missing.

- [ ] **Step 3: Implement the file**

Create `app/deps.py`:

```python
"""DI container — selects ``VisionExtractor`` and ``Orchestrator`` per env.

E1 ships **placeholder** providers that satisfy the protocol shape but raise
``NotImplementedError`` on any method call that would touch the real seam.
Real implementations land at E3 (vision) and E4 (orchestrator).
"""
from __future__ import annotations

from typing import Any

from app.config import Settings


class _PlaceholderVisionExtractor:
    """Conforms to the ``VisionExtractor`` Protocol shape (extract method);
    raises on invocation. Real implementations land in E3.
    """

    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def extract(self, label: Any) -> list[Any]:
        raise NotImplementedError("seam not wired in E1 (E3)")


class _PlaceholderOpenAIOrchestrator:
    """``Orchestrator`` ABC placeholder. Real implementation lands at E4."""

    backend = "openai"

    async def refine(self, payload: Any) -> Any:
        raise NotImplementedError("seam not wired in E1 (E4)")


class _PlaceholderAnthropicOrchestrator:
    backend = "anthropic"

    async def refine(self, payload: Any) -> Any:
        raise NotImplementedError("seam not wired in E1 (E4)")


def build_vision_extractor(settings: Settings) -> _PlaceholderVisionExtractor:
    return _PlaceholderVisionExtractor(mode=settings.vision_mode)


def build_orchestrator(
    settings: Settings,
) -> _PlaceholderOpenAIOrchestrator | _PlaceholderAnthropicOrchestrator:
    if settings.orchestrator_backend == "anthropic":
        return _PlaceholderAnthropicOrchestrator()
    return _PlaceholderOpenAIOrchestrator()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_dependency_injection.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/deps.py tests/test_dependency_injection.py
git commit -m "feat(e1): add DI container with placeholder seam providers"
```

---

## Task 24: app/api/healthz.py — GET /healthz route

**Files:**
- Create: `app/api/__init__.py` (empty)
- Create: `app/api/healthz.py`
- Create: `tests/test_healthz_stub.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_healthz_stub.py`:

```python
"""GET /healthz returns 200 with the documented payload shape (E1 stub).

L1 AC #3: the endpoint does NOT invoke any seam yet; full warm-up lands in E5.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app_with_healthz_only() -> FastAPI:
    from app.api.healthz import router

    app = FastAPI()
    app.include_router(router)
    return app


def test_healthz_returns_200_with_documented_shape() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    os.environ.setdefault("VISION_MODE", "cloud")
    os.environ.setdefault("ORCHESTRATOR_BACKEND", "openai")

    client = TestClient(_make_app_with_healthz_only())
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "mode" in body
    assert body["mode"]["vision"] in {"local", "cloud", "auto"}
    assert body["mode"]["orchestrator"] in {"openai", "anthropic"}


def test_healthz_does_not_invoke_seams() -> None:
    """E1 §4 AC #3: ``/healthz`` does not call ``extract()`` or ``refine()``."""
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")

    client = TestClient(_make_app_with_healthz_only())
    response = client.get("/healthz")
    assert response.status_code == 200
    # If the route invoked the placeholder providers' seam methods, we would
    # have surfaced a 500 with a NotImplementedError. The 200 response
    # transitively asserts the seams were not invoked.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_healthz_stub.py -v`
Expected: 2 FAILED — module missing.

- [ ] **Step 3: Implement the file**

Create `app/api/__init__.py` (empty):

```python
```

Create `app/api/healthz.py`:

```python
"""GET /healthz route. E1 ships the stub; E5 wires the full warm-up sentinel.

L1 §4 AC #3 / AC #7:
- 200 with ``{"status": "ok", "version": <semver>, "mode": {vision, orchestrator}}``.
- A single structured-log JSON line per invocation.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.config import Settings


router = APIRouter(tags=["health"])
_logger = logging.getLogger("app.healthz")


def _get_settings() -> Settings:
    return Settings()


@router.get("/healthz")
async def healthz(settings: Settings = Depends(_get_settings)) -> dict[str, object]:
    body: dict[str, object] = {
        "status": "ok",
        "version": settings.app_version,
        "mode": {
            "vision": settings.vision_mode,
            "orchestrator": settings.orchestrator_backend,
        },
    }
    _logger.info("healthz_invoked", extra={"reason_code": "ENGINE.OK.NONE"})
    return body
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_healthz_stub.py -v`
Expected: 2 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/api/__init__.py app/api/healthz.py tests/test_healthz_stub.py
git commit -m "feat(e1): add GET /healthz stub route"
```

---

## Task 25: app/main.py — FastAPI app factory + startup hook

**Files:**
- Create: `app/main.py`
- Create: `tests/test_main_app_factory.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_main_app_factory.py`:

```python
"""App factory wires healthz route + startup hook + logging configuration."""
from __future__ import annotations

import os

from fastapi.testclient import TestClient


def test_app_module_exposes_app_object() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import app  # noqa: F401

    assert app is not None


def test_app_registers_healthz_route() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/healthz" in paths


def test_app_factory_function_is_idempotent() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import create_app

    a = create_app()
    b = create_app()
    assert a is not b
    assert {r.path for r in a.routes} == {r.path for r in b.routes}


def test_app_responds_200_to_healthz_via_test_client() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import app

    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_main_app_factory.py -v`
Expected: 4 FAILED — `app.main` missing.

- [ ] **Step 3: Implement the file**

Create `app/main.py`:

```python
"""FastAPI application factory. Source: ARCH §14.3.

Boot sequence (E1 subset; E2–E8 extend):
1. Read ``Settings``.
2. Configure logging (JSON-line stdout + redaction filter).
3. Construct the FastAPI app.
4. Register the ``/healthz`` route.

Later epochs add: rule-loader startup, vision/orchestrator wiring, label/batch/
override/eval routes, UI mounts, SSE.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.healthz import router as healthz_router
from app.config import Settings
from app.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings)

    application = FastAPI(
        title="TTB Label Verification (prototype)",
        version=settings.app_version,
    )
    application.include_router(healthz_router)

    @application.on_event("startup")
    async def _on_startup() -> None:
        logging.getLogger("app.main").info(
            "app_startup",
            extra={
                "reason_code": "ENGINE.OK.NONE",
                "rule_set_version": "0.0.0",  # E2 will overwrite at rule-pack load.
                "model_version": settings.llm_model_snapshot,
                "prompt_version": settings.prompt_version,
            },
        )

    return application


app: FastAPI = create_app()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_main_app_factory.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_main_app_factory.py
git commit -m "feat(e1): add FastAPI app factory wiring logging + healthz route"
```

---

## Task 26: tests/test_secrets_grep.py — NFR-SEC-002 enforcement

**Files:**
- Create: `tests/test_secrets_grep.py`

- [ ] **Step 1: Write the failing test (which is its own implementation)**

Create `tests/test_secrets_grep.py`:

```python
"""NFR-SEC-002 enforcement: ``os.environ`` is read by ``app/config.py`` ONLY.

L1 §4 AC #6: ``grep -rn 'os.environ' app/ | grep -v 'config.py'`` returns no hits.
"""
from __future__ import annotations

import re
from pathlib import Path


_OS_ENVIRON_RE = re.compile(r"\bos\.environ\b")


def test_os_environ_read_only_in_app_config_py() -> None:
    repo = Path(__file__).parents[1]
    app_dir = repo / "app"
    offenders: list[str] = []
    for path in app_dir.rglob("*.py"):
        # Allowed: app/config.py is the single source of truth.
        if path.relative_to(repo) == Path("app") / "config.py":
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _OS_ENVIRON_RE.search(line):
                offenders.append(f"{path.relative_to(repo)}:{lineno}: {stripped}")
    assert not offenders, (
        "NFR-SEC-002 violation: os.environ accessed outside app/config.py:\n"
        + "\n".join(offenders)
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_secrets_grep.py -v`
Expected: PASS — confirms the codebase already routes secrets through `app/config.py`. (If this test fails, it indicates a real NFR-SEC-002 violation that must be fixed before commit — refactor the offender to inject a `Settings` object instead of reading `os.environ` directly.)

- [ ] **Step 3: Commit**

```bash
git add tests/test_secrets_grep.py
git commit -m "test(e1): enforce NFR-SEC-002 single-source env-var policy"
```

---

## Task 27: tests/test_e1_exit_gate.py — integration suite for L1 §4 ACs

**Files:**
- Create: `tests/test_e1_exit_gate.py`

- [ ] **Step 1: Write the integration suite**

Create `tests/test_e1_exit_gate.py`:

```python
"""E1 exit-gate integration suite.

Asserts the 9 ACs from ``docs/plans/ttb-label-verification-epoch-1-foundation.md``
§4. Most are upheld transitively by the per-task tests (T1–T26); this file
ties the per-AC contracts together as one runnable assertion suite.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).parents[1]


def test_ac1_pyproject_is_valid_and_uv_lock_exists() -> None:
    """AC #1: ``uv sync`` succeeds (cloud profile). Existence of ``uv.lock``
    is a transitive check; the parallel-plan-executor verifies fresh
    ``uv sync`` time off-band on a clean checkout."""
    assert (REPO_ROOT / "pyproject.toml").exists()
    assert (REPO_ROOT / "uv.lock").exists()


def test_ac2_taskipy_demo_target_defined() -> None:
    """AC #2: ``uv run task demo`` boots the app. Here we assert the task is
    declared; subprocess boot is exercised by the parallel-plan-executor's
    smoke step, not by pytest."""
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.taskipy.tasks]" in text
    assert "demo = " in text
    assert "uvicorn app.main:app" in text


def test_ac3_healthz_returns_200_with_payload_shape() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import app

    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body and "mode" in body


def test_ac4_test_surface_meets_minimum() -> None:
    """AC #4: ≥4 test files, ≥25 assertions across the suite.

    A loose proxy: count test files and ``def test_`` declarations.
    """
    tests_dir = REPO_ROOT / "tests"
    test_files = list(tests_dir.glob("test_*.py"))
    assert len(test_files) >= 4, [p.name for p in test_files]
    test_count = 0
    for path in test_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("def test_"):
                test_count += 1
    assert test_count >= 25, f"only {test_count} tests defined"


def test_ac5_wire_envelopes_round_trip_byte_identical_keys() -> None:
    """AC #5: every PRD §6.x wire envelope round-trips."""
    from app.schemas.wire.application import ApplicationEnvelope
    from app.schemas.wire.batch import BatchEnvelope
    from app.schemas.wire.disposition import DispositionEnvelope
    from app.schemas.wire.error import ErrorEnvelope

    fixtures_dir = REPO_ROOT / "tests" / "wire_fixtures"
    cases = [
        (ApplicationEnvelope, "application.json"),
        (DispositionEnvelope, "disposition.json"),
        (BatchEnvelope, "batch.json"),
        (ErrorEnvelope, "error.json"),
    ]
    for model, name in cases:
        raw = json.loads((fixtures_dir / name).read_text())
        env = model.model_validate(raw)
        # Re-validate after a dump round trip; equality holds.
        rt = model.model_validate_json(env.model_dump_json())
        assert rt == env, name


def test_ac6_no_os_environ_outside_app_config() -> None:
    """AC #6: NFR-SEC-002 grep enforcement.

    Delegated to ``tests/test_secrets_grep.py``; included here for
    exit-gate completeness — re-run inline.
    """
    from tests.test_secrets_grep import (  # type: ignore[import-not-found]
        test_os_environ_read_only_in_app_config_py,
    )

    test_os_environ_read_only_in_app_config_py()


def test_ac7_healthz_emits_one_json_log_line(capsys) -> None:
    """AC #7: structured log emits a single JSON line on /healthz."""
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")
    from app.main import create_app

    app_obj = create_app()
    client = TestClient(app_obj)
    capsys.readouterr()  # clear startup banner
    r = client.get("/healthz")
    assert r.status_code == 200
    captured = capsys.readouterr().out
    json_lines = [ln for ln in captured.splitlines() if ln.strip().startswith("{")]
    assert json_lines, captured
    parsed = json.loads(json_lines[-1])
    assert "ts" in parsed
    assert "level" in parsed
    assert "msg" in parsed


def test_ac8_di_providers_raise_not_implemented_on_seam_invocation() -> None:
    """AC #8: providers raise NotImplementedError on extract()/refine()."""
    import asyncio

    from app.config import Settings
    from app.deps import build_orchestrator, build_vision_extractor

    s = Settings()
    extractor = build_vision_extractor(s)
    orch = build_orchestrator(s)

    async def _run() -> tuple[bool, bool]:
        e3, e4 = False, False
        try:
            await extractor.extract(label=None)  # type: ignore[arg-type]
        except NotImplementedError as exc:
            e3 = "seam not wired in E1" in str(exc) and "E3" in str(exc)
        try:
            await orch.refine(payload=None)  # type: ignore[arg-type]
        except NotImplementedError as exc:
            e4 = "seam not wired in E1" in str(exc) and "E4" in str(exc)
        return e3, e4

    e3, e4 = asyncio.run(_run())
    assert e3 and e4


def test_ac9_rule_set_canonically_declared_in_app_schemas_rules() -> None:
    """AC #9 (E1 partial): canonical declaration lives in app/schemas/rules.py.

    The full ``is``-identity assertion against ``app/rules/models.py`` belongs
    to E2 when the re-export lands; here we only confirm canonical residency.
    """
    from app.schemas.rules import RuleSet

    assert RuleSet.__module__ == "app.schemas.rules"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_e1_exit_gate.py -v`
Expected: 9 PASSED.

- [ ] **Step 3: Run the full suite to confirm everything composes**

Run: `uv run pytest -v`
Expected: all tests PASSED. Count must be ≥ 25 (per AC #4).

- [ ] **Step 4: Smoke-test the demo task off-band**

Run: `uv run task demo` (in a separate shell), then in another shell:
```bash
curl -fsS http://localhost:8000/healthz
```
Expected: a 200 JSON response with `status=ok`, `version`, `mode`. Send `Ctrl+C` to the demo shell — process exits cleanly.

This is operator validation for AC #2; the parallel-plan-executor records it manually.

- [ ] **Step 5: Commit**

```bash
git add tests/test_e1_exit_gate.py
git commit -m "test(e1): add exit-gate integration suite for L1 §4 ACs"
```

---

## Task 28: README.md — reviewer-profile setup

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README content**

Replace `README.md` (the current one is a stub):

```markdown
# TTB Label Verification — Prototype

A standalone, web-deployable proof-of-concept for AI-orchestrated, deterministic-rule-core
TTB COLA label verification. **Prototype tier** per BRD §8.2 — not a production ATO claim,
no COLAs Online integration, no persistence beyond the current process.

See `docs/PRD.md` (v0.6) and `docs/ARCHITECTURE.md` (v0.3) for the full spec; see
`docs/plans/ttb-label-verification-epochs.md` for the L1 epoch plan.

## Reviewer profiles (ARCH §9.1)

Three one-command setup profiles target the deployed-URL and on-prem trajectories.

### Profile A — Hosted demo (preferred)

The deployed URL serves the cloud-mode default (GPT-4o on crop, Structured Outputs
``strict:true``). No local install; no API key needed for review against cached fixtures.

### Profile B — Local cloud-mode boot

```bash
git clone <repo>
cd ttb-label-verification
cp .env.example .env  # then fill OPENAI_API_KEY
uv sync               # CPU profile; ≤90s on a 5 Mbps connection
uv run task demo      # uvicorn app.main:app on :8000
curl http://localhost:8000/healthz
```

### Profile C — Local GPU mode (on-prem-trajectory)

```bash
uv sync --extra gpu   # adds paddlepaddle-gpu (CUDA 12.6) + torch
VISION_MODE=local uv run task demo
```

GPU profile boot adds ~30–45 s for first-``/healthz`` (model load); subsequent
``/healthz`` warm calls are ≤2 s. See ``DEMO-RUNBOOK.md`` for the demo timeline.

## Project structure

```
app/                    FastAPI single-process app
  schemas/              Pydantic v2 internal + wire (PRD §6.x) types
  logging/              JSON-line stdout, OTel GenAI attribute names
  api/                  Route handlers (E1: /healthz; E5–E8 add the rest)
  config.py             Pydantic Settings (single source of truth for env vars)
  deps.py               DI container; selects VisionExtractor / Orchestrator
  main.py               App factory
tests/                  pytest suite
docs/                   PRD, ARCHITECTURE, decisions, epoch plans
```

## Testing

```bash
uv run pytest -v
```

The exit-gate integration suite is ``tests/test_e1_exit_gate.py`` (E1) and the
analogous ``test_e<N>_exit_gate.py`` for later epochs.
```

- [ ] **Step 2: Verify the file renders cleanly**

Visually inspect; ensure no broken anchors and the three reviewer profiles read clearly.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(e1): document reviewer profiles A/B/C and project layout"
```

---

## Self-review

**Spec coverage check (against L1 §4 ACs and §2 components):**

- AC #1 `uv sync` ≤ 90 s — T1 ships pyproject + lockfile; off-band timing check in T27 / executor smoke.
- AC #2 `uv run task demo` boots — T1 declares the task; T25 ships `app/main.py`; T27 step 4 smoke-tests the boot.
- AC #3 `/healthz` 200 + payload — T24 ships the route; T27 AC3 asserts.
- AC #4 ≥ 4 test files, ≥ 25 assertions — T27 AC4 counts; we ship ~10 test files and ~30+ tests.
- AC #5 wire envelopes round-trip — T14–T17 ship per-envelope round-trips; T27 AC5 confirms all four.
- AC #6 NFR-SEC-002 grep — T26 enforces; T27 AC6 re-runs.
- AC #7 structured log line on `/healthz` — T18–T21 build logging; T24 emits; T27 AC7 asserts.
- AC #8 DI providers raise `NotImplementedError("E3"/"E4")` — T23 ships providers; T27 AC8 asserts.
- AC #9 `RuleSet` canonical in `app/schemas/rules.py` — T11 ships canonical declaration; T27 AC9 asserts module residency. Full `is`-identity vs `app/rules/models.py` deferred to E2 (in scope per "Stay strictly in E1" hard constraint).

§2 components mapped:
- §2.1 `pyproject.toml`, `uv.lock`, `.env.example`, `README.md` → T1, T2, T28. Dockerfiles deferred to E8 (out of E1 exit gate; documented in plan header).
- §2.2 `app/main.py`, `app/config.py`, `app/deps.py`, `app/api/healthz.py` → T22, T23, T24, T25.
- §2.3 internal Pydantic models → T5–T13.
- §2.3 wire envelopes → T14–T17.
- §2.4 logging subsystem → T18–T21.
- §2.5 test infrastructure → T3 (conftest), T4 (fixtures), T5–T17 (per-schema), T22 (config), T18–T21 (logging), T23 (DI), T24 (healthz), T25 (factory), T26 (secrets), T27 (exit gate). pytest config in T1.

**Placeholder scan:** none — every step ships executable code or a concrete file write.

**Type consistency check:**
- `BeverageClass` declared in T6, imported by T5 (forward ref), T7, T11 — consistent.
- `ReasonCode` exposed as `str | None` field type and `ReasonCode.validate_grammar` static method (T7) — used by T15's wire schema indirectly via `RuleFindingWire.reason_code: str` (no validation at the wire layer per "validation at boundary, not interior" — boundary validation lives in E2's RuleLoader).
- `MatchPolicy` enum (T11) shares the value space with `MatchKind` (T5) but they are distinct types — `MatchPolicy` is rule-pack data; `MatchKind` is per-evidence engine output. Both retained.
- `Disposition` literal (T15) uses `pass | fail | needs_review` — matches PRD §6.2 exactly.
- `Outcome` enum (T7) is broader (`pass | fail | insufficient_evidence | not_applicable | timeout | error`) — internal engine vocabulary, not wire vocabulary; consistent with ARCH §6.4.
- `ItemState` (T12) declares `failed` as a flat enum value with optional `failed_reason` field on `BatchItem` — pragmatic flattening of the L1 spec's `failed(reason)` side-edge; documented in T12.

**Cross-epoch boundary check:** No file under `app/rules/`, `app/vision/`, `app/orchestrator/`, `app/services/`, `app/batch/`, `app/ui/`, `frontend/`, `rules/`, `assets/`, `fixtures/`, `demo/`, `eval/`, `Dockerfile*`, `docker-compose*.yml` is created or modified by this plan. Hard constraint upheld.

---

## Execution

Per olorin CLAUDE.md, this plan is dispatched via **`parallel-plan-executor`** (the only L2 executor on this workspace). The executor runs each task in an isolated worktree subagent with the `task-executor` skill body injected for TDD enforcement; commits land directly on the active branch (no squash, fast-forward only).

Next steps after this plan is reviewed:
1. Run `parallel-planning` to add the dependency graph + execution waves.
2. Run `plan-review` (plan-checker structural pass + architectural reviewer).
3. `/clear` and dispatch via `parallel-plan-executor`.

---

## Dependency Graph

> Generated by `parallel-planning`. Consumed by `parallel-plan-executor` — the executor dispatches every task in a wave concurrently (≤6 per dispatch message) with a barrier between waves. Commits land directly on `main` (fast-forward, no squash).

### Task Dependencies

| Task | Depends On | Blocks | Files Owned |
|---|---|---|---|
| T1: pyproject + uv.lock + app pkg | — | T2, T3, T5, T18, T22, T28 | `pyproject.toml`, `uv.lock`, `app/__init__.py`, `tests/test_bootstrap.py` |
| T2: .env.example | T1 | T27 | `.env.example`, `tests/test_env_example.py` |
| T3: conftest + tests pkg | T1 | T4, T5–T17 (transitive) | `tests/__init__.py`, `tests/conftest.py`, `tests/test_conftest.py` |
| T4: wire fixtures | T3 | T14, T15, T16, T17, T27 | `tests/wire_fixtures/*.json`, `tests/test_wire_fixtures.py` |
| T6: expected + schemas pkg | T1 | T5, T7, T11 | `app/schemas/__init__.py`, `app/schemas/expected.py`, `tests/test_schemas_expected.py` |
| T5: extracted schema | T6 (`BeverageClass` import + pkg marker) | T7, T8, T9, T10, T12, T13, T14, T26 | `app/schemas/extracted.py`, `tests/test_schemas_round_trip.py` (creator) |
| T7: rejection schema | T5 (test file) + T6 (BeverageClass + Severity declared here) | T11, T15 | `app/schemas/rejection.py`, modifies `tests/test_schemas_round_trip.py` |
| T8: refined schema | T7 (test file only — no import dep) | T9 | `app/schemas/refined.py`, modifies `tests/test_schemas_round_trip.py` |
| T9: audit schema | T8 (test file) | T10, T15 | `app/schemas/audit.py`, modifies `tests/test_schemas_round_trip.py` |
| T10: metrics schema | T9 (test file) | T11, T15 | `app/schemas/metrics.py`, modifies `tests/test_schemas_round_trip.py` |
| T11: rules schema | T10 (test file) + T6 (BeverageClass) + T7 (Severity) | T12 | `app/schemas/rules.py`, modifies `tests/test_schemas_round_trip.py` |
| T12: batch schema | T11 (test file) | T13 | `app/schemas/batch.py`, modifies `tests/test_schemas_round_trip.py` |
| T13: calls schema | T12 (test file) | T14 | `app/schemas/calls.py`, modifies `tests/test_schemas_round_trip.py` |
| T14: wire/application | T13 (test file) + T4 (fixtures) | T15, T16, T17 | `app/schemas/wire/__init__.py`, `app/schemas/wire/application.py`, modifies `tests/test_schemas_round_trip.py` |
| T15: wire/disposition | T14 (test file + wire/__init__) + T9 + T10 | T16 | `app/schemas/wire/disposition.py`, modifies `tests/test_schemas_round_trip.py` |
| T16: wire/batch | T15 (test file) + T14 (wire/__init__) | T17 | `app/schemas/wire/batch.py`, modifies `tests/test_schemas_round_trip.py` |
| T17: wire/error | T16 (test file) + T14 (wire/__init__) | T26, T27 | `app/schemas/wire/error.py`, modifies `tests/test_schemas_round_trip.py` |
| T18: otel_genai formatter | T1 | T19, T20, T21 | `app/logging/__init__.py` (empty), `app/logging/otel_genai.py`, `tests/test_logging_emission.py` (creator) |
| T19: redaction filter | T18 (logging pkg + test file) | T21 | `app/logging/redaction.py`, modifies `tests/test_logging_emission.py` |
| T20: ring_buffer | T19 (test file only) | T21 | `app/logging/ring_buffer.py`, modifies `tests/test_logging_emission.py` |
| T21: configure_logging | T20 (test file) + T18 (`__init__.py`) + T19 (filter import) | T25 | modifies `app/logging/__init__.py`, modifies `tests/test_logging_emission.py` |
| T22: Settings | T1 | T23, T24, T26 | `app/config.py`, `tests/test_config_load.py` |
| T23: DI providers | T22 | T26 | `app/deps.py`, `tests/test_dependency_injection.py` |
| T24: /healthz route | T22 | T25, T26 | `app/api/__init__.py`, `app/api/healthz.py`, `tests/test_healthz_stub.py` |
| T25: app factory | T21, T22, T24 | T26 | `app/main.py`, `tests/test_main_app_factory.py` |
| T26: secrets-grep test | T17, T22, T23, T24, T25 (must scan all of `app/`) | T27 | `tests/test_secrets_grep.py` |
| T27: exit-gate suite | T2, T17, T22, T23, T24, T25, T26 | — | `tests/test_e1_exit_gate.py` |
| T28: README | — (docs-only; could parallelize anywhere) | — | `README.md` |

### Shared Files (force serialization)

| File | Owners | Resolution |
|---|---|---|
| `tests/test_schemas_round_trip.py` | T5 (create) → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 (each appends) | Strict serial chain. **See "Optimization opportunity" below.** |
| `tests/test_logging_emission.py` | T18 (create) → T19 → T20 → T21 (each appends) | Serial chain. **See "Optimization opportunity" below.** |
| `app/logging/__init__.py` | T18 (creates empty placeholder) → T21 (replaces with `configure_logging`) | T18→T21 ordering required. |

### Execution Waves (post plan-review revision)

```
Wave 1 (1 task):       [T1]                                             ← bootstrap
Wave 2 (5 tasks):      [T2, T3, T18, T22, T28]                          ← root-level work
Wave 3 (5 tasks):      [T4, T6, T19, T23, T24]                          ← T6 owns app/schemas/__init__.py + expected.py
Wave 4 (2 tasks):      [T5, T20]                                        ← T5 needs T6; T20 needs T19
Wave 5 (2 tasks):      [T7, T21]                                        ← T7 needs T5+T6; T21 needs T18+T19+T20
Wave 6 (2 tasks):      [T8, T25]                                        ← T8 = schema chain; T25 = app factory (needs T21+T22+T24)
Wave 7 (1 task):       [T9]                                             ← schema test-file ownership chain
Wave 8 (1 task):       [T10]
Wave 9 (1 task):       [T11]                                            ← also needs T6 (BeverageClass) + T7 (Severity)
Wave 10 (1 task):      [T12]
Wave 11 (1 task):      [T13]
Wave 12 (1 task):      [T14]                                            ← also needs T4 (fixtures) + T5 (pkg)
Wave 13 (1 task):      [T15]                                            ← also needs T9 (AuditRecord) + T10 (Metrics)
Wave 14 (1 task):      [T16]
Wave 15 (1 task):      [T17]
Wave 16 (1 task):      [T26]                                            ← grep-scan over app/
Wave 17 (1 task):      [T27]                                            ← exit-gate integration
```

**Critical path:** T1 → T6 → T5 → T7 → T8 → T9 → T10 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T26 → T27 (16 hops).

**Parallelism factor:** 28 tasks across 17 waves ≈ 1.65 tasks/wave (low). Early waves (W1–W6) are healthily parallel; the schema serial chain (W7–W15) drops parallelism to 1 task/wave.

**Wave changes from v0.2 to v0.3:**
- T19 (logging redaction) and T20 (logging ring buffer) split into Waves 3 and 4 — they both modify `tests/test_logging_emission.py` so cannot be in the same wave.
- T5 (extracted) and T6 (expected) swapped — `extracted.py` now real-imports `BeverageClass` from `expected.py` (post plan-review fix); T6 owns `app/schemas/__init__.py` package marker.
- T6 owns its own test file `tests/test_schemas_expected.py` (T6 runs before the shared `test_schemas_round_trip.py` is created by T5).

### Optimization opportunity (apply at plan-review)

The schema serial chain (W5–W15) and the logging serial chain (W3–W4) are caused by **append-style edits to two shared test files** (`tests/test_schemas_round_trip.py`, `tests/test_logging_emission.py`). The fix is structural and worth applying at the plan-review pass:

1. Split `tests/test_schemas_round_trip.py` into one file per schema module — `tests/test_schema_extracted.py`, `tests/test_schema_expected.py`, …, `tests/test_schema_wire_error.py` (13 files).
2. Split `tests/test_logging_emission.py` into `tests/test_logging_otel_genai.py`, `tests/test_logging_redaction.py`, `tests/test_logging_ring_buffer.py`, `tests/test_logging_configure.py` (4 files).

After the split, the recomputed wave graph collapses to **8 waves**:

```
Wave 1 (1):  [T1]
Wave 2 (6):  [T2, T3, T5, T18, T22, T28]
Wave 3 (6):  [T4, T6, T8, T9, T10, T12]
Wave 4 (5):  [T13, T19, T20, T23, T24]
Wave 5 (3):  [T7, T14, T21]
Wave 6 (5):  [T11, T15, T16, T17, T25]
Wave 7 (1):  [T26]
Wave 8 (1):  [T27]
```

That is **~28 tasks across 8 waves ≈ 3.5 tasks/wave** — a ~2× wall-clock speedup. The split also matches Python convention (one test file per module) and is no harder to review.

**Recommendation:** apply the split during the `plan-review` pass before dispatching. The structural reviewer should flag this anyway; pre-applying saves a round trip.

### Wave-by-wave dispatch notes (for the executor)

- **Wave 1 (T1)** is sequential because it produces `uv.lock` and the `app/` package marker that every other task imports.
- **Wave 2 (5 parallel)** produces five independent surfaces: env-var docs, conftest, formatter, Settings, README. No file overlap.
- **Wave 3 (6 parallel)** is the largest concurrent dispatch. Verify executor concurrency cap is set to 6.
- **Waves 4–5** mix logging and schema work; T25 (app factory) is intentionally late because it needs both `configure_logging` (T21) and `healthz_router` (T24).
- **Schema serial chain (W6–W15)** runs one task per wave. If the optimization above is applied, this collapses to two parallel waves.
- **Wave 16 (T26)** runs the NFR-SEC-002 grep enforcement — must follow every task that creates a `*.py` file in `app/`.
- **Wave 17 (T27)** is the integration gate. The executor should fail the entire dispatch if T27 fails.

### Executor handoff

Next steps:
1. `plan-review` (plan-checker structural pass + architectural reviewer). **Apply the test-file split optimization at this step if reviewers agree.**
2. `/clear`.
3. Dispatch via `parallel-plan-executor`.

---

## Change log

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-05-03 | Initial L2 plan — 28 tasks decomposing E1 (foundation & boot). Commits per task, atomic. Dockerfiles deferred to E8. Cross-epoch import-identity AC #9 partially deferred to E2 (canonical declaration ships here). |
| 0.2 | 2026-05-03 | Added Dependency Graph + Execution Waves (parallel-planning pass). Schema serial chain noted; test-file-split optimization recommended at plan-review (would drop wave count from 17 → 8). |
| 0.3 | 2026-05-03 | Plan-review revision pass. Fixes: (a) T19/T20 wave conflict — split into Waves 3/4 (both modify `test_logging_emission.py`); (b) T5/T6 swap — `extracted.py` real-imports `BeverageClass` from `expected.py` (was TYPE_CHECKING forward ref, fragile); T6 owns `app/schemas/__init__.py` and `tests/test_schemas_expected.py`; (c) T23 exception text now matches L1 §4 AC #8 verbatim ("seam not wired in E1"); (d) T22 `dev_mode` field validator coerces empty-string → False (pydantic-settings strict-bool would otherwise raise); (e) T22 + T2 inventory aligned with `LOG_LEVEL` added to `.env.example`; (f) T22 `Settings.from_env()` factory added per L1 §2.2; (g) T1 `pytest.ini_options` now declares `markers` per L1 §2.5; (h) T11 docstring documents the E2 re-export `is`-identity contract; (i) T15 docstring documents the D-017 confidence-builder ownership (E5). |
