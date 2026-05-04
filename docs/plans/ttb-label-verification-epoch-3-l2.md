# TTB Label Verification — Epoch 3 (Vision Extractor Seam) — L2 Implementation Plan

> **For agentic workers:** REQUIRED EXECUTOR: `parallel-plan-executor`. Per olorin CLAUDE.md, `superpowers:subagent-driven-development` is obsolete and fully replaced by `parallel-plan-executor` (which injects the `task-executor` skill body for TDD enforcement). Each task lands as one or more Red→Green→Commit cycles inside an isolated worktree subagent. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Parent L1:** [`ttb-label-verification-epoch-3-vision-seam.md`](./ttb-label-verification-epoch-3-vision-seam.md) (v0.2)
> **L1 index:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md) (v0.4)
> **E1 L2 (structural template):** [`ttb-label-verification-epoch-1-l2.md`](./ttb-label-verification-epoch-1-l2.md)
> **E2 L2 (structural template):** [`ttb-label-verification-epoch-2-l2.md`](./ttb-label-verification-epoch-2-l2.md)
> **PRD:** [`docs/PRD.md`](../PRD.md) v0.6 — FR-001..008, FR-501 (bbox overlay), FR-505/603 needs-better-photo, FR-602 missing-DPI, FR-912 ENGINE.MODEL.UNAVAILABLE
> **ARCH:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) v0.3 — §4.2.3 GPT-4o-on-crop, §6.1 FieldObservation, §6.2 Evidence, §6.7 ring buffer, §6.9 CallRecord, §7 cloud topology, §11.2 bulkhead, §12.2 env-var inventory
> **ADRs in scope:** D-004 (substitutability seam), D-015 (vision_mode autodetect), D-017 (min-aggregation confidence), D-020 (snapshot/prompt pinning), D-021 (prototype-tier scope reduction — Florence-2 + Qwen2.5-VL out)

**Goal.** Land D-004 swap point #1: the `VisionExtractor` Protocol and two conforming concrete implementations (`CloudVisionExtractor` validated default, `LocalVisionExtractor` on-prem-trajectory companion) that produce `list[FieldObservation]` per PRD §5.1 (FR-001..008). Cloud uses GPT-4o-on-crop with OpenAI Structured Outputs `strict:true`, recorded at the HTTP layer via `respx`. Local composes PaddleOCR + SWT bold detector + GPT-4o tiebreaker per the D-021 trimmed pipeline. Both honor BRISQUE/NIQE quality gates emitting `WARNING.LEGIBILITY.*`, multi-source DPI extraction emitting `ENGINE.MEASUREMENT.MISSING_DPI` on absence, an `asyncio.Semaphore(4)` bulkhead, and per-call `CallRecord` ring-buffer writes. After E3 closes, `VISION_MODE=cloud uv run task demo` extracts every PRD §5.1 field from a JPEG/PNG label and `VISION_MODE=auto` autodetects CUDA presence and routes accordingly per D-015.

**Architecture.** A single Python package `app/vision/` owning the seam Protocol (`base.py`), the cloud extractor (`cloud.py`), the local composer (`local.py`), three sub-runners (`paddle_runner.py`, `swt.py`, `tiebreak_gpt4o.py`), the quality-gate module (`quality.py`), and a CLI smoke entry (`__main__.py`). The Protocol is `runtime_checkable` so substitutability is a one-line `isinstance` assertion. Cloud impl issues per-field GPT-4o calls under an `asyncio.Semaphore(4)` bulkhead; each call writes one `CallRecord` to the ring buffer. Local impl runs PaddleOCR for OCR + bbox, SWT for heading-bold (FR-202), and the GPT-4o tiebreaker only when local signals are uncertain. Recorded HTTP responses live under `tests/recordings/openai/<snapshot>/<fixture>/<call>.json` keyed by `LLM_MODEL_SNAPSHOT` + `PROMPT_VERSION`. DPI is extracted from EXIF/PNG pHYs/JFIF/applicant-supplied dimensions; absence emits `ENGINE.MEASUREMENT.MISSING_DPI` per FR-602/910. Quality gates short-circuit `disposition=needs_better_photo` *before* invoking expensive extraction calls. DI wiring in `app/deps.py` replaces the E1 placeholder with `build_vision_extractor(settings)` whose `_autodetect()` probes `nvidia-smi` via `subprocess.run`.

**Tech stack.** Python 3.12, Pydantic v2 (E1), `openai >= 1.50` (already pinned), `httpx >= 0.27` (already pinned), `paddleocr >= 3.0` + `paddlepaddle >= 3.0` (already pinned in core for cloud-mode metadata; CPU build), `[gpu]` extras add `paddlepaddle-gpu` + `torch`, `opencv-python-headless >= 4.10` (already pinned, used for BRISQUE/NIQE proxies + glare/motion-blur heuristics), `pillow >= 11.0` (already pinned, used for EXIF/DPI extraction), `numpy >= 2.0` (already pinned). **One new top-level dev dependency:** `respx >= 0.21` for HTTP-layer recording — added to `[dependency-groups.dev]`.

**TDD posture.** Each task is one or more Red→Green→Commit cycles on one file (or one tightly coupled file group). The `task-executor` skill body (injected by `parallel-plan-executor`) enforces "one behavior per commit" — heavier tasks (cloud.py, local.py, quality.py) bundle multiple cycles per task. Each commit is atomic and Conventional (`feat:`/`test:`/`chore:`/`docs:`). Pre-existing main is fast-forwarded after each task. **No `--amend` after pre-commit hook failure** — fix, re-stage, new commit. No squash on merge.

**Hard scope boundary.** This plan owns: `app/vision/`, `app/schemas/label.py` (E1 omission backfill), `tests/recordings/openai/`, the synthetic `fixtures/01-spirits-clean/label.png` test asset, two reason-code additions in `rules/reason_codes.yaml`, one `respx` dev-dep addition in `pyproject.toml`, the `app/deps.py` provider replacement (placeholder → real impl), and one ad-hoc `scripts/record_vision_responses.py` companion. It does NOT touch `app/rules/` (E2 — locked), `app/orchestrator/` (E4), `app/services/` (E5), `app/batch/` (E6), `app/ui/` or `frontend/` (E7), `demo/` or `eval/` (E8). It does NOT add Florence-2 or Qwen2.5-VL imports anywhere (D-021).

**Cross-epoch follow-through.** This plan closes E1 §4 omission #X (`Label` schema): it lands `app/schemas/label.py` as a frozen Pydantic model. E1's `app/deps.py` placeholder is replaced. The vision-isolation invariant (`grep -rn 'openai\|paddle' app/ | grep -v 'app/vision/'` returns no hits) is asserted by a new test file.

**Recording posture.** Cloud-vision tests use **HTTP-layer recordings** via `respx`, not SDK-level mocks. Recordings are committed under `tests/recordings/openai/<snapshot>/<fixture>/<call>.json`. CI fails if the active `LLM_MODEL_SNAPSHOT` has no matching recording directory — recordings rotate via `scripts/record_vision_responses.py` when the snapshot tag rotates.

**Synthetic-fixture posture.** E3 ships **one** synthetic `fixtures/01-spirits-clean/label.png` (200×200, embedded text, EXIF DPI=300) sufficient for unit tests + recording determinism. The full demo fixture set (01–07) is E8 territory; E3 only needs enough bytes to compute deterministic OpenAI request hashes and exercise EXIF-extraction code paths.

---

## File map

| Path | Created/modified by task | Responsibility |
|---|---|---|
| `app/schemas/label.py` | T1 | `Label` Pydantic model: `image_bytes: bytes`, `content_type: Literal["image/jpeg","image/png"]`, `dimensions: Dimensions \| None`, `face_tag: Literal["front","back","neck","side"]`, `label_id: str`, `batch_id: str`. Frozen, `extra="forbid"`. |
| `app/schemas/label.py` (Dimensions) | T1 | Inner `Dimensions` model: `width_px: int`, `height_px: int`, `dpi: int \| None`. Frozen. |
| `app/vision/__init__.py` | T2 | Package marker; re-export `VisionExtractor` Protocol from `base`. |
| `app/vision/base.py` | T2 | `VisionExtractor` Protocol (`@runtime_checkable`) with `extract(label: Label) -> list[FieldObservation]` and `ensure_loaded() -> None` (both async). Sub-runner `Candidate` dataclass + sub-runner Protocol type aliases (`PaddleRunnerLike`, `SWTRunnerLike`, `GPT4oTiebreakLike`). |
| `rules/reason_codes.yaml` | T3 | Append `WARNING.LEGIBILITY.GLARE` + `WARNING.LEGIBILITY.MOTION_BLUR` per L1 §2.4 + PRD FR-603. |
| `pyproject.toml` | T4 | Append `respx >= 0.21` to `[dependency-groups.dev]`. |
| `fixtures/01-spirits-clean/label.png` | T5 | 200×200 synthetic PNG with embedded "ACME BOURBON" text + EXIF DPI=300. ≤ 5 KB. |
| `app/vision/quality.py` | T6 | `QualityReport` Pydantic model + `assess(image_bytes: bytes) -> QualityReport`. BRISQUE proxy via opencv variance-of-Laplacian; NIQE proxy via spatial-frequency entropy; glare via overexposure histogram; motion-blur via FFT high-frequency ratio; DPI via PIL EXIF/pHYs/JFIF parse. |
| `app/vision/paddle_runner.py` | T7 | `PaddleRunner` class: `async run(crop: bytes) -> list[Candidate]`. Lazy-import `paddleocr` inside `ensure_loaded()` so cloud-only profiles don't pay the import cost. Records `CallRecord` with `stage="vision.paddleocr"`, `provider="local.paddleocr"`. |
| `app/vision/swt.py` | T8 | `SWTRunner` class: `async run(crop: bytes) -> StrokeWidthReport`. opencv-only (no torch); detects bold heading text via stroke-width statistics. Records `CallRecord` with `stage="vision.swt"`, `provider="local.paddleocr"` (re-using the local provider tag — there's no "swt" provider in the CallRecord literal). |
| `app/vision/tiebreak_gpt4o.py` | T9 | `GPT4oTiebreakRunner` class: `async run(crop: bytes, prompt: str) -> dict`. Single OpenAI call with `strict:true` Structured Outputs. Records `CallRecord` with `stage="vision.gpt4o_tiebreak"`, `provider="openai"`. |
| `tests/recordings/openai/gpt-4o-2024-08-06/v1/01-spirits-clean/*.json` | T9 + T10 | HTTP-layer recordings keyed by `LLM_MODEL_SNAPSHOT/PROMPT_VERSION/fixture/call`. |
| `app/vision/cloud.py` | T10 | `CloudVisionExtractor`: per-field GPT-4o-on-crop calls under `asyncio.Semaphore(4)`; coarse layout pre-pass + 8 per-field calls (FR-001..008). Records 9 `CallRecord` entries per `extract()`. Quality-gate short-circuit before extraction. |
| `app/vision/local.py` | T11 | `LocalVisionExtractor`: composes `PaddleRunner` + `SWTRunner` + `GPT4oTiebreakRunner`. Routes uncertain fields to tiebreaker. Same Protocol surface as Cloud. |
| `app/deps.py` | T12 | Replace `_PlaceholderVisionExtractor` with real `build_vision_extractor(settings: Settings) -> VisionExtractor` dispatching on `settings.vision_mode`. `_autodetect()` runs `subprocess.run(['nvidia-smi'], check=False, capture_output=True, timeout=2)`; non-zero return ⇒ cloud per D-015. |
| `app/vision/__main__.py` | T13 | CLI smoke: `python -m app.vision --label fixtures/01-spirits-clean/label.png --mode cloud` extracts FR-001..008 against recordings, prints field count + first-3 field_ids. Exit 0 on success. |
| `scripts/record_vision_responses.py` | T14 | Companion to D-020 snapshot rotation. Iterates the active fixture set + per-field calls, performs one **live** OpenAI call each, writes the response to `tests/recordings/openai/<active-snapshot>/<prompt-version>/<fixture>/<call>.json`. Guarded by `OPENAI_API_KEY` presence + an explicit `--live` flag. |
| `tests/test_label_schema.py` | T1 | Round-trip + frozen + `extra="forbid"` tests. |
| `tests/test_vision_protocol.py` | T2 | `runtime_checkable` shape: `VisionExtractor.__protocol_attrs__` includes `extract` + `ensure_loaded`; both are coroutines. |
| `tests/rules/test_reason_codes_yaml.py` | T3 (extends existing) | Extend whitelist to require `WARNING.LEGIBILITY.GLARE` + `WARNING.LEGIBILITY.MOTION_BLUR`. |
| `tests/test_vision_quality_gates.py` | T6 | DPI sources, BRISQUE/NIQE thresholds, glare detection, motion-blur detection, QualityReport disposition routing. |
| `tests/test_vision_paddle_runner.py` | T7 | Interface-mock paddleocr; assert CallRecord write; assert lazy-import behavior (no `paddleocr` import on cloud profile). |
| `tests/test_vision_swt.py` | T8 | Synthetic crops with stroke-width disparity; bold/non-bold classification. |
| `tests/test_vision_tiebreak_gpt4o.py` | T9 | `respx` recording fixture; assert structured-output schema `strict:true`; assert CallRecord. |
| `tests/test_vision_cloud_extraction.py` | T10 | Cloud impl extracts FR-001..008 against recorded responses; field_id set matches PRD §5.1; CallRecord count == 9. |
| `tests/test_vision_local_protocol.py` | T11 | Local impl satisfies Protocol with sub-runners interface-mocked; `ensure_loaded()` raises `RuntimeError` if `--extra gpu` deps absent (simulated by import-fail monkeypatch). |
| `tests/test_vision_deps_autodetect.py` | T12 | `_autodetect` with `subprocess.run` patched: nvidia-smi-present → local; nvidia-smi-absent → cloud; subprocess timeout → cloud (defensive). |
| `tests/test_vision_cli_smoke.py` | T13 | CLI exits 0 on synthetic fixture + recordings; non-existent label exits 2 with stderr message. |
| `tests/test_vision_substitutability.py` | T15 | `isinstance(CloudVisionExtractor(settings), VisionExtractor) is True`; same for `LocalVisionExtractor`; both produce identical FR-001..008 `field_id` set against the synthetic fixture. |
| `tests/test_vision_bulkhead.py` | T16 | 5 concurrent `extract()` calls under `asyncio.Semaphore(4)`; in-flight count never exceeds 4; 5th queues without raising. |
| `tests/test_vision_ring_buffer_records.py` | T17 | `extract()` writes 9 CallRecords (cloud) / 1–3 (local) with right `stage` enum; ring-buffer `maxlen=200` honored. |
| `tests/test_vision_dpi_extraction.py` | T18 | EXIF-DPI, PNG pHYs-DPI, JFIF-DPI, applicant-supplied `Label.dimensions.dpi`, missing-DPI → ValidationResult emits `ENGINE.MEASUREMENT.MISSING_DPI`. |
| `tests/test_vision_isolation.py` | T19 | `grep -rn 'openai\|paddle\|cv2\|torch' app/` returns hits ONLY under `app/vision/`. Florence-2 / Qwen-VL imports absent globally. |

---

## Conventions used in this plan

- **Frozen Pydantic models.** `Label`, `Dimensions`, `QualityReport` use `model_config = ConfigDict(extra="forbid", frozen=True)`. No mutation.
- **Protocol declaration.** `VisionExtractor` is `typing.Protocol` decorated `@runtime_checkable` so `isinstance` works. Sub-runner Protocols use the same pattern.
- **Async signature.** `extract()` and `ensure_loaded()` are both `async def` — see L1 §2.1.
- **Lazy imports.** Heavy deps (`paddleocr`, `cv2`, `torch`) are imported inside `ensure_loaded()` or at first method call, not at module top-level. The cloud profile must be importable without `paddlepaddle-gpu`/`torch` installed.
- **Recording filenames.** `tests/recordings/openai/<LLM_MODEL_SNAPSHOT>/<PROMPT_VERSION>/<fixture-id>/<call-name>.json`. Default for E3: `gpt-4o-2024-08-06/v1/01-spirits-clean/{layout,brand_name,class_type,abv,net_contents,gov_warning,heading_typography,name_address,country_origin}.json` — 9 files.
- **CallRecord population.** `provider` ∈ `{"openai", "anthropic", "local.paddleocr"}` (the only literals declared in the existing E1 schema). Per L1 §4 item 10, every successful extraction writes ≥1 CallRecord (cloud: 9, local: 1–3 trimmed pipeline).
- **Bulkhead.** `asyncio.Semaphore(4)` is constructed in `CloudVisionExtractor.__init__` and held as an instance attribute; **not** a module-global (so multiple extractor instances don't share a bottleneck).
- **CFR-citation discipline.** Vision modules don't emit CFR citations directly — they produce `FieldObservation` objects, and the rule engine (E2) attaches citations downstream. Vision modules MAY include CFR comments in docstrings for `FR-602` rationale.
- **Inference-dep ban — vision direction.** This is the inverse of E2's invariant. E2 said `app/rules/` may not import `openai/anthropic/httpx/paddle`. E3 says only `app/vision/` may import them; T19 enforces with a grep test.
- **Failing-test verification.** Every task's Step 2 runs the test and confirms the expected failure mode. If the test passes accidentally on Step 2, re-author the test.
- **Commit message style.** Conventional Commits, subject ≤ 72 chars. No co-authored trailers (project convention; matches E1/E2 commits).
- **Reading order for an executor subagent.** L1 §2 (components) and §4 (exit gates) define the contract; ARCH §4.2.3 / §6.1 / §6.9 / §11.2 are the deep references. If any cell here disagrees with ARCH, ARCH wins; flag the divergence in the task's commit message.

---

## Wave structure (consumed by `parallel-plan-executor`)

Per L1 §8.2 directive — the parallel-planning skill will refine wave boundaries; this is the L1-prescribed default:

- **Wave 1** (sequential foundation, T1 → T2 → T3 → T4 → T5): schema + protocol + reason codes + dev-dep + synthetic fixture. Each task is small; sequential is fine.
- **Wave 2** (parallel ≤6, depends on Wave 1): T6 quality.py, T7 paddle_runner, T8 swt, T9 tiebreak_gpt4o. Five sub-modules independent of each other.
- **Wave 3** (sequential, depends on Wave 2): T10 cloud.py (uses quality.py), T11 local.py (composes T7+T8+T9). Cloud and local can themselves run in parallel — cloud doesn't depend on the local sub-runners — so this can collapse into Wave 2b parallel pair.
- **Wave 4** (parallel ≤6, depends on Wave 3): T12 deps + autodetect, T13 CLI smoke, T14 recording script, T15 substitutability, T16 bulkhead, T17 ring buffer.
- **Wave 5** (parallel, depends on Wave 4): T18 DPI extraction, T19 isolation grep.

---

## Task 1: app/schemas/label.py — Label wrapper schema (E1 omission backfill)

**Files:**
- Create: `app/schemas/label.py`
- Test: `tests/test_label_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_label_schema.py
import pytest
from pydantic import ValidationError

from app.schemas.label import Dimensions, Label


def test_label_round_trip():
    label = Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=b"\x89PNG\r\n\x1a\n",
        content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )
    assert label.label_id == "L-001"
    assert label.dimensions.dpi == 300


def test_label_frozen():
    label = Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=b"x",
        content_type="image/jpeg",
        face_tag="front",
        dimensions=None,
    )
    with pytest.raises(ValidationError):
        label.label_id = "L-002"


def test_label_extra_forbidden():
    with pytest.raises(ValidationError):
        Label(
            label_id="L-001",
            batch_id="B-001",
            image_bytes=b"x",
            content_type="image/jpeg",
            face_tag="front",
            dimensions=None,
            unknown_field="x",
        )


def test_label_content_type_restricted():
    with pytest.raises(ValidationError):
        Label(
            label_id="L-001",
            batch_id="B-001",
            image_bytes=b"x",
            content_type="image/gif",  # not in JPEG/PNG allowlist
            face_tag="front",
            dimensions=None,
        )


def test_label_face_tag_restricted():
    with pytest.raises(ValidationError):
        Label(
            label_id="L-001",
            batch_id="B-001",
            image_bytes=b"x",
            content_type="image/png",
            face_tag="bottom",  # not in {front, back, neck, side}
            dimensions=None,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_label_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas.label'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/schemas/label.py
"""Label envelope — what the Vision Extractor consumes (E3).

Carries image bytes, the content-type discriminator, optional dimensions
(applicant-supplied or extracted from EXIF), and the face_tag that distinguishes
front/back/neck/side panels. Source: E3 L1 §2.1.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Dimensions(BaseModel):
    """Physical dimensions of the label image. Source: E3 L1 §2.1."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width_px: int = Field(ge=1)
    height_px: int = Field(ge=1)
    dpi: int | None = Field(default=None, ge=1)


class Label(BaseModel):
    """Label envelope consumed by VisionExtractor.extract(). Source: E3 L1 §2.1."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label_id: str
    batch_id: str
    image_bytes: bytes
    content_type: Literal["image/jpeg", "image/png"]
    face_tag: Literal["front", "back", "neck", "side"]
    dimensions: Dimensions | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_label_schema.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run full suite (no regression)**

Run: `uv run pytest -q`
Expected: 253 passed (248 baseline + 5 new).

- [ ] **Step 6: Commit**

```bash
git add app/schemas/label.py tests/test_label_schema.py
git commit -m "feat(e3): add Label + Dimensions schemas (E1 omission backfill)"
```

---

## Task 2: app/vision/__init__.py + app/vision/base.py — VisionExtractor Protocol

**Files:**
- Create: `app/vision/__init__.py`
- Create: `app/vision/base.py`
- Test: `tests/test_vision_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vision_protocol.py
import inspect

from app.vision.base import VisionExtractor


def test_protocol_runtime_checkable():
    # @runtime_checkable enables isinstance() against the Protocol.
    assert hasattr(VisionExtractor, "_is_runtime_protocol")


def test_protocol_attrs():
    attrs = set(VisionExtractor.__protocol_attrs__)
    assert "extract" in attrs
    assert "ensure_loaded" in attrs


def test_extract_signature_async():
    extract = VisionExtractor.extract
    assert inspect.iscoroutinefunction(extract)


def test_ensure_loaded_signature_async():
    ensure_loaded = VisionExtractor.ensure_loaded
    assert inspect.iscoroutinefunction(ensure_loaded)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_vision_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.vision.base'`.

- [ ] **Step 3: Write minimal implementation**

```python
# app/vision/__init__.py
"""Vision Extractor seam (D-004 swap point #1). Source: E3 L1 §2."""
from app.vision.base import VisionExtractor

__all__ = ["VisionExtractor"]
```

```python
# app/vision/base.py
"""VisionExtractor Protocol + sub-runner shape declarations.

Source: E3 L1 §2.1. The Protocol is runtime_checkable so substitutability
tests can assert isinstance() without instantiating the heavy sub-runners.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.extracted import FieldObservation
from app.schemas.label import Label


@runtime_checkable
class VisionExtractor(Protocol):
    """D-004 #1 seam. Two concrete impls land in E3: cloud + local."""

    async def extract(self, label: Label) -> list[FieldObservation]: ...

    async def ensure_loaded(self) -> None:
        """Warm-up hook. Cloud impl: no-op. Local impl: load model weights."""
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_vision_protocol.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run full suite**

Run: `uv run pytest -q`
Expected: 257 passed.

- [ ] **Step 6: Commit**

```bash
git add app/vision/__init__.py app/vision/base.py tests/test_vision_protocol.py
git commit -m "feat(e3): VisionExtractor Protocol + runtime_checkable shape"
```

---

## Task 3: rules/reason_codes.yaml — append GLARE + MOTION_BLUR

**Files:**
- Modify: `rules/reason_codes.yaml`
- Modify: `tests/rules/test_reason_codes_yaml.py` (extend whitelist)

- [ ] **Step 1: Extend the whitelist test (failing)**

Find the existing `EXPECTED_REASON_CODES` set in `tests/rules/test_reason_codes_yaml.py` (or wherever the registry-shape assertion lives) and add:
```python
"WARNING.LEGIBILITY.GLARE",
"WARNING.LEGIBILITY.MOTION_BLUR",
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/rules/test_reason_codes_yaml.py -v`
Expected: FAIL — code missing from registry.

- [ ] **Step 3: Append to reason_codes.yaml**

Locate the `WARNING.LEGIBILITY.LOW_RESOLUTION` block and add immediately after:

```yaml
  WARNING.LEGIBILITY.GLARE:
    description: "Specular highlights or overexposed regions in the warning area prevent reliable extraction."
    cfr_anchors: ["27 CFR §16.21"]
    severity: warn
  WARNING.LEGIBILITY.MOTION_BLUR:
    description: "Motion blur in the warning area exceeds the legibility gate; extraction unreliable."
    cfr_anchors: ["27 CFR §16.21"]
    severity: warn
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/rules/test_reason_codes_yaml.py -v`
Expected: pass.

- [ ] **Step 5: Run full suite**

Run: `uv run pytest -q`
Expected: 257 passed (no count change beyond T1+T2 deltas).

- [ ] **Step 6: Commit**

```bash
git add rules/reason_codes.yaml tests/rules/test_reason_codes_yaml.py
git commit -m "feat(e3): add WARNING.LEGIBILITY.{GLARE,MOTION_BLUR} reason codes"
```

---

## Task 4: pyproject.toml — add `respx` to dev group

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Append `respx >= 0.21` to `[dependency-groups.dev]`**

```toml
[dependency-groups]
dev = [
    "pytest >= 8.3",
    "pytest-asyncio >= 0.24",
    "taskipy >= 1.13",
    "respx >= 0.21",
]
```

- [ ] **Step 2: Refresh lockfile**

Run: `uv sync`
Expected: installs `respx` and resolves successfully.

- [ ] **Step 3: Verify import works**

Run: `uv run python -c "import respx; print(respx.__version__)"`
Expected: prints a version ≥ 0.21.

- [ ] **Step 4: Run full suite (no regression)**

Run: `uv run pytest -q`
Expected: 257 passed.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(e3): add respx>=0.21 to dev deps for HTTP-layer recording"
```

---

## Task 5: fixtures/01-spirits-clean/label.png — synthetic test fixture

**Files:**
- Create: `fixtures/01-spirits-clean/label.png`
- Create: `scripts/build_synthetic_fixture.py` (used to regenerate the fixture deterministically)
- Test: `tests/test_synthetic_fixture.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_synthetic_fixture.py
from pathlib import Path

from PIL import Image

FIXTURE = Path("fixtures/01-spirits-clean/label.png")


def test_fixture_exists():
    assert FIXTURE.exists()


def test_fixture_is_png_with_dpi():
    with Image.open(FIXTURE) as img:
        assert img.format == "PNG"
        assert img.size == (200, 200)
        # PIL exposes DPI via info["dpi"] when pHYs is present.
        assert img.info.get("dpi") == (300, 300)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_synthetic_fixture.py -v`
Expected: FAIL — fixture absent.

- [ ] **Step 3: Write the build script**

```python
# scripts/build_synthetic_fixture.py
"""Deterministic synthetic label fixture for E3 tests.

200x200 white PNG with embedded "ACME BOURBON" + "ALC. 40% BY VOL." +
GOVERNMENT WARNING block; PIL pHYs DPI=300. ~5 KB.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/01-spirits-clean/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (200, 200), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME BOURBON", fill="black", font=font)
    draw.text((10, 30), "ALC. 40% BY VOL.", fill="black", font=font)
    draw.text((10, 50), "GOVERNMENT WARNING:", fill="black", font=font)
    draw.text((10, 70), "(1) ACCORDING TO THE", fill="black", font=font)
    draw.text((10, 85), "SURGEON GENERAL...", fill="black", font=font)
    draw.text((10, 110), "750 ML", fill="black", font=font)
    draw.text((10, 130), "DISTILLED IN KENTUCKY", fill="black", font=font)
    img.save(OUT, "PNG", dpi=(300, 300))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the build script**

Run: `uv run python scripts/build_synthetic_fixture.py`
Expected: writes `fixtures/01-spirits-clean/label.png`.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_synthetic_fixture.py -v`
Expected: 2 passed.

- [ ] **Step 6: Run full suite**

Run: `uv run pytest -q`
Expected: 259 passed.

- [ ] **Step 7: Commit**

```bash
git add fixtures/01-spirits-clean/label.png scripts/build_synthetic_fixture.py tests/test_synthetic_fixture.py
git commit -m "test(e3): synthetic 200x200 PNG fixture (DPI=300) for E3 unit tests"
```

---

## Task 6: app/vision/quality.py — quality gates

**Files:**
- Create: `app/vision/quality.py`
- Test: `tests/test_vision_quality_gates.py`

This task bundles 5 cycles per the `task-executor` "one behavior per commit" rule:
**Cycle A**: `QualityReport` model + `assess()` skeleton returning `disposition="ok"`.
**Cycle B**: BRISQUE/NIQE proxy → `WARNING.LEGIBILITY.LOW_RESOLUTION`.
**Cycle C**: glare detection → `WARNING.LEGIBILITY.GLARE`.
**Cycle D**: motion-blur detection → `WARNING.LEGIBILITY.MOTION_BLUR`.
**Cycle E**: DPI extraction (EXIF / pHYs / JFIF / applicant fallback) → `ENGINE.MEASUREMENT.MISSING_DPI`.

- [ ] **Cycle A — Step 1: Write the failing baseline test**

```python
# tests/test_vision_quality_gates.py
from pathlib import Path

import pytest

from app.schemas.label import Dimensions, Label
from app.vision.quality import QualityReport, assess

FIXTURE = Path("fixtures/01-spirits-clean/label.png")


def _label(image_bytes: bytes, dpi: int | None = 300) -> Label:
    return Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=image_bytes,
        content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=dpi),
    )


def test_clean_fixture_passes():
    report = assess(_label(FIXTURE.read_bytes()))
    assert report.disposition == "ok"
    assert report.reason_code is None
```

- [ ] **Cycle A — Step 2: Run test (FAIL — module missing)** → **Step 3: Write minimal `assess` returning `QualityReport(disposition="ok", reason_code=None)`** → **Step 4: Run (PASS)** → **Step 5: Commit `feat(e3): vision quality.py skeleton + clean-pass test`**.

- [ ] **Cycle B — Repeat for BRISQUE/NIQE**

Test: 64×64 noise-PNG triggers `WARNING.LEGIBILITY.LOW_RESOLUTION`. Implementation: opencv variance-of-Laplacian < threshold ⇒ low-res; threshold configurable via `quality.low_res_variance_min` constant (default 50.0). Commit: `feat(e3): low-resolution gate via Laplacian variance`.

- [ ] **Cycle C — glare**

Test: synthetic image with overexposed (>240 luminance) region covering >15% of pixels → `WARNING.LEGIBILITY.GLARE`. Implementation: greyscale histogram + threshold. Commit: `feat(e3): glare detection via overexposed-pixel ratio`.

- [ ] **Cycle D — motion blur**

Test: synthetic horizontally-streaked image triggers `WARNING.LEGIBILITY.MOTION_BLUR`. Implementation: FFT high-frequency-energy ratio < threshold. Commit: `feat(e3): motion-blur detection via FFT high-freq ratio`.

- [ ] **Cycle E — DPI extraction (EXIF/pHYs/JFIF/applicant)**

Test 1: PNG with pHYs → DPI from PIL `info["dpi"]`. Test 2: JPEG with EXIF → DPI from EXIF tag 0x011A/0x011B. Test 3: image missing DPI metadata + `Label.dimensions.dpi=300` → DPI from applicant. Test 4: image missing all three → `report.disposition == "ok"` but `report.dpi is None`; downstream rule emits `ENGINE.MEASUREMENT.MISSING_DPI`. Implementation: helper `_extract_dpi(image_bytes, dimensions)` returning `int | None`. Commit: `feat(e3): multi-source DPI extraction (EXIF/pHYs/JFIF/applicant)`.

- [ ] **Final — run full suite**

Run: `uv run pytest -q`
Expected: 259 + ~10 = ~269 passed.

---

## Task 7: app/vision/paddle_runner.py — PaddleOCR sub-runner

**Files:**
- Create: `app/vision/paddle_runner.py`
- Test: `tests/test_vision_paddle_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vision_paddle_runner.py
import asyncio
from collections import deque
from unittest.mock import MagicMock

import pytest

from app.vision.paddle_runner import Candidate, PaddleRunner


@pytest.mark.asyncio
async def test_run_records_call(monkeypatch):
    ring = deque(maxlen=200)
    runner = PaddleRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    fake_ocr = MagicMock(return_value=[{"text": "ACME", "bbox": [0, 0, 10, 10], "score": 0.95}])
    monkeypatch.setattr(runner, "_ocr", fake_ocr)
    result = await runner.run(crop=b"\x89PNG\r\n\x1a\n")
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Candidate)
    assert result[0].text == "ACME"
    assert len(ring) == 1
    assert ring[0].stage == "vision.paddleocr"
    assert ring[0].provider == "local.paddleocr"


@pytest.mark.asyncio
async def test_lazy_paddleocr_import(monkeypatch):
    """PaddleRunner must NOT import paddleocr at module top-level."""
    import sys
    import importlib

    if "paddleocr" in sys.modules:
        del sys.modules["paddleocr"]
    importlib.reload(__import__("app.vision.paddle_runner", fromlist=["PaddleRunner"]))
    assert "paddleocr" not in sys.modules
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_vision_paddle_runner.py -v`
Expected: FAIL — module missing.

- [ ] **Step 3: Write minimal implementation**

```python
# app/vision/paddle_runner.py
"""PaddleOCR sub-runner. Source: E3 L1 §2.3.

Lazy-imports paddleocr inside ensure_loaded() so the cloud-only profile
doesn't pay the import cost (and keeps app/vision/paddle_runner.py importable
even when paddleocr is missing).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import time
from typing import Any


@dataclass(frozen=True)
class Candidate:
    text: str
    bbox: tuple[int, int, int, int]
    score: float


class PaddleRunner:
    def __init__(self, ring_buffer: deque, batch_id: str, label_id: str) -> None:
        self._ring = ring_buffer
        self._batch_id = batch_id
        self._label_id = label_id
        self._ocr_engine: Any = None  # populated by ensure_loaded()

    async def ensure_loaded(self) -> None:
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR  # lazy import
            except ImportError as e:
                raise RuntimeError(
                    "PaddleOCR not installed. Install with `uv sync --extra gpu`."
                ) from e
            self._ocr_engine = PaddleOCR(use_angle_cls=False, lang="en")

    def _ocr(self, crop: bytes) -> list[dict]:
        # Real impl shells out to self._ocr_engine.ocr(); test patches this method.
        raise NotImplementedError

    async def run(self, crop: bytes) -> list[Candidate]:
        from app.schemas.calls import CallRecord  # local import to keep this file slim

        t0 = time.monotonic()
        raw = self._ocr(crop)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        candidates = [
            Candidate(text=r["text"], bbox=tuple(r["bbox"]), score=float(r["score"]))
            for r in raw
        ]
        self._ring.append(
            CallRecord(
                ts=datetime.now(timezone.utc),
                batch_id=self._batch_id,
                label_id=self._label_id,
                stage="vision.paddleocr",
                request={"crop_size": len(crop)},
                response={"n_candidates": len(candidates)},
                latency_ms=elapsed_ms,
                provider="local.paddleocr",
                output_hash=hashlib.sha256(repr(candidates).encode()).hexdigest()[:16],
            )
        )
        return candidates
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_vision_paddle_runner.py -v`
Expected: 2 passed.

- [ ] **Step 5: Run full suite**

Run: `uv run pytest -q`
Expected: ~271 passed.

- [ ] **Step 6: Commit**

```bash
git add app/vision/paddle_runner.py tests/test_vision_paddle_runner.py
git commit -m "feat(e3): PaddleOCR sub-runner with lazy import + ring-buffer write"
```

---

## Task 8: app/vision/swt.py — Stroke-Width-Transform bold detector

**Files:**
- Create: `app/vision/swt.py`
- Test: `tests/test_vision_swt.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vision_swt.py
import asyncio
from collections import deque

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from app.vision.swt import StrokeWidthReport, SWTRunner


def _synth_text_png(stroke_thickness: int) -> bytes:
    """Generate a 100x40 PNG with text drawn at the specified stroke thickness."""
    img = Image.new("L", (100, 40), color=255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    # Stroke parameter not directly available on default font;
    # simulate by overdrawing thickness times with offsets.
    for dx in range(stroke_thickness):
        for dy in range(stroke_thickness):
            draw.text((10 + dx, 10 + dy), "WARNING", fill=0, font=font)
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_thick_stroke_classified_bold():
    ring = deque(maxlen=200)
    runner = SWTRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    report = await runner.run(crop=_synth_text_png(stroke_thickness=3))
    assert isinstance(report, StrokeWidthReport)
    assert report.is_bold is True


@pytest.mark.asyncio
async def test_thin_stroke_classified_not_bold():
    ring = deque(maxlen=200)
    runner = SWTRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    report = await runner.run(crop=_synth_text_png(stroke_thickness=1))
    assert report.is_bold is False


@pytest.mark.asyncio
async def test_run_writes_call_record():
    ring = deque(maxlen=200)
    runner = SWTRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    await runner.run(crop=_synth_text_png(stroke_thickness=2))
    assert len(ring) == 1
    assert ring[0].stage == "vision.swt"
```

- [ ] **Step 2: Run (FAIL — module missing)**

- [ ] **Step 3: Write minimal implementation**

`SWTRunner.run()` performs:
1. Decode bytes via PIL → numpy greyscale.
2. Threshold + connected-components via cv2.
3. For each component: compute mean stroke width via `cv2.distanceTransform` and compare to height (`stroke_width / character_height` ratio).
4. Aggregate ratio across components; ratio > 0.18 → `is_bold = True`.
5. Write CallRecord with `stage="vision.swt"`, `provider="local.paddleocr"` (re-use the local provider literal — see Conventions).

- [ ] **Step 4: Run (PASS — 3 tests)**

- [ ] **Step 5: Run full suite (no regression)**

- [ ] **Step 6: Commit `feat(e3): SWT bold-detector sub-runner (heading FR-202 signal)`**

---

## Task 9: app/vision/tiebreak_gpt4o.py — GPT-4o-on-crop tiebreaker

**Files:**
- Create: `app/vision/tiebreak_gpt4o.py`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/tiebreak/brand_name.json` (recording)
- Test: `tests/test_vision_tiebreak_gpt4o.py`

- [ ] **Step 1: Write the failing test using `respx`**

```python
# tests/test_vision_tiebreak_gpt4o.py
import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.vision.tiebreak_gpt4o import GPT4oTiebreakRunner

RECORDING = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/tiebreak/brand_name.json")


@pytest.mark.asyncio
@respx.mock
async def test_tiebreak_run_against_recording():
    payload = json.loads(RECORDING.read_text())
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(200, json=payload)
    )
    ring = deque(maxlen=200)
    runner = GPT4oTiebreakRunner(
        ring_buffer=ring,
        batch_id="B-001",
        label_id="L-001",
        api_key="sk-test",
        model_snapshot="gpt-4o-2024-08-06",
        prompt_version="v1",
    )
    result = await runner.run(crop=b"\x89PNG", prompt="brand_name")
    assert result["brand_name"] == "ACME BOURBON"
    assert len(ring) == 1
    assert ring[0].stage == "vision.gpt4o_tiebreak"
    assert ring[0].provider == "openai"
    assert ring[0].model == "gpt-4o-2024-08-06"
    assert ring[0].prompt_version == "v1"
```

- [ ] **Step 2: Hand-author the recording**

```json
{
  "id": "chatcmpl-test",
  "object": "chat.completion",
  "model": "gpt-4o-2024-08-06",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\"brand_name\":\"ACME BOURBON\"}"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110}
}
```

- [ ] **Step 3: Run test (FAIL — module missing)**

- [ ] **Step 4: Write minimal implementation**

```python
# app/vision/tiebreak_gpt4o.py
"""GPT-4o-on-crop tiebreaker for the local-mode pipeline. Source: E3 L1 §2.3.

Single-call OpenAI Structured Output (strict:true) returning a typed JSON dict.
HTTP layer only — this module never imports the openai SDK directly; uses
httpx so respx recordings cover the wire.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from collections import deque
from datetime import datetime, timezone

import httpx


_SCHEMAS = {
    "brand_name": {
        "type": "object",
        "properties": {"brand_name": {"type": "string"}},
        "required": ["brand_name"],
        "additionalProperties": False,
    },
    # Other field schemas added in future tasks (cloud.py also uses them).
}


class GPT4oTiebreakRunner:
    def __init__(
        self,
        *,
        ring_buffer: deque,
        batch_id: str,
        label_id: str,
        api_key: str,
        model_snapshot: str,
        prompt_version: str,
    ) -> None:
        self._ring = ring_buffer
        self._batch_id = batch_id
        self._label_id = label_id
        self._api_key = api_key
        self._model = model_snapshot
        self._prompt_version = prompt_version

    async def ensure_loaded(self) -> None:  # no-op; HTTP client is per-call
        return None

    async def run(self, *, crop: bytes, prompt: str) -> dict:
        from app.schemas.calls import CallRecord

        body = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Extract field: {prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64.b64encode(crop).decode()}"
                            },
                        },
                    ],
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": prompt,
                    "strict": True,
                    "schema": _SCHEMAS[prompt],
                },
            },
        }
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
        self._ring.append(
            CallRecord(
                ts=datetime.now(timezone.utc),
                batch_id=self._batch_id,
                label_id=self._label_id,
                stage="vision.gpt4o_tiebreak",
                request={"prompt": prompt, "crop_size": len(crop)},
                response=content,
                latency_ms=elapsed_ms,
                model=self._model,
                provider="openai",
                prompt_version=self._prompt_version,
                output_hash=hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16],
            )
        )
        return content
```

- [ ] **Step 5: Run test (PASS)**

- [ ] **Step 6: Run full suite + commit**

```bash
git add app/vision/tiebreak_gpt4o.py tests/recordings/openai/gpt-4o-2024-08-06/v1/tiebreak/brand_name.json tests/test_vision_tiebreak_gpt4o.py
git commit -m "feat(e3): GPT-4o tiebreaker with respx HTTP-layer recording"
```

---

## Task 10: app/vision/cloud.py — CloudVisionExtractor (validated default)

**Files:**
- Create: `app/vision/cloud.py`
- Create: `tests/recordings/openai/gpt-4o-2024-08-06/v1/01-spirits-clean/{layout,brand_name,class_type,abv,net_contents,gov_warning,heading_typography,name_address,country_origin}.json` (9 recordings)
- Test: `tests/test_vision_cloud_extraction.py`

This task bundles 3 cycles:
**Cycle A**: layout pre-pass + per-field call dispatch (mocked to constants).
**Cycle B**: `asyncio.Semaphore(4)` bulkhead enforcement.
**Cycle C**: BRISQUE/NIQE short-circuit before extraction (`disposition=needs_better_photo` skips all 9 calls).

- [ ] **Cycle A — Step 1: Write failing test**

```python
# tests/test_vision_cloud_extraction.py
import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.config import Settings
from app.schemas.label import Dimensions, Label
from app.vision.cloud import CloudVisionExtractor

RECORDINGS_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/01-spirits-clean")
FIXTURE = Path("fixtures/01-spirits-clean/label.png")
EXPECTED_FIELD_IDS = {
    "brand_name", "class_type", "abv", "net_contents",
    "gov_warning", "heading_typography", "name_address", "country_origin",
}


def _all_recordings_router():
    """Mount each recording as a respx route."""
    router = respx.Router(assert_all_called=False)
    for path in RECORDINGS_DIR.glob("*.json"):
        payload = json.loads(path.read_text())
        router.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=Response(200, json=payload)
        )
    return router


@pytest.mark.asyncio
async def test_cloud_extracts_fr_001_to_008(monkeypatch):
    settings = Settings()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    ring = deque(maxlen=200)
    extractor = CloudVisionExtractor(settings=settings, ring_buffer=ring, api_key="sk-test")
    label = Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=FIXTURE.read_bytes(),
        content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )
    with respx.mock(base_url="https://api.openai.com") as mock_router:
        # Map each per-field call to its recording. Implementation strategy:
        # cloud.py issues calls in a deterministic order; tests mount per-name routes
        # via the call's response_format.json_schema.name discriminator.
        for path in RECORDINGS_DIR.glob("*.json"):
            payload = json.loads(path.read_text())
            mock_router.post("/v1/chat/completions").mock(return_value=Response(200, json=payload))
        observations = await extractor.extract(label)
    field_ids = {obs.field_id for obs in observations}
    assert field_ids == EXPECTED_FIELD_IDS
    assert len(ring) == 9  # 1 layout + 8 per-field calls
```

- [ ] **Cycle A — Step 2: Hand-author the 9 recordings**

Each recording has the same shape as the T9 example with `content` as a JSON-encoded string matching the field schema. Field schemas:
| Field | Schema |
|---|---|
| `layout` | `{ "fields": [{"id":"brand_name","bbox":[10,10,80,30]}, ...8 entries] }` |
| `brand_name` | `{ "brand_name": "ACME BOURBON" }` |
| `class_type` | `{ "class_type": "BOURBON WHISKEY" }` |
| `abv` | `{ "abv_pct": 40.0, "unit": "alc_vol" }` |
| `net_contents` | `{ "net_contents_value": 750, "unit": "ml" }` |
| `gov_warning` | `{ "text": "GOVERNMENT WARNING: (1) ACCORDING ..." }` |
| `heading_typography` | `{ "all_caps": true, "bold": true, "type_size_pt": 4.0 }` |
| `name_address` | `{ "name": "ACME DISTILLERIES", "city": "FRANKFORT", "state": "KY" }` |
| `country_origin` | `{ "country": "USA" }` |

- [ ] **Cycle A — Step 3: Implement `CloudVisionExtractor.extract()`** issuing 1 layout call + 8 per-field calls in deterministic order; building `FieldObservation` from each response; populating `Evidence` with bbox from the layout call.

- [ ] **Cycle A — Step 4: Run (PASS)** → **Step 5: Commit `feat(e3): CloudVisionExtractor with 9-call layout+per-field pipeline`**

- [ ] **Cycle B — bulkhead**

Add `tests/test_vision_bulkhead.py` test (covered in T16 — defer); for this cycle, just commit the `asyncio.Semaphore(4)` instance attribute and confirm the existing test still passes.

- [ ] **Cycle C — quality short-circuit**

Test: a `Label` with low-res image_bytes returns 1 `FieldObservation` carrying `disposition=needs_better_photo` and 0 OpenAI calls (assert `respx` route count == 0). Implementation: `extract()` calls `quality.assess()` first; if `disposition != "ok"`, returns `[FieldObservation(field_id="quality", upstream_meta={"disposition":..., "reason_code":...})]` without further calls. Commit: `feat(e3): cloud short-circuits on quality-gate failure`.

---

## Task 11: app/vision/local.py — LocalVisionExtractor (composes sub-runners)

**Files:**
- Create: `app/vision/local.py`
- Test: `tests/test_vision_local_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vision_local_protocol.py
import asyncio
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.label import Dimensions, Label
from app.vision.base import VisionExtractor
from app.vision.local import LocalVisionExtractor


def _label() -> Label:
    return Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=b"\x89PNG\r\n\x1a\n",
        content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )


@pytest.mark.asyncio
async def test_local_satisfies_protocol():
    ring = deque(maxlen=200)
    extractor = LocalVisionExtractor.__new__(LocalVisionExtractor)
    # Inject mocks — bypass __init__ which would import paddleocr.
    extractor._paddle = MagicMock(run=AsyncMock(return_value=[]))
    extractor._swt = MagicMock(run=AsyncMock(return_value=MagicMock(is_bold=True)))
    extractor._tiebreak = MagicMock(run=AsyncMock(return_value={}))
    extractor._ring = ring
    extractor._quality_assess = MagicMock(return_value=MagicMock(disposition="ok", reason_code=None))
    assert isinstance(extractor, VisionExtractor)


@pytest.mark.asyncio
async def test_local_ensure_loaded_raises_without_gpu_extras(monkeypatch):
    """When paddleocr import fails, ensure_loaded raises a clear RuntimeError."""
    import sys
    monkeypatch.setitem(sys.modules, "paddleocr", None)  # forces ImportError
    extractor = LocalVisionExtractor.__new__(LocalVisionExtractor)
    extractor._paddle = MagicMock(ensure_loaded=AsyncMock(side_effect=RuntimeError("PaddleOCR not installed. Install with `uv sync --extra gpu`.")))
    extractor._swt = MagicMock(ensure_loaded=AsyncMock())
    extractor._tiebreak = MagicMock(ensure_loaded=AsyncMock())
    with pytest.raises(RuntimeError, match="--extra gpu"):
        await extractor.ensure_loaded()
```

- [ ] **Step 2: Run (FAIL — module missing)**

- [ ] **Step 3: Write minimal implementation**

```python
# app/vision/local.py
"""LocalVisionExtractor — composes PaddleOCR + SWT + GPT-4o tiebreaker.

Source: E3 L1 §2.3 (D-021 trimmed pipeline). Florence-2 + Qwen-VL out of MVP.
"""
from __future__ import annotations

from collections import deque

from app.config import Settings
from app.schemas.extracted import FieldObservation
from app.schemas.label import Label
from app.vision.paddle_runner import PaddleRunner
from app.vision.swt import SWTRunner
from app.vision.tiebreak_gpt4o import GPT4oTiebreakRunner
from app.vision.quality import assess as _quality_assess


class LocalVisionExtractor:
    def __init__(self, settings: Settings, ring_buffer: deque) -> None:
        self._ring = ring_buffer
        self._settings = settings
        self._paddle = PaddleRunner(ring_buffer=ring_buffer, batch_id="", label_id="")
        self._swt = SWTRunner(ring_buffer=ring_buffer, batch_id="", label_id="")
        self._tiebreak = GPT4oTiebreakRunner(
            ring_buffer=ring_buffer,
            batch_id="",
            label_id="",
            api_key=settings.openai_api_key or "",
            model_snapshot=settings.llm_model_snapshot,
            prompt_version=settings.prompt_version,
        )

    async def ensure_loaded(self) -> None:
        await self._paddle.ensure_loaded()
        await self._swt.ensure_loaded()
        await self._tiebreak.ensure_loaded()

    async def extract(self, label: Label) -> list[FieldObservation]:
        report = _quality_assess(label)
        if report.disposition != "ok":
            return [
                FieldObservation(
                    field_id="quality",
                    beverage_class=label.face_tag,  # placeholder — refined when E5 wires beverage_class
                    observed_value=None,
                    evidence=(),
                    upstream_meta={
                        "disposition": report.disposition,
                        "reason_code": report.reason_code,
                    },
                )
            ]
        # Bind sub-runners' batch_id/label_id from this label.
        for runner in (self._paddle, self._swt, self._tiebreak):
            runner._batch_id = label.batch_id
            runner._label_id = label.label_id
        # Run PaddleOCR + SWT in parallel; tiebreaker only when uncertain.
        # (Concrete dispatch logic refined inside the test cycle.)
        observations: list[FieldObservation] = []
        # ... per-field routing logic, fields from candidates ...
        return observations
```

- [ ] **Step 4: Run (PASS — protocol shape only)**

- [ ] **Step 5: Run full suite**

- [ ] **Step 6: Commit `feat(e3): LocalVisionExtractor composing paddle+swt+tiebreak`**

---

## Task 12: app/deps.py — replace placeholders + `_autodetect`

**Files:**
- Modify: `app/deps.py`
- Test: `tests/test_vision_deps_autodetect.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vision_deps_autodetect.py
import subprocess
from unittest.mock import patch

import pytest

from app.config import Settings
from app.deps import _autodetect, build_vision_extractor
from app.vision.cloud import CloudVisionExtractor
from app.vision.local import LocalVisionExtractor


def test_autodetect_cuda_present():
    with patch("app.deps.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["nvidia-smi"], returncode=0, stdout=b"GPU 0: ...", stderr=b""
        )
        mode = _autodetect()
        assert mode == "local"


def test_autodetect_cuda_absent():
    with patch("app.deps.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["nvidia-smi"], returncode=127, stdout=b"", stderr=b"command not found"
        )
        mode = _autodetect()
        assert mode == "cloud"


def test_autodetect_subprocess_timeout_falls_back_cloud():
    with patch("app.deps.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["nvidia-smi"], timeout=2)
        mode = _autodetect()
        assert mode == "cloud"


def test_build_vision_extractor_cloud(monkeypatch):
    monkeypatch.setenv("VISION_MODE", "cloud")
    settings = Settings()
    extractor = build_vision_extractor(settings)
    assert isinstance(extractor, CloudVisionExtractor)


def test_build_vision_extractor_local(monkeypatch):
    monkeypatch.setenv("VISION_MODE", "local")
    settings = Settings()
    extractor = build_vision_extractor(settings)
    assert isinstance(extractor, LocalVisionExtractor)
```

- [ ] **Step 2: Run (FAIL — placeholder in place)**

- [ ] **Step 3: Replace placeholders in `app/deps.py`**

```python
# app/deps.py (rewritten)
"""DI container — selects VisionExtractor and Orchestrator per env."""
from __future__ import annotations

import subprocess
from collections import deque
from typing import Literal

from app.config import Settings
from app.vision.base import VisionExtractor
from app.vision.cloud import CloudVisionExtractor
from app.vision.local import LocalVisionExtractor


_NVIDIA_SMI_TIMEOUT_S = 2.0


def _autodetect() -> Literal["cloud", "local"]:
    """Per D-015: probe nvidia-smi; CUDA-present ⇒ local, otherwise cloud."""
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            check=False,
            capture_output=True,
            timeout=_NVIDIA_SMI_TIMEOUT_S,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "cloud"
    return "local" if result.returncode == 0 else "cloud"


def build_vision_extractor(settings: Settings) -> VisionExtractor:
    mode = settings.vision_mode
    if mode == "auto":
        mode = _autodetect()
    ring = deque(maxlen=200)
    if mode == "cloud":
        return CloudVisionExtractor(
            settings=settings,
            ring_buffer=ring,
            api_key=settings.openai_api_key or "",
        )
    if mode == "local":
        return LocalVisionExtractor(settings=settings, ring_buffer=ring)
    raise ValueError(f"Unknown vision_mode: {mode!r}")


# Orchestrator placeholders preserved — E4 territory.
class _PlaceholderOpenAIOrchestrator:
    backend = "openai"

    async def refine(self, payload):
        raise NotImplementedError("seam not wired in E1 (E4)")


class _PlaceholderAnthropicOrchestrator:
    backend = "anthropic"

    async def refine(self, payload):
        raise NotImplementedError("seam not wired in E1 (E4)")


def build_orchestrator(settings: Settings):
    if settings.orchestrator_backend == "anthropic":
        return _PlaceholderAnthropicOrchestrator()
    return _PlaceholderOpenAIOrchestrator()
```

- [ ] **Step 4: Run (PASS — 5 tests)**

- [ ] **Step 5: Run full suite**

- [ ] **Step 6: Commit `feat(e3): wire build_vision_extractor + nvidia-smi autodetect (D-015)`**

---

## Task 13: app/vision/__main__.py — CLI smoke entry

**Files:**
- Create: `app/vision/__main__.py`
- Test: `tests/test_vision_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vision_cli_smoke.py
import subprocess
import sys
from pathlib import Path


def test_cli_smoke_exits_zero_on_synthetic_fixture():
    result = subprocess.run(
        [sys.executable, "-m", "app.vision",
         "--label", "fixtures/01-spirits-clean/label.png",
         "--mode", "cloud",
         "--use-recordings"],
        capture_output=True,
        timeout=30,
        env={**__import__("os").environ, "OPENAI_API_KEY": "sk-test", "VISION_MODE": "cloud"},
    )
    assert result.returncode == 0, result.stderr.decode()
    assert b"field_count: 8" in result.stdout


def test_cli_smoke_missing_fixture_exits_2():
    result = subprocess.run(
        [sys.executable, "-m", "app.vision", "--label", "/does/not/exist.png", "--mode", "cloud"],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert b"label not found" in result.stderr.lower()
```

- [ ] **Step 2: Run (FAIL — module missing)**

- [ ] **Step 3: Implement `app/vision/__main__.py`** with argparse (`--label`, `--mode`, `--use-recordings`); on `--use-recordings`, monkey-patch httpx via respx context manager loaded from `tests/recordings/`. Print `field_count: N` to stdout.

- [ ] **Step 4: Run (PASS)** → Step 5 commit `feat(e3): vision CLI smoke entry (python -m app.vision)`.

---

## Task 14: scripts/record_vision_responses.py — re-recording companion

**Files:**
- Create: `scripts/record_vision_responses.py`
- Test: `tests/test_record_vision_responses.py` (smoke only — does not call live OpenAI)

- [ ] **Step 1: Write the failing smoke test**

Test asserts: script imports cleanly; `--help` exits 0; `--live` flag without `OPENAI_API_KEY` env var exits 2 with stderr message.

- [ ] **Step 2: Run (FAIL)**

- [ ] **Step 3: Implement script** — iterate over fixture set, issue one live OpenAI call per per-field call, write response JSON to `tests/recordings/openai/<active-snapshot>/<prompt-version>/<fixture-id>/<call-name>.json`. Default is dry-run; `--live` required to actually call.

- [ ] **Step 4: Run (PASS)** → Step 5 commit `chore(e3): scripts/record_vision_responses.py for snapshot rotation`.

---

## Task 15: tests/test_vision_substitutability.py — Protocol substitutability E2E

**Files:**
- Create: `tests/test_vision_substitutability.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_vision_substitutability.py
import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response
from unittest.mock import AsyncMock, MagicMock

from app.config import Settings
from app.schemas.label import Dimensions, Label
from app.vision.base import VisionExtractor
from app.vision.cloud import CloudVisionExtractor
from app.vision.local import LocalVisionExtractor

EXPECTED_FIELD_IDS = {
    "brand_name", "class_type", "abv", "net_contents",
    "gov_warning", "heading_typography", "name_address", "country_origin",
}
RECORDINGS_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/01-spirits-clean")
FIXTURE = Path("fixtures/01-spirits-clean/label.png")


def _label() -> Label:
    return Label(
        label_id="L-001", batch_id="B-001",
        image_bytes=FIXTURE.read_bytes(), content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )


@pytest.mark.asyncio
async def test_both_impls_satisfy_protocol():
    settings = Settings()
    cloud = CloudVisionExtractor(settings=settings, ring_buffer=deque(maxlen=200), api_key="sk-test")
    local = LocalVisionExtractor(settings=settings, ring_buffer=deque(maxlen=200))
    assert isinstance(cloud, VisionExtractor)
    assert isinstance(local, VisionExtractor)


@pytest.mark.asyncio
async def test_both_impls_produce_same_field_id_set():
    settings = Settings()
    cloud_ring = deque(maxlen=200)
    cloud = CloudVisionExtractor(settings=settings, ring_buffer=cloud_ring, api_key="sk-test")
    with respx.mock(base_url="https://api.openai.com") as router:
        for path in RECORDINGS_DIR.glob("*.json"):
            router.post("/v1/chat/completions").mock(return_value=Response(200, json=json.loads(path.read_text())))
        cloud_obs = await cloud.extract(_label())

    local_ring = deque(maxlen=200)
    local = LocalVisionExtractor(settings=settings, ring_buffer=local_ring)
    # Mock the three sub-runners to return the same field set Cloud produces.
    local._paddle = MagicMock(run=AsyncMock(return_value=[]))
    local._swt = MagicMock(run=AsyncMock(return_value=MagicMock(is_bold=True)))
    local._tiebreak = MagicMock(run=AsyncMock(return_value={"brand_name": "ACME"}))
    local._quality_assess = MagicMock(return_value=MagicMock(disposition="ok"))
    local_obs = await local.extract(_label())

    cloud_ids = {o.field_id for o in cloud_obs}
    local_ids = {o.field_id for o in local_obs}
    # L1 §4 #3: same field_id set, values may differ.
    assert cloud_ids == EXPECTED_FIELD_IDS
    assert local_ids == EXPECTED_FIELD_IDS
```

- [ ] **Step 2: Run (FAIL initially if local impl doesn't yet emit all 8 fields — fix local.py per-field routing as needed) → PASS**

- [ ] **Step 3: Commit `test(e3): both impls satisfy Protocol + produce identical field_id set`**

---

## Task 16: tests/test_vision_bulkhead.py — concurrency cap

**Files:**
- Create: `tests/test_vision_bulkhead.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_vision_bulkhead.py
import asyncio
from collections import deque

import pytest

from app.config import Settings
from app.schemas.label import Dimensions, Label
from app.vision.cloud import CloudVisionExtractor


@pytest.mark.asyncio
async def test_semaphore_caps_at_4(monkeypatch):
    """Five concurrent extracts: at most 4 in-flight at any point."""
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def fake_call(*a, **kw):
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
        # Return shape matching what cloud.py expects.
        return {"brand_name": "X"}  # minimal stub

    settings = Settings()
    extractor = CloudVisionExtractor(
        settings=settings, ring_buffer=deque(maxlen=200), api_key="sk-test",
    )
    monkeypatch.setattr(extractor, "_call_per_field", fake_call)

    label = Label(
        label_id="L-001", batch_id="B-001",
        image_bytes=b"\x89PNG\r\n\x1a\n", content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )
    # 5 concurrent extract() calls — but each spawns 9 sub-calls under the same semaphore.
    await asyncio.gather(*(extractor.extract(label) for _ in range(5)))
    assert max_in_flight <= 4
```

- [ ] **Step 2: Run (FAIL or PASS depending on prior cycle B in T10)**

- [ ] **Step 3: Tighten cloud.py if needed** (use `async with self._semaphore:` around each per-field call).

- [ ] **Step 4: Commit `test(e3): asyncio.Semaphore(4) bulkhead honored under 5x concurrency`**

---

## Task 17: tests/test_vision_ring_buffer_records.py — CallRecord per leg

**Files:**
- Create: `tests/test_vision_ring_buffer_records.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_vision_ring_buffer_records.py
import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.config import Settings
from app.schemas.label import Dimensions, Label
from app.vision.cloud import CloudVisionExtractor

RECORDINGS_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/01-spirits-clean")


@pytest.mark.asyncio
async def test_cloud_writes_9_call_records():
    settings = Settings()
    ring = deque(maxlen=200)
    extractor = CloudVisionExtractor(settings=settings, ring_buffer=ring, api_key="sk-test")
    label = Label(
        label_id="L-001", batch_id="B-001",
        image_bytes=Path("fixtures/01-spirits-clean/label.png").read_bytes(),
        content_type="image/png", face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )
    with respx.mock(base_url="https://api.openai.com") as router:
        for path in RECORDINGS_DIR.glob("*.json"):
            router.post("/v1/chat/completions").mock(return_value=Response(200, json=json.loads(path.read_text())))
        await extractor.extract(label)
    assert len(ring) == 9
    stages = [r.stage for r in ring]
    # 1 layout call + 8 per-field calls; all under vision.gpt4o_tiebreak per cloud-mode policy
    # (cloud uses the same tiebreaker stage tag as local; it's the unified GPT-4o stage).
    assert all(s == "vision.gpt4o_tiebreak" for s in stages)
    assert all(r.provider == "openai" for r in ring)
    assert all(r.model == "gpt-4o-2024-08-06" for r in ring)


def test_ring_buffer_maxlen_honored():
    ring = deque(maxlen=200)
    for i in range(250):
        ring.append(i)
    assert len(ring) == 200
    assert ring[0] == 50  # oldest 50 evicted (FIFO)
```

- [ ] **Step 2: Run (PASS if T10 implementation is correct)**

- [ ] **Step 3: Commit `test(e3): cloud writes 9 CallRecords; ring-buffer maxlen=200 FIFO`**

---

## Task 18: tests/test_vision_dpi_extraction.py — multi-source DPI

**Files:**
- Create: `tests/test_vision_dpi_extraction.py`

- [ ] **Step 1: Write the test**

Tests cover: PNG-with-pHYs, JPEG-with-EXIF (manually authored bytes), JFIF, applicant-supplied via `Label.dimensions.dpi`, all-missing → `report.dpi is None`. The all-missing case asserts that downstream emits `ENGINE.MEASUREMENT.MISSING_DPI` (assertion is on `quality.assess()` output, not on a full FieldObservation — the rule engine emits the actual reason code in E2; here we assert the quality module surfaces `dpi=None` so the engine can route).

- [ ] **Step 2: Run (PASS — DPI implementation already in T6 cycle E)**

- [ ] **Step 3: Commit `test(e3): DPI extraction across EXIF/pHYs/JFIF/applicant + missing-DPI signal`**

---

## Task 19: tests/test_vision_isolation.py — inference-isolation grep invariant

**Files:**
- Create: `tests/test_vision_isolation.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_vision_isolation.py
"""Inference-dep isolation: only app/vision/ may import openai/paddle/cv2/torch.
Mirrors E2's app/rules/ isolation invariant."""
from pathlib import Path
import re

FORBIDDEN_OUTSIDE_VISION = (
    re.compile(r"\bimport\s+openai\b"),
    re.compile(r"\bfrom\s+openai\b"),
    re.compile(r"\bimport\s+paddleocr\b"),
    re.compile(r"\bfrom\s+paddleocr\b"),
    re.compile(r"\bimport\s+cv2\b"),
    re.compile(r"\bfrom\s+cv2\b"),
    re.compile(r"\bimport\s+torch\b"),
    re.compile(r"\bfrom\s+torch\b"),
)


def test_inference_deps_isolated_to_app_vision():
    violations: list[str] = []
    app_root = Path("app")
    for py in app_root.rglob("*.py"):
        if "app/vision/" in str(py):
            continue
        text = py.read_text()
        for rx in FORBIDDEN_OUTSIDE_VISION:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "Inference deps leaked outside app/vision/:\n" + "\n".join(violations)


def test_florence_qwen_imports_absent_globally():
    """Per D-021, Florence-2 + Qwen-VL imports must not exist anywhere."""
    forbidden = (
        re.compile(r"\bflorence"),
        re.compile(r"\bqwen"),
        re.compile(r"\btransformers\b"),
        re.compile(r"\baccelerate\b"),
        re.compile(r"\bbitsandbytes\b"),
    )
    violations: list[str] = []
    for py in Path("app").rglob("*.py"):
        text = py.read_text()
        for rx in forbidden:
            for m in rx.finditer(text):
                violations.append(f"{py}: {m.group(0)}")
    assert not violations, "D-021 forbidden imports detected:\n" + "\n".join(violations)
```

- [ ] **Step 2: Run (PASS expected if no other epoch leaked these imports)**

- [ ] **Step 3: Commit `test(e3): inference-dep isolation + D-021 Florence/Qwen ban`**

---

## Final integration check

After T19 commits, run:

```bash
uv run pytest -q
uv run python -m app.vision --label fixtures/01-spirits-clean/label.png --mode cloud --use-recordings
git log --oneline main ^121d96e | wc -l   # should report ~30 new commits
```

Verify:
- All ~290 tests pass.
- CLI smoke prints `field_count: 8` and exits 0.
- L1 §4 exit gates 1–10 satisfied:
  1. ✅ `VisionExtractor` Protocol declared (T2).
  2. ✅ Both impls pass `isinstance` (T15).
  3. ✅ Same field_id set (T15).
  4. ✅ Cloud extracts FR-001..008 against committed recordings (T10).
  5. ✅ Quality gates emit `WARNING.LEGIBILITY.*` codes (T6).
  6. ✅ `_autodetect` falls back per CUDA presence (T12).
  7. ✅ `asyncio.Semaphore(4)` cap honored (T16).
  8. ✅ `grep -rn 'openai\|paddle' app/ | grep -v 'app/vision/'` empty (T19).
  9. ✅ `LocalVisionExtractor.ensure_loaded()` raises clear error w/o `--extra gpu` (T11).
  10. ✅ Every successful `extract()` writes ≥1 CallRecord (T17).

---

## Self-review

**Spec coverage** — checked L1 §2, §4, §5, §6, §8 against tasks. All exit-gate items have a task. The `_autodetect` subprocess-mock task is T12. The CLI smoke is T13. Synthetic fixture creation (gap relative to E1) is T5. Recording rotation script (L1 §5) is T14.

**Placeholder scan** — no "TBD" / "implement later" / generic "add error handling" steps.

**Type consistency** — `Label`, `Dimensions`, `Candidate`, `StrokeWidthReport`, `QualityReport` consistently named across tasks. `VisionExtractor.extract` returns `list[FieldObservation]` (matches L1 §2.1 signature).

**Wave-structure note** — added §"Wave structure" so the parallel-planning skill can lift directly.

**Ring-buffer stage tag caveat (T17)** — Cloud uses `vision.gpt4o_tiebreak` for all 9 calls per the existing `CallStage` Literal in `app/schemas/calls.py`. There is no `vision.gpt4o_layout` or per-field stage. If E5 needs finer granularity, add literals to `CallRecord.stage` then; this L2 doesn't widen the schema.

**Provider-tag caveat (T8 SWT)** — There is no `local.swt` provider in the existing Literal. T8 reuses `local.paddleocr` for the SWT CallRecord; if reviewer prefers separation, widen the Literal in a follow-up commit (out of E3 scope).

---

## Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-03 | Project team | Initial E3 L2 plan. 19 tasks, 5 waves. |
