# Epoch 3 — Vision Extractor Seam (D-004 #1)

> **Parent:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **Tier:** L1 (epoch-level).
> **Substitutability seam owned:** **D-004 swap point #1** — `VisionExtractor` `Protocol` at `app/vision/base.py`. Two concrete implementations, one validated default, one on-prem-trajectory companion.
> **Depends on:** **E1** (`FieldObservation`, `Evidence`, `BBox`, `Label` schema).

---

## 1. Goal

Land the first substitutability seam. Define the `VisionExtractor` Protocol; ship `CloudVisionExtractor` as the validated default for the deployed URL; ship `LocalVisionExtractor` as the on-prem-trajectory companion gated by `--extra gpu`. Every call site downstream consumes the Protocol, never a concrete impl. The seam is provably substitutable: a single contract test runs both implementations against the same fixture set and asserts identical `FieldObservation` shape (not necessarily identical values — but shape, types, and the FR-001–008 field set must match).

After E3, **`VISION_MODE=cloud uv run task demo` extracts every PRD §5.1 field from a JPEG/PNG label** with reasonable confidence, and `VISION_MODE=local uv run task demo --extra gpu` does the same against the on-prem-trajectory deployment topology.

---

## 2. Components delivered

### 2.1 Seam interface (`app/vision/base.py`)

```python
from typing import Protocol
from app.schemas.extracted import FieldObservation
from app.schemas.label import Label

class VisionExtractor(Protocol):
    async def extract(self, label: Label) -> list[FieldObservation]: ...
    async def ensure_loaded(self) -> None: ...  # warm-up hook
```

`Label` is a thin wrapper schema declared in E1 carrying `image_bytes`, `content_type`, optional `dimensions={width_px, height_px, dpi}`, and `face_tag ∈ {front, back, neck, side}`.

### 2.2 Cloud implementation (`app/vision/cloud.py`) — validated default

`CloudVisionExtractor` uses **GPT-4o-on-crop** with OpenAI Structured Outputs `strict:true` for every leg per ARCH §4.2.3 / §7. Each FR-001 through FR-008 field maps to a structured-schema extraction call; the Web layer's pre-extraction crop-suggestion (a coarse layout pass) is a single GPT-4o call returning candidate bboxes; per-field extraction calls each take a crop and return a typed `FieldObservation` slice.

Rate-limit and bulkhead per ARCH §11.2: at most 4 outstanding calls (asyncio.Semaphore). All calls record into `CallRecord` ring buffer with `provider="openai"`, `model_version`, `prompt_version`, `output_hash`.

### 2.3 Local implementation (`app/vision/local.py`) — on-prem-trajectory companion

`LocalVisionExtractor` runs:

1. **PaddleOCR PP-OCRv5 (GPU)** via `app/vision/paddle_runner.py` — coarse text + bbox extraction.
2. **Stroke-Width-Transform (SWT) bold detector** via `app/vision/swt.py` — heading-bold for FR-202.
3. **Florence-2-large** via `app/vision/florence2.py` (HuggingFace Transformers + `accelerate`) — layout analysis, region proposals.
4. **GPT-4o-on-crop tiebreaker** via `app/vision/tiebreak_gpt4o.py` — only invoked when local signals disagree (per ARCH §4.2.3); strict:true Structured Outputs.
5. **Qwen2.5-VL-7B-AWQ fallback** via `app/vision/qwen_vl.py` — when Florence-2 + GPT-4o are both unavailable.

All five components implement a small internal sub-interface (`async run(crop) -> Candidate`) so the local pipeline composes them deterministically. The local impl lives behind the `[gpu]` optional dependency group and degrades gracefully if `paddlepaddle-gpu` / `torch` / `transformers` are not installed (raises `RuntimeError` at `ensure_loaded()`).

### 2.4 Quality gates (`app/vision/quality.py`)

Per T4 §Q4.6 / FR-602 / FR-603:

- BRISQUE / NIQE quality score (computed via `opencv-python-headless` + a small reference implementation; the L2 plan settles whether to use a published BRISQUE Python port or implement the simpler NIQE; recommend a published port to keep the math reviewable).
- DPI extraction from EXIF / PNG `pHYs` / JFIF; falls back to `dimensions.dpi` if the applicant supplied it.
- Glare / motion-blur heuristics on the warning region only (cheap; runs after layout).

Returns a `QualityReport` with `disposition: ok | needs_better_photo` and a `WARNING.LEGIBILITY.*` reason code on degradation. The Vision Extractor short-circuits with `disposition=needs_better_photo` *before* invoking expensive extraction calls.

### 2.5 DI wiring (`app/deps.py` updated)

E1 left `app/deps.py` with `NotImplementedError` placeholders. E3 fills the `VisionExtractor` provider:

```python
def get_vision_extractor(settings: Settings) -> VisionExtractor:
    match settings.vision_mode:
        case "cloud": return CloudVisionExtractor(settings)
        case "local": return LocalVisionExtractor(settings)
        case "auto":  return _autodetect(settings)
        case _: raise ValueError(...)
```

`_autodetect` probes for a CUDA device via `nvidia-smi` (Python `subprocess.run(['nvidia-smi'], check=False)`); falls back to cloud per D-015.

### 2.6 Test surface

- `tests/test_vision_substitutability.py` — runtime check that both `CloudVisionExtractor` and `LocalVisionExtractor` satisfy the `VisionExtractor` Protocol; both implement `extract()` and `ensure_loaded()` with matching signatures; both produce `list[FieldObservation]` against the same fixture labels.
- `tests/test_vision_cloud_extraction.py` — cloud impl extracts FR-001 through FR-008 against canned multipart JPEG/PNG fixtures using **recorded OpenAI responses** (HTTP-level fixtures via `respx` or `httpx_mock`); `LLM_MODEL_SNAPSHOT` and `PROMPT_VERSION` pinned so recordings stay valid.
- `tests/test_vision_quality_gates.py` — BRISQUE/NIQE scores on `fixtures/04-low-res-blurry/` triggers `needs_better_photo` with `WARNING.LEGIBILITY.LOW_RESOLUTION`; glare fixture triggers `WARNING.LEGIBILITY.GLARE`; motion blur triggers `WARNING.LEGIBILITY.MOTION_BLUR`.
- `tests/test_vision_dpi_extraction.py` — DPI extracted from EXIF, PNG pHYs, JFIF, and applicant-supplied `dimensions.dpi`; missing DPI emits `ENGINE.MEASUREMENT.MISSING_DPI` (FR-602 / FR-910).
- `tests/test_vision_local_protocol.py` — local impl satisfies the Protocol with all five sub-runners interface-mocked; `ensure_loaded()` raises a clear error if `--extra gpu` deps are missing.
- `tests/test_vision_bulkhead.py` — concurrency budget (asyncio.Semaphore at 4) is honored; concurrent calls beyond the budget queue without raising.
- `tests/test_vision_ring_buffer_records.py` — every call writes a `CallRecord` to the per-batch ring buffer with the right `stage` enum value and `latency_ms` populated.

---

## 3. Wire / data contracts owned by this epoch

E3 owns no wire-layer contract; the seam consumes the E1 `Label` schema and produces the E1 `list[FieldObservation]`. E3 **does** own the `FieldObservation.upstream_meta` keys (`engine_version`, `model_snapshot`, `processing_ms`, etc.) — the L2 plan settles the exact key set and asserts both impls populate them.

---

## 4. Exit gate

The epoch lands when **all of these pass**:

1. `app/vision/base.py` declares `VisionExtractor` as a `typing.Protocol` with `extract()` and `ensure_loaded()`.
2. `tests/test_vision_substitutability.py` asserts `isinstance(CloudVisionExtractor(settings), VisionExtractor) is True` and the same for `LocalVisionExtractor` (via `runtime_checkable`).
3. Both impls produce the **same set of `FieldObservation.field_id` values** against the same fixture label image (the values may differ — not asserted equal — but the field set must match the FR-001 through FR-008 manifest).
4. Cloud impl extracts every PRD §5.1 field from `fixtures/01-spirits-clean/label.png` using recorded OpenAI responses; the recorded responses are committed under `tests/recordings/openai/` keyed by `LLM_MODEL_SNAPSHOT` + `PROMPT_VERSION`.
5. Quality gates emit `WARNING.LEGIBILITY.*` reason codes on the degraded fixtures (low-res, glare, motion-blur); on a clean fixture they pass through with `disposition=ok`.
6. `VISION_MODE=auto` falls back to cloud when no CUDA device is detected; falls back to local when CUDA is present (CI runs both code paths via env-var override).
7. The asyncio.Semaphore bulkhead caps concurrent vision calls at 4; a 5th request queues without raising.
8. `grep -rn 'openai\|paddle\|florence\|qwen' app/ | grep -v 'app/vision/'` returns no hits — the vision dependencies are isolated to the seam directory.
9. `LocalVisionExtractor.ensure_loaded()` on a CPU-only machine raises a clear `RuntimeError` naming the missing `--extra gpu` deps (instead of an obscure `ImportError`).
10. Every successful `extract()` call writes one `CallRecord` per inference leg (≥ 1 for cloud, up to 5 for local); ring-buffer `maxlen=200` is honored.

---

## 5. TDD strategy

**Mockable** —

- **OpenAI HTTP responses:** recorded via `respx` (or `httpx_mock`) at the HTTP layer, **not** at the SDK level. Recording at the HTTP layer survives SDK upgrades; recording at the SDK level requires test rewrites on every SDK bump.
- **PaddleOCR / Florence-2 / Qwen runners:** interface-mocked via `monkeypatch` setting the runner's `run()` method.
- **`nvidia-smi` subprocess:** mocked with `subprocess.run` patched.

**Real** —

- BRISQUE / NIQE math on actual fixture images (committed PNG/JPEG files).
- DPI extraction from real EXIF / PNG pHYs / JFIF metadata.
- The asyncio.Semaphore behavior under concurrent `pytest-asyncio` fixtures.

**Recording posture.** Cloud-vision tests use recordings, **not** live calls — every test must be runnable offline. The L2 plan ships a `scripts/record_vision_responses.py` that re-records when `LLM_MODEL_SNAPSHOT` rotates (this is in the same family as `scripts/regenerate_fixtures.py` from D-020 but scoped to test recordings rather than demo cache).

---

## 6. Out of scope for this epoch

- Multi-image label aggregation (front + back + neck) — PRD OQ-PRD-4 (open); the Vision Extractor's contract returns observations per image; aggregation is **not** in E3.
- Live OpenAI calls in CI — strictly recorded.
- Cross-session caching — per ARCH §6.7, session-scoped only; persistence is OQ-ARCH-2 (deferred to production).
- LLM cost optimization (token counting, prompt compression) — out of MVP; recorded responses make the topic moot for the demo.
- Local-mode validation against demo fixtures — accepted-risk-7 in parent §6: local impl is shipped to prove the seam holds, not to be the demo's primary path. Cloud is the validated default.

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenAI Structured Outputs `strict:true` rejects edge inputs (e.g., a label with no clear `brand_name` region) | Medium | Medium | Schema design favors permissive optionality (every extracted field is `optional` in the schema); failure surfaces as `null` field which the Application Service routes to `needs_review` via FR-302 ocr-reconcile (E4) |
| HTTP recordings drift after `LLM_MODEL_SNAPSHOT` rotates and tests silently use stale data | Medium | Medium | Recording filename includes the snapshot tag; CI fails if the active snapshot has no recording |
| Local-mode imports inflate `uv sync` time on the cloud profile | Low | Medium | Local-only imports gated by `[gpu]` optional dependency group; CPU profile excludes `torch` / `transformers` / `paddlepaddle-gpu` |
| Florence-2 license incompatibility | Low | High | Florence-2 ships under MIT (per HuggingFace model card); license check in CI |
| BRISQUE / NIQE Python ports underperform on real-world fixtures, false-flagging clean labels as low-quality | Medium | Medium | Quality-gate thresholds are configurable in `configs/vision.local.toml` and `configs/vision.cloud.toml`; tuned during E8 against the eval corpus |
| Cloud bulkhead at 4 outstanding calls bottlenecks under fixture-05 (50-label batch) | Low | Medium | The batch processor's `LOOKAHEAD_K=3` (E6) limits in-flight items to 4 anyway; cloud bulkhead is a defense-in-depth, not the throughput governor |

---

## 8. L2 hand-off notes

When E3 lands:

1. Decompose into 7 tasks: Protocol declaration → Cloud impl → Local impl pipeline (5 sub-tasks: paddle_runner, swt, florence2, tiebreak_gpt4o, qwen_vl) → quality.py → DI wiring → ring-buffer integration. Local pipeline tasks are parallelizable (each sub-runner is independent).
2. **Wave structure:** base.py → cloud.py + local sub-runners (parallel) → local.py composes them (sequential after sub-runners) → quality.py + DI + ring-buffer integration (parallel).
3. The L2 plan **must** include a task that runs `python -m app.vision.cloud --label fixtures/01-spirits-clean/label.png` as a CLI smoke against the recorded responses.
4. The L2 plan **must** include a task that exercises `_autodetect()` on both a CUDA-present and CUDA-absent machine via subprocess monkeypatching.
5. Recordings are stored under `tests/recordings/openai/<snapshot-tag>/<fixture-id>/<call-name>.json`.

---

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial epoch-3 L1 doc. |
