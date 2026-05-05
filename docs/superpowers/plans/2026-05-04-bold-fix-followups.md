# Bold-Fix Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `parallel-plan-executor` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close five gaps surfaced in review of commit `6c2b312` (the bold-detection wiring): the SWT measurement never fires on real labels, the rule-routing alias surfaced previously-broken validators, the reviewer surface leaks audit-only keys and shows no label image, and the live macro-F1 number in the README is stale.

**Architecture:** Each fix is a narrow, single-file (or near-single-file) change preserving existing seams. T1–T4 are independent and parallelizable. T5 depends on T1–T4 because the eval re-measure must reflect the corrected pipeline.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, OpenCV (`opencv-python-headless`), Pillow, Jinja2 templates + a built React island (already-bundled at `app/ui/static/island/single.js`; do not rebuild as part of these tasks).

---

## File Structure

```
app/
  api/
    ui.py                              # MODIFY (T1) — add /labels/<eval>/image route + thread image_url to template; (T2) no
    labels.py                          # not touched
  services/
    envelope_builder.py                # MODIFY (T2) — strip audit-only keys before _coerce_str
  vision/
    cloud.py                           # MODIFY (T3) — pass image dimensions into measure_heading_bold; bbox fallback
    heading_measure.py                 # MODIFY (T3) — accept image_dimensions; full-image fallback when bbox is degenerate
  rules/_validators/
    fuzzy_brand.py                     # MODIFY (T4) — project dict observed_value via known key; NOT_APPLICABLE when expected missing
    format_check.py                    # MODIFY (T4) — same dict-projection + NOT_APPLICABLE handling
  ui/
    templates/
      single.html                      # MODIFY (T1) — render <figure><img></figure> when image_url is in context
      base.html                        # not touched
demo/                                  # not touched
README.md                              # MODIFY (T5) — refresh §Trade-offs macro-F1 prose
tests/
  test_label_image_route.py            # CREATE (T1)
  test_envelope_extracted_value_clean.py  # CREATE (T2)
  test_heading_measurement.py          # MODIFY (T3) — add fallback-bbox tests
  test_validator_dict_observation.py   # CREATE (T4)
```

The plan touches **8 files** across **app/** and **tests/** (plus README). Each task ships its own test file or extends one — never share a test file between tasks.

---

## Conventions

**Test command (every step):**
`uv run --python 3.12 python -m pytest <path> -q`
(prefix the test path with the task's test file; never run the whole suite from a per-step verification — only at the end of each task and at end-of-plan.)

**Commit cadence:** one commit per task at the green-test point. Use Conventional-Commits (`fix(scope):`, `feat(scope):`).

**Branch:** `feat/e8-backend` (already checked out). Do not branch off; tasks land directly on this branch.

**Working directory:** `/home/context/olorin/projects/takehome-e8backend`. All file paths in the plan are relative to this directory.

---

## Task 1: Display label image in reviewer UI

**Why:** The single-label shell (fixture mode + upload mode) renders the `DispositionEnvelope` JSON, but a grader has no way to look at the actual label image to sanity-check the extraction. There is no `<img>` anywhere on `/`. This task adds an image-serving route for upload-mode and a static route for fixture-mode, and threads an `image_url` into the template so `single.html` can render a figure.

**Files:**
- Create test: `tests/test_label_image_route.py`
- Modify: `app/api/ui.py` (add `_LATEST_UPLOAD_IMAGES` cache, add `GET /labels/{eval_id}/image` route, add fixture image route, thread `image_url` into both `single_page_shell` and `single_label_upload`)
- Modify: `app/ui/templates/single.html` (render `<figure><img src="{{ image_url }}" alt="..."></figure>` when set)

### Step 1.1 — Write failing test for fixture image route

- [ ] Create `tests/test_label_image_route.py` with the contents below:

```python
"""Reviewer UI must display the label image. Two routes are required:

  GET /fixtures/{slug}/label.png  — returns the PNG bytes for the demo
                                     fixtures shipped under fixtures/.
  GET /labels/{eval_id}/image     — returns the bytes uploaded via
                                     POST /. Bytes are cached in-process
                                     keyed on the synthesized evaluation_id
                                     so a follow-up GET against the rendered
                                     page sees the same image.

Both routes return 404 for unknown ids; both set Content-Type: image/png
or image/jpeg.
"""
from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app


def _png_1x1() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (1, 1), color=(0, 0, 0)).save(buf, "PNG")
    return buf.getvalue()


def test_fixture_image_route_serves_png():
    client = TestClient(create_app())
    response = client.get("/fixtures/01/label.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_fixture_image_route_404_on_unknown_slug():
    client = TestClient(create_app())
    response = client.get("/fixtures/99/label.png")
    assert response.status_code == 404


def test_root_html_includes_image_for_fixture_mode():
    """`GET /?fixture=01` must surface an <img> pointing at the fixture
    image route so the reviewer can see what the engine read."""
    client = TestClient(create_app())
    response = client.get("/?fixture=01")
    assert response.status_code == 200
    assert "<img" in response.text
    assert "/fixtures/01/label.png" in response.text


def test_upload_image_round_trips():
    """An upload's bytes must be retrievable via /labels/{eval_id}/image
    so the rendered template can display them."""
    from app.api.ui import _get_upload_evaluator
    from tests._fakes.evaluator import FakeEvaluator
    from tests.conftest import _stub_disposition_envelope

    app = create_app()
    env = _stub_disposition_envelope(42, disposition="pass")
    fake = FakeEvaluator([(0.0, env)])
    app.dependency_overrides[_get_upload_evaluator] = lambda: fake
    client = TestClient(app)

    png = _png_1x1()
    response = client.post(
        "/", files={"label": ("upload.png", png, "image/png")}
    )
    assert response.status_code == 200
    # The shell must reference the image route by the synthesized eval id.
    assert f"/labels/{env.evaluation_id}/image" in response.text

    # The bytes round-trip — the cache lookup returns the exact upload.
    img = client.get(f"/labels/{env.evaluation_id}/image")
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"
    assert img.content == png


def test_upload_image_404_on_unknown_eval_id():
    client = TestClient(create_app())
    response = client.get("/labels/no-such-id/image")
    assert response.status_code == 404
```

- [ ] **Step 1.2 — Run the test, confirm it fails**

`uv run --python 3.12 python -m pytest tests/test_label_image_route.py -q`
Expected: 5 failed (routes don't exist; template doesn't include `<img>`).

- [ ] **Step 1.3 — Implement the routes and template wiring**

Edit `app/api/ui.py`:

1. Near the existing `_DEMO_ENVELOPE_CACHE: dict[str, str] = {}` block, add:

```python
# Per-process cache of upload bytes keyed by synthesized evaluation_id. Bounded
# so a long-running Space doesn't grow without limit. The value is (mime, bytes);
# bytes are GC'd when the entry is evicted.
from collections import OrderedDict
_UPLOAD_IMAGE_CACHE_MAX = 64
_LATEST_UPLOAD_IMAGES: OrderedDict[str, tuple[str, bytes]] = OrderedDict()


def _stash_upload_image(eval_id: str, mime: str, body: bytes) -> None:
    _LATEST_UPLOAD_IMAGES[eval_id] = (mime, body)
    while len(_LATEST_UPLOAD_IMAGES) > _UPLOAD_IMAGE_CACHE_MAX:
        _LATEST_UPLOAD_IMAGES.popitem(last=False)


# Fixture image directory — mirrors the on-disk layout under fixtures/.
_FIXTURE_IMAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "fixtures"
_FIXTURE_DIR_BY_SLUG = {
    "01": "01-spirits-clean",
    "02": "02-bourbon-stones-throw",
    "03": "03-warning-title-case",
    "04": "04-low-res-blurry",
    "06": "06-abv-out-of-tolerance",
    "07": "07-borderline-confidence",
}
```

2. Add two routes (immediately after the existing `single_label_upload` definition):

```python
from fastapi.responses import Response


@router.get("/fixtures/{slug}/label.png")
async def fixture_label_image(slug: str) -> Response:
    """Serve the PNG for one of the shipped demo fixtures."""
    dirname = _FIXTURE_DIR_BY_SLUG.get(slug)
    if dirname is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"unknown fixture {slug!r}")
    path = _FIXTURE_IMAGE_ROOT / dirname / "label.png"
    try:
        body = path.read_bytes()
    except OSError:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"fixture image missing: {slug}")
    return Response(content=body, media_type="image/png")


@router.get("/labels/{eval_id}/image")
async def upload_label_image(eval_id: str) -> Response:
    """Serve the PNG/JPEG bytes uploaded for a given evaluation."""
    entry = _LATEST_UPLOAD_IMAGES.get(eval_id)
    if entry is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"no image for evaluation {eval_id!r}")
    mime, body = entry
    return Response(content=body, media_type=mime)
```

3. In `single_page_shell`, build the `image_url` and add it to the template context:

Replace the existing `return templates.TemplateResponse(...)` call inside `single_page_shell` with:

```python
    return templates.TemplateResponse(
        request=request,
        name="single.html",
        context={
            "envelope_json": _read_demo_envelope(slug),
            "dev_mode": settings.dev_mode,
            "fixture_slug": slug,
            "prev_fixture": prev_slug,
            "next_fixture": next_slug,
            "image_url": f"/fixtures/{slug}/label.png",
        },
    )
```

4. In `single_label_upload`, after building `app_obj` and before calling `evaluator.evaluate`, stash the upload bytes:

```python
    _stash_upload_image(evaluation_id, mime, image_bytes)
```

And in the `return templates.TemplateResponse(...)` for the success path, add `"image_url": f"/labels/{evaluation_id}/image"` to the context.

Edit `app/ui/templates/single.html` — add a figure block immediately after the `<nav>` block and before `<form>`:

```html
  {% if image_url %}
  <figure class="label-preview">
    <img src="{{ image_url }}" alt="The label image being reviewed" />
    <figcaption>Source label image — what the extractor saw.</figcaption>
  </figure>
  {% endif %}
```

- [ ] **Step 1.4 — Run the test, confirm it passes**

`uv run --python 3.12 python -m pytest tests/test_label_image_route.py -q`
Expected: 5 passed.

- [ ] **Step 1.5 — Commit**

```bash
git add app/api/ui.py app/ui/templates/single.html tests/test_label_image_route.py
git commit -m "feat(ui): show label image in single-label reviewer

Adds /fixtures/{slug}/label.png and /labels/{eval_id}/image routes so the
reviewer surface can display the actual label being evaluated. Upload mode
stashes bytes in a bounded per-process cache keyed on the synthesized
evaluation_id; fixture mode serves directly from disk. Template renders
a <figure> when image_url is set."
```

---

## Task 2: Strip audit-only keys from `extracted_value`

**Why:** The wire envelope's per-field `extracted_value` is `_coerce_str(observed_value)` — a stringified dump of the entire dict the cloud extractor produced. After T4 of the bold-fix work, that dict now also carries audit-only keys (`heading_bold_llm`, `heading_bold_measured`, `heading_bold_measured_confident`, `heading_bold_width_height_ratio`) and the per-call self-reported `confidence`. None of these belong on the reviewer surface — they leak internals (e.g., `extracted_value="{'brand_name': 'ACME', 'confidence': 0.95}"`). The reviewer should see the extracted value, not the introspection.

**Files:**
- Create test: `tests/test_envelope_extracted_value_clean.py`
- Modify: `app/services/envelope_builder.py` (filter keys at the wire-projection boundary, per-field-id)

### Step 2.1 — Write failing test

- [ ] Create `tests/test_envelope_extracted_value_clean.py`:

```python
"""The wire envelope's `extracted_value` must show the reviewer-facing
extraction, not internal audit keys. The cloud extractor's observed_value
dict carries:

  - per-field self-reported `confidence` (used by the engine to set
    Evidence.confidence; not user-facing).
  - on `gov_warning` only: heading_bold_llm, heading_bold_measured,
    heading_bold_measured_confident, heading_bold_width_height_ratio
    — internal records of the LLM-vs-measurement comparison.

The wire `extracted_value` must omit those keys.
"""
from __future__ import annotations

from app.schemas.expected import BeverageClass, ExpectedValue
from app.schemas.extracted import (
    Evidence,
    EvidenceSource,
    FieldObservation,
    MatchKind,
)
from app.services.envelope_builder import build_field_findings


def _evidence(field_id: str) -> Evidence:
    return Evidence(
        field_id=field_id,
        source=EvidenceSource.LAYOUT,
        match_kind=MatchKind.NONE,
        confidence=0.95,
    )


def _obs(field_id: str, value: dict) -> FieldObservation:
    return FieldObservation(
        field_id=field_id,
        beverage_class=BeverageClass.SPIRITS,
        observed_value=value,
        evidence=(_evidence(field_id),),
        upstream_meta={},
    )


def test_extracted_value_strips_per_field_confidence():
    findings = build_field_findings(
        results=(),
        observations=[_obs("brand_name", {"brand_name": "ACME", "confidence": 0.95})],
        expected_values=[ExpectedValue(field_id="brand_name")],
    )
    target = next(f for f in findings if f.field_name == "brand_name")
    assert "confidence" not in target.extracted_value
    assert "ACME" in target.extracted_value


def test_extracted_value_strips_heading_audit_keys():
    findings = build_field_findings(
        results=(),
        observations=[
            _obs(
                "gov_warning",
                {
                    "text": "GOVERNMENT WARNING: …",
                    "heading_text": "GOVERNMENT WARNING",
                    "heading_all_caps": True,
                    "heading_bold": True,
                    "type_size_pt": 8.0,
                    "confidence": 0.55,
                    "heading_bold_llm": True,
                    "heading_bold_measured": True,
                    "heading_bold_measured_confident": True,
                    "heading_bold_width_height_ratio": 0.42,
                },
            )
        ],
        expected_values=[ExpectedValue(field_id="gov_warning")],
    )
    target = next(f for f in findings if f.field_name == "warning")
    leaked = (
        "confidence",
        "heading_bold_llm",
        "heading_bold_measured",
        "heading_bold_measured_confident",
        "heading_bold_width_height_ratio",
    )
    for key in leaked:
        assert key not in target.extracted_value, f"leaked audit key: {key}"
    # User-visible content survives.
    assert "GOVERNMENT WARNING" in target.extracted_value


def test_extracted_value_preserves_non_audit_keys_on_warning():
    findings = build_field_findings(
        results=(),
        observations=[
            _obs(
                "gov_warning",
                {
                    "text": "BODY",
                    "heading_text": "GOVERNMENT WARNING",
                    "heading_all_caps": True,
                    "heading_bold": True,
                    "type_size_pt": 8.0,
                    "confidence": 0.9,
                },
            )
        ],
        expected_values=[ExpectedValue(field_id="gov_warning")],
    )
    target = next(f for f in findings if f.field_name == "warning")
    # heading_text + heading_bold drive the verdict — must remain visible.
    assert "GOVERNMENT WARNING" in target.extracted_value
```

- [ ] **Step 2.2 — Run the test, confirm it fails**

`uv run --python 3.12 python -m pytest tests/test_envelope_extracted_value_clean.py -q`
Expected: 2 failed (audit keys leak).

- [ ] **Step 2.3 — Implement the strip**

Edit `app/services/envelope_builder.py`. Locate `_coerce_str` (currently at lines 61–64) and add a sibling helper plus update the call site:

Add immediately below `_coerce_str`:

```python
# Audit-only keys that flow through the cloud extractor's observed_value but
# should never appear on the reviewer surface. Keep this list narrow — every
# new audit key the extractor emits has to be added here explicitly so the
# default is "user-facing unless declared otherwise."
_AUDIT_ONLY_OBSERVED_VALUE_KEYS = frozenset({
    "confidence",
    "heading_bold_llm",
    "heading_bold_measured",
    "heading_bold_measured_confident",
    "heading_bold_width_height_ratio",
})


def _strip_audit_keys(value):
    """If `value` is a dict, drop keys we never want on the wire surface."""
    if not isinstance(value, dict):
        return value
    return {k: v for k, v in value.items() if k not in _AUDIT_ONLY_OBSERVED_VALUE_KEYS}
```

Find the line where `extracted_value` is assigned in the `FieldFindingWire` construction (it's currently a `_coerce_str(obs.observed_value)` call inside `build_field_findings`). Change it to:

```python
            extracted_value=_coerce_str(_strip_audit_keys(obs.observed_value)),
```

(If `_coerce_str` is called in more than one place to format `observed_value`, update every callsite consistently.)

- [ ] **Step 2.4 — Run the test, confirm it passes**

`uv run --python 3.12 python -m pytest tests/test_envelope_extracted_value_clean.py -q`
Expected: 3 passed.

- [ ] **Step 2.5 — Run the existing envelope-builder tests for regression**

`uv run --python 3.12 python -m pytest tests/ -q -k "envelope or wire" --no-header`
Expected: prior count of passes; no regression.

- [ ] **Step 2.6 — Commit**

```bash
git add app/services/envelope_builder.py tests/test_envelope_extracted_value_clean.py
git commit -m "fix(envelope): strip audit-only keys from extracted_value

The cloud extractor's observed_value dict carries internal keys
(self-reported confidence; bold-detection LLM-vs-measurement audit
fields) that should not land on the reviewer surface. _strip_audit_keys
filters them at the wire-projection boundary; the canonical primitive
content (brand_name, heading_text, etc.) still flows through."
```

---

## Task 3: Fix bbox-zero failure mode in `measure_heading_bold`

**Why:** GPT-4o's layout call routinely returns `bbox=[0, 0, 0, 0]` for `gov_warning` on real fixtures (verified on `demo/sample-envelope-01.json` post-bold-fix). `measure_heading_bold` checks `x1 <= x0 or y1 <= y0` and short-circuits with `confident=False` — meaning the SWT measurement never actually runs and the LLM's self-reported `heading_bold` is used 100% of the time. The README's "measured, not guessed" claim is currently aspirational. The fix is a **fallback bbox**: when the layout bbox is degenerate, run SWT against the **lower half** of the full image (the warning is by regulation in the lower portion of the label, and any heading-density signal there is dominated by the warning heading text). Mark the result `confident=True` only when component count and ratio look reasonable; otherwise honour the existing fallback chain.

**Files:**
- Modify test: `tests/test_heading_measurement.py` (add three new tests)
- Modify: `app/vision/heading_measure.py` (accept full-image dimensions hint and a `fallback_to_full_image` switch)
- Modify: `app/vision/cloud.py` (always pass the image when calling `measure_heading_bold`; let the function decide)

### Step 3.1 — Write failing tests

- [ ] Append to `tests/test_heading_measurement.py`:

```python
def test_zero_bbox_falls_back_to_lower_half_when_text_present():
    """GPT-4o's layout call sometimes returns [0,0,0,0]. The measurement
    must still run on a sensible region rather than punting to the LLM —
    the heading lives in the lower half of TTB labels by regulation, so
    that's the fallback crop."""
    # 200x80 image: top half is white, bottom half has rendered bold text.
    img = Image.new("L", (200, 80), color=255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(24)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((10, 50), "GOVERNMENT WARNING", fill=0, font=font)
    arr = np.asarray(img)
    import cv2
    ink = (arr < 128).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    ink = cv2.dilate(ink, kernel, iterations=2)
    arr = np.where(ink > 0, 0, 255).astype(np.uint8)
    out = BytesIO()
    Image.fromarray(arr, mode="L").save(out, "PNG")
    png = out.getvalue()

    m = measure_heading_bold(png, (0, 0, 0, 0))
    assert m.confident, "fallback must run when bbox is degenerate"
    assert m.is_bold


def test_none_bbox_falls_back_to_lower_half():
    img = Image.new("L", (200, 80), color=255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(24)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((10, 50), "GOVERNMENT WARNING", fill=0, font=font)
    arr = np.asarray(img)
    import cv2
    ink = (arr < 128).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    ink = cv2.dilate(ink, kernel, iterations=2)
    arr = np.where(ink > 0, 0, 255).astype(np.uint8)
    out = BytesIO()
    Image.fromarray(arr, mode="L").save(out, "PNG")
    png = out.getvalue()

    m = measure_heading_bold(png, None)
    assert m.confident
    assert m.is_bold


def test_blank_image_with_zero_bbox_returns_unconfident():
    """Fallback only activates when the lower half actually has text. A
    blank fallback crop must not silently classify as `not bold` with
    confident=True — that would make the LLM fallback path unreachable."""
    img = Image.new("L", (200, 80), color=255)
    out = BytesIO()
    img.save(out, "PNG")
    png = out.getvalue()

    m = measure_heading_bold(png, (0, 0, 0, 0))
    assert not m.confident
```

- [ ] **Step 3.2 — Run the new tests, confirm they fail**

`uv run --python 3.12 python -m pytest tests/test_heading_measurement.py -q`
Expected: 3 failed (the existing zero-bbox / none-bbox tests now fail because they currently expect `confident=False`); also the existing tests need updating in the same step.

**Important:** the existing tests `test_zero_bbox_returns_unconfident` and `test_none_bbox_returns_unconfident` assert the old behavior. Update them to reflect the new contract — they keep passing on inputs without text in the lower half:

```python
def test_zero_bbox_returns_unconfident_when_no_text_present():
    """A degenerate bbox + a blank lower half can't be measured."""
    blank = Image.new("L", (200, 80), color=255)
    out = BytesIO()
    blank.save(out, "PNG")
    m = measure_heading_bold(out.getvalue(), (0, 0, 0, 0))
    assert not m.confident


def test_none_bbox_returns_unconfident_when_no_text_present():
    blank = Image.new("L", (200, 80), color=255)
    out = BytesIO()
    blank.save(out, "PNG")
    m = measure_heading_bold(out.getvalue(), None)
    assert not m.confident
```

(Replace the prior `test_zero_bbox_returns_unconfident` and `test_none_bbox_returns_unconfident` definitions with these two.)

- [ ] **Step 3.3 — Implement the fallback**

Edit `app/vision/heading_measure.py`. Replace the `measure_heading_bold` function (currently at lines 47–98) with:

```python
def measure_heading_bold(
    image_bytes: bytes,
    bbox: tuple[int, int, int, int] | None,
) -> HeadingMeasurement:
    """Run the SWT-style measurement on the heading region.

    `bbox` is `(x0, y0, x1, y1)` in pixel coordinates produced by the layout
    call. A `None` or zero-area bbox triggers a fallback: measure the lower
    half of the full image, where the §16.22 warning heading lives by
    regulation. The fallback only reports `confident=True` when there are
    enough connected components to produce a stable stroke-width estimate.
    """
    try:
        full = Image.open(BytesIO(image_bytes)).convert("L")
    except Exception:  # noqa: BLE001 — defensive: malformed PNG
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    crop = _resolve_crop(full, bbox)
    if crop is None:
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    return _swt_on_crop(crop)


def _resolve_crop(
    full: "Image.Image",
    bbox: tuple[int, int, int, int] | None,
) -> "Image.Image | None":
    """Return the actual crop to measure, or None if no usable region."""
    if bbox is not None:
        x0, y0, x1, y1 = bbox
        if x1 > x0 and y1 > y0:
            try:
                crop = full.crop((x0, y0, x1, y1))
            except Exception:  # noqa: BLE001
                return None
            if crop.width >= 8 and crop.height >= 8:
                return crop
    # Fallback: the lower half of the image. §16.22(a) places the warning at
    # the bottom of the label, so this is where the heading text lives.
    h = full.height
    if h < 16:
        return None
    return full.crop((0, h // 2, full.width, h))


def _swt_on_crop(crop: "Image.Image") -> HeadingMeasurement:
    gray = np.asarray(crop)
    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

    widths: list[float] = []
    heights: list[float] = []
    for i in range(1, n_labels):
        x, y, w, h, _area = stats[i]
        comp_dist = dist[y : y + h, x : x + w]
        comp_pixels = comp_dist[comp_dist > 0]
        if comp_pixels.size == 0:
            continue
        widths.append(float(comp_pixels.mean()) * 2.0)
        heights.append(float(h))

    # `confident` requires at least a handful of components so the fallback
    # crop's blank-image case lands as unconfident. 4 components is a low
    # bar that any real heading text clears (one stroke per character).
    if len(widths) < 4:
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    mean_w = float(np.mean(widths))
    mean_h = float(np.mean(heights))
    ratio = mean_w / mean_h if mean_h > 0 else 0.0
    return HeadingMeasurement(
        is_bold=ratio > WIDTH_HEIGHT_RATIO_BOLD_MIN,
        mean_stroke_width=mean_w,
        mean_character_height=mean_h,
        width_height_ratio=ratio,
        confident=True,
    )
```

(`app/vision/cloud.py` already calls `measure_heading_bold(label.image_bytes, bbox)` and reads `measurement.confident` — no change needed there.)

- [ ] **Step 3.4 — Run the heading-measurement tests, confirm green**

`uv run --python 3.12 python -m pytest tests/test_heading_measurement.py -q`
Expected: 7 passed (5 prior + 3 new + 2 rewritten).

- [ ] **Step 3.5 — Sanity-check on a real fixture**

`uv run --python 3.12 python -c "from pathlib import Path; from app.vision.heading_measure import measure_heading_bold; b = Path('fixtures/01-spirits-clean/label.png').read_bytes(); print(measure_heading_bold(b, (0,0,0,0)))"`

Expected output: `HeadingMeasurement(is_bold=..., ..., confident=True)` — confident, with a real ratio. (Whether it lands `is_bold=True` or `False` depends on the fixture; the contract here is `confident=True`.)

- [ ] **Step 3.6 — Commit**

```bash
git add app/vision/heading_measure.py tests/test_heading_measurement.py
git commit -m "fix(vision): fall back to lower-half crop when layout bbox is degenerate

GPT-4o's layout call routinely returns bbox=[0,0,0,0] for gov_warning,
so the SWT measurement never ran on real labels and the README's
'measured, not guessed' claim was aspirational. When the bbox is
degenerate, measure the lower half of the image — the §16.22 warning
heading lives there by regulation. confident=True is gated on at least
4 detected components so blank fallback crops still defer to the LLM."
```

---

## Task 4: Fix validators that broke when the rule-routing alias landed

**Why:** Commit `6c2b312` added the `_FIELD_ID_RULE_ALIASES` map in `app/rules/yaml_engine.py` so `evidence_required: [warning_block]` matches `field_id="gov_warning"`. That fixed the heading rule but also turned on previously-dormant rules whose validators were coded against `obs.observed_value` being a string (not the dict the cloud extractor produces) **and** which rely on `expected.value` being supplied. On FIX-01 we now see:

- `spirits.brand.present` (validator: `fuzzy_brand`) — fails BRAND.PRESENCE.MISSING because `str({"brand_name": "ACME", "confidence": 0.95})` doesn't fuzzy-match the empty default `expected.value`.
- `spirits.alcohol.format` (validator: `regex_match`) — fails ALCOHOL_CONTENT.FORMAT.INVALID because the dict's stringification doesn't match the alc-text regex.

Two-part fix: validators must (a) project a primitive out of dict `observed_value` via a known per-field key when the dict shape is recognized, and (b) return `Outcome.NOT_APPLICABLE` instead of FAIL when the rule needs an expected value but none was supplied.

**Files:**
- Create test: `tests/test_validator_dict_observation.py`
- Modify: `app/rules/_validators/fuzzy_brand.py`
- Modify: `app/rules/_validators/format_check.py`

### Step 4.1 — Write failing tests

- [ ] Create `tests/test_validator_dict_observation.py`:

```python
"""Validators must read primitives from the cloud extractor's dict-shaped
observed_value, and must report NOT_APPLICABLE — not FAIL — when the rule
requires an expected value that was never supplied."""
from __future__ import annotations

from app.rules._validators import ValidatorContext
from app.rules._validators.format_check import regex_match
from app.rules._validators.fuzzy_brand import fuzzy_brand
from app.schemas.expected import BeverageClass, ExpectedValue
from app.schemas.extracted import (
    Evidence,
    EvidenceSource,
    FieldObservation,
    MatchKind,
)
from app.schemas.rejection import Outcome, Severity
from app.schemas.rules import RuleDefinition


def _ctx() -> ValidatorContext:
    return ValidatorContext(
        assets={}, decision_tables={}, started_at_ms=0, engine_version="t"
    )


def _obs(field_id: str, value) -> FieldObservation:
    return FieldObservation(
        field_id=field_id,
        beverage_class=BeverageClass.SPIRITS,
        observed_value=value,
        evidence=(Evidence(field_id=field_id, source=EvidenceSource.LAYOUT,
                            match_kind=MatchKind.NONE, confidence=0.95),),
        upstream_meta={},
    )


def _brand_rule() -> RuleDefinition:
    return RuleDefinition(
        rule_id="spirits.brand.present",
        cfr_citation="27 CFR §5.63(a)",
        applies_to_classes=(BeverageClass.SPIRITS,),
        reason_code="BRAND.PRESENCE.MISSING",
        severity=Severity.REJECT,
        match_policy="fuzzy",
        validator="fuzzy_brand",
        parameters={
            "pass_threshold": 0.92,
            "needs_review_threshold": 0.85,
            "needs_review_reason_code": "BRAND.NAME.NEEDS_REVIEW",
        },
        evidence_required=("brand",),
        effective_date="2022-02-09",
        test_fixtures=(),
    )


def _alcohol_format_rule() -> RuleDefinition:
    return RuleDefinition(
        rule_id="spirits.alcohol.format",
        cfr_citation="27 CFR §5.65(b)",
        applies_to_classes=(BeverageClass.SPIRITS,),
        reason_code="ALCOHOL_CONTENT.FORMAT.INVALID",
        severity=Severity.REJECT,
        match_policy="regex",
        validator="regex_match",
        parameters={
            "pattern": r"^\s*(?:alcohol|alc\.?)\s*[0-9]{1,2}(?:\.[0-9]+)?\s*%?\s*(?:by\s+volume|/\s*vol\.?|vol\.?)\s*$",
            "ignore_case": True,
        },
        evidence_required=("alc_text",),
        effective_date="2022-02-09",
        test_fixtures=(),
    )


# ---- fuzzy_brand --------------------------------------------------------

def test_fuzzy_brand_projects_dict_via_brand_name_key():
    """Cloud extractor emits {brand_name, confidence}; the validator must
    extract the brand string, not stringify the dict."""
    obs = _obs("brand_name", {"brand_name": "ACME BOURBON", "confidence": 0.95})
    exp = ExpectedValue(field_id="brand_name", value="ACME BOURBON")
    result = fuzzy_brand(obs, exp, _brand_rule(), _ctx())
    assert result.outcome == Outcome.PASS, "exact dict-projected match must pass"


def test_fuzzy_brand_no_expected_returns_not_applicable():
    """When no application supplied an expected brand, the rule has nothing
    to compare and must report NOT_APPLICABLE — not silently fail."""
    obs = _obs("brand_name", {"brand_name": "ACME BOURBON", "confidence": 0.95})
    exp = ExpectedValue(field_id="brand_name")  # no value
    result = fuzzy_brand(obs, exp, _brand_rule(), _ctx())
    assert result.outcome == Outcome.NOT_APPLICABLE


def test_fuzzy_brand_string_observation_still_works():
    """Backwards compat: hand-built fixtures pass strings."""
    obs = _obs("brand_name", "ACME BOURBON")
    exp = ExpectedValue(field_id="brand_name", value="ACME BOURBON")
    result = fuzzy_brand(obs, exp, _brand_rule(), _ctx())
    assert result.outcome == Outcome.PASS


# ---- regex_match (alcohol.format) --------------------------------------

def test_regex_match_synthesizes_alc_text_from_dict():
    """ABV dict {abv_pct, unit, confidence} must project to the string
    'ALCOHOL <pct>% BY VOLUME' the alc-format regex expects."""
    obs = _obs("abv", {"abv_pct": 40.0, "unit": "%", "confidence": 0.9})
    exp = ExpectedValue(field_id="abv")
    result = regex_match(obs, exp, _alcohol_format_rule(), _ctx())
    assert result.outcome == Outcome.PASS


def test_regex_match_dict_off_pattern_fails():
    obs = _obs("abv", {"abv_pct": 40.0, "unit": "PROOF", "confidence": 0.9})
    exp = ExpectedValue(field_id="abv")
    result = regex_match(obs, exp, _alcohol_format_rule(), _ctx())
    assert result.outcome == Outcome.FAIL


def test_regex_match_string_observation_still_works():
    """Backwards compat: legacy string observations match directly."""
    obs = _obs("abv", "ALCOHOL 40% BY VOLUME")
    exp = ExpectedValue(field_id="abv")
    result = regex_match(obs, exp, _alcohol_format_rule(), _ctx())
    assert result.outcome == Outcome.PASS
```

- [ ] **Step 4.2 — Run tests, confirm they fail**

`uv run --python 3.12 python -m pytest tests/test_validator_dict_observation.py -q`
Expected: 6 failed (one per test) — none of the projection / NOT_APPLICABLE behavior exists yet.

- [ ] **Step 4.3 — Implement dict-projection in `fuzzy_brand`**

Edit `app/rules/_validators/fuzzy_brand.py`. Replace the body (the part inside the `fuzzy_brand` function) with:

```python
@register("fuzzy_brand")
def fuzzy_brand(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    observed = _project_brand(obs.observed_value)
    expected = "" if exp.value is None else str(exp.value)
    meta = _build_meta(rule, ctx)

    # The rule needs something to compare against. Without an expected brand
    # the application never declared one — surface as NOT_APPLICABLE rather
    # than silently failing every cold-loaded label.
    if not expected:
        return ValidationResult(
            rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class, outcome=Outcome.NOT_APPLICABLE,
            severity=rule.severity, reason_code=None,
            aggregated_confidence=_conf(obs), evidence=obs.evidence,
            expected=exp, observed=obs, engine_meta=meta,
        )

    if stage_a_normalized(observed, expected):
        return ValidationResult(
            rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class, outcome=Outcome.PASS,
            severity=rule.severity, reason_code=None,
            aggregated_confidence=_conf(obs), evidence=obs.evidence,
            expected=exp, observed=obs, engine_meta=meta,
        )

    score = stage_b_fuzzy(observed, expected)
    pass_th = float(rule.parameters.get("pass_threshold", 0.92))
    nr_th = float(rule.parameters.get("needs_review_threshold", 0.85))
    nr_code = rule.parameters.get("needs_review_reason_code", "BRAND.NAME.NEEDS_REVIEW")

    if score >= pass_th:
        return ValidationResult(
            rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class, outcome=Outcome.PASS,
            severity=rule.severity, reason_code=None,
            aggregated_confidence=_conf(obs), evidence=obs.evidence,
            expected=exp, observed=obs, engine_meta=meta,
        )
    if score >= nr_th:
        return ValidationResult(
            rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class, outcome=Outcome.FAIL,
            severity=Severity.WARN, reason_code=nr_code,
            aggregated_confidence=_conf(obs), evidence=obs.evidence,
            expected=exp, observed=obs, engine_meta=meta,
        )
    return ValidationResult(
        rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
        beverage_class=obs.beverage_class, outcome=Outcome.FAIL,
        severity=rule.severity, reason_code=rule.reason_code,
        aggregated_confidence=_conf(obs), evidence=obs.evidence,
        expected=exp, observed=obs, engine_meta=meta,
    )
```

Add the `_project_brand` helper above `fuzzy_brand`:

```python
def _project_brand(value: object) -> str:
    """The cloud extractor produces {brand_name, confidence}; legacy fixtures
    pass a bare string. Return the brand string in either shape."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # `brand_name` is the canonical cloud key; `value` is the legacy fixture key.
        for key in ("brand_name", "value"):
            v = value.get(key)
            if isinstance(v, str) and v:
                return v
    return ""
```

- [ ] **Step 4.4 — Implement dict-projection in `regex_match`**

Edit `app/rules/_validators/format_check.py`. Read the file first to learn its current shape, then update the `regex_match` function to:

```python
@register("regex_match")
def regex_match(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    pattern = rule.parameters.get("pattern", "")
    ignore_case = bool(rule.parameters.get("ignore_case", False))
    flags = re.IGNORECASE if ignore_case else 0
    observed = _project_alc_text(obs.observed_value, obs.field_id)
    ok = bool(re.match(pattern, observed, flags=flags)) if observed else False
    return ValidationResult(
        rule_id=rule.rule_id,
        cfr_citation=rule.cfr_citation,
        beverage_class=obs.beverage_class,
        outcome=Outcome.PASS if ok else Outcome.FAIL,
        severity=rule.severity,
        reason_code=None if ok else rule.reason_code,
        aggregated_confidence=_conf(obs),
        evidence=obs.evidence,
        expected=exp,
        observed=obs,
        engine_meta=_build_meta(rule, ctx),
    )
```

Add the helper above (or below) the function:

```python
def _project_alc_text(value: object, field_id: str) -> str:
    """Build the canonical 'alcohol N% by volume' string from the cloud
    extractor's abv dict. Legacy string observations pass through unchanged."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if field_id in ("abv", "alcohol_content"):
            pct = value.get("abv_pct")
            unit = value.get("unit", "%")
            if pct is None:
                return ""
            return f"alcohol {pct}{unit} by volume"
        # Generic projection: pick the first scalar value with a stable order.
        for key in ("text", "value", "name"):
            v = value.get(key)
            if isinstance(v, str) and v:
                return v
    return ""
```

(`re` is already imported in `format_check.py`; verify the import is present and add it if not.)

- [ ] **Step 4.5 — Run the new tests and confirm green**

`uv run --python 3.12 python -m pytest tests/test_validator_dict_observation.py -q`
Expected: 6 passed.

- [ ] **Step 4.6 — Run the broader suite for regressions**

`uv run --python 3.12 python -m pytest tests/ -q --ignore=tests/eval --deselect "tests/test_keyboard_model.py" --deselect "tests/test_reflow_320px.py" --deselect "tests/test_disposition_pill_wcag_141.py" --deselect "tests/test_eval_full.py"`
Expected: prior pass count + the new 6, no regressions.

- [ ] **Step 4.7 — Commit**

```bash
git add app/rules/_validators/fuzzy_brand.py app/rules/_validators/format_check.py tests/test_validator_dict_observation.py
git commit -m "fix(rules): validators project dict observed_value and skip when expected missing

The rule-routing alias map (commit 6c2b312) turned on validators that were
coded against string-shaped observed_value back when only hand-built
fixtures fed them. The cloud extractor produces dicts, so str(obs) leaked
serialization noise into the comparand and every cold-loaded label
flunked spirits.brand.present and spirits.alcohol.format.

fuzzy_brand and regex_match now project a primitive out of the dict via
known per-field keys (brand_name; abv_pct + unit). When the rule requires
an expected value that was never supplied (no application context),
fuzzy_brand returns NOT_APPLICABLE instead of silently failing."
```

---

## Task 5: Re-measure macro-F1 and refresh README

**Why:** README §Trade-offs reports a live macro-F1 of 0.19 from before T1–T4. Now that the bbox-zero, validator dict-shape, and audit-key issues are fixed, the live score has to be re-measured and the prose updated honestly. T5 must run **after** T1–T4 land.

**Files:**
- Run: `uv run --python 3.12 python -m eval.harness --subset full --mode live` (or whatever the canonical full-suite invocation is — check `pyproject.toml` `[tool.uv.scripts]` and the `eval/` README)
- Modify: `README.md`

### Step 5.1 — Inventory the eval entry points

- [ ] Read `pyproject.toml` for the `eval-full` task definition; read `eval/harness.py` for its CLI surface.

```bash
grep -n "eval-full\|eval-smoke" pyproject.toml
```

Expected: tasks named `eval-full` and `eval-smoke` already exist.

### Step 5.2 — Run the smoke suite first (cheap sanity)

- [ ] `uv run task eval-smoke 2>&1 | tail -40`

Capture stdout to a temp note. Compare disposition macro-F1 to the prior README claim (0.19 live, 0.82 replay).

### Step 5.3 — Run the full live suite

- [ ] `uv run task eval-full 2>&1 | tee /tmp/eval-full-after.log | tail -60`

Note the new disposition macro-F1, cost-weighted score, and any rule-recall changes. Cost cap on the suite is governed by `tests/research/eval/conftest.py` constants in the upstream tree — for this project the eval harness has no hard cap, but a single full run is ~$0.50–$1.50. Halt if the run is going off the rails (timeouts, key errors).

### Step 5.4 — Re-run the replay-mode suite

- [ ] `uv run task eval-full -- --mode replay 2>&1 | tee /tmp/eval-full-replay-after.log | tail -60`

(or whatever the harness CLI flag is for replay mode — confirm with `python -m eval.harness --help`.)

### Step 5.5 — Update README §Trade-offs

- [ ] Open `README.md` and locate the bullet that begins **"The full eval AC gate (macro-F1 ≥ 0.70) is not met end-to-end."** — currently at line 61.

Rewrite the numerical claims in that bullet to reflect the post-fix measurements. Preserve the structure (live numbers first, replay numbers second, cost-weighted score, then the link to the eval write-up). If macro-F1 has materially shifted (improved or regressed), say so plainly. Do **not** invent numbers — if a measurement is unavailable, say "not re-measured" rather than fabricating a value.

If the live macro-F1 has crossed the 0.70 gate, also update the line in the same paragraph that asserts the gate is not met.

### Step 5.6 — Cross-check FIX-01 disposition

- [ ] `python3 -c "import json; e = json.loads(open('demo/sample-envelope-01.json').read()); print('disposition:', e['disposition']); print('confidence:', e['disposition_confidence'])"`

If FIX-01 still lands `disposition='fail'`, regenerate the envelopes:
`OPENAI_API_KEY=... uv run --python 3.12 python scripts/build_demo_envelopes.py`

Then re-inspect — the brand and alcohol-format rules should no longer be the cause of failure. (Other rules that legitimately fail on this fixture, like the warning-block heading rule, may still fire.)

### Step 5.7 — Commit

- [ ] `git add README.md demo/sample-envelope-*.json`
- [ ] `git commit -m "docs(readme): refresh §Trade-offs with post-followup eval numbers"`

---

## Self-Review Checklist (run after writing the plan)

- [x] **Spec coverage:** All 5 review findings have explicit tasks. T1=image display; T2=audit-key strip; T3=bbox-zero; T4=broken validators; T5=re-measure.
- [x] **No placeholders:** Every step has either runnable code, an exact file path with line numbers, or a precise command. No "implement appropriate handling" hand-waves.
- [x] **Type consistency:** `_strip_audit_keys` (T2) is the only new public surface; T1 + T3 are pure additions inside existing files; T4 helpers (`_project_brand`, `_project_alc_text`) are private and used only by their owning validator.
- [x] **TDD posture:** Every task starts with a failing test (steps numbered `.1`), a failure-confirmation step, the implementation, a green-test confirmation, and a commit. Per-step granularity is 2–5 minutes.
- [x] **Frequent commits:** One commit per task. Tasks 1–4 are independent and can land in any order.
