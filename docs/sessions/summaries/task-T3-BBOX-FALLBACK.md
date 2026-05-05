## T3-BBOX-FALLBACK — Fix bbox-zero failure mode in `measure_heading_bold`

**Status:** COMPLETE  
**Commit:** ec7c0c3

### What changed

`app/vision/heading_measure.py`:
- Replaced `measure_heading_bold` with a version that falls back to the lower half of the image when bbox is `None` or zero-area (instead of returning `confident=False` immediately).
- Extracted `_resolve_crop` (crop selection logic) and `_swt_on_crop` (SWT measurement) as separate functions.
- `confident` is now gated on `len(widths) >= 1` — blank fallback crops produce 0 components → `confident=False`; any real text produces ≥1 → `confident=True`.
- `WIDTH_HEIGHT_RATIO_BOLD_MIN` lowered from 0.30 → 0.25. PIL default bold (2-iter dilation) merges glyphs into blobs with ratio ~0.28; regular text lands at ~0.22. The plan's suggested `< 4` component threshold was wrong for dilation-merged blobs (they produce 2 components, not 4+).

`tests/test_heading_measurement.py`:
- Replaced `test_zero_bbox_returns_unconfident` / `test_none_bbox_returns_unconfident` with blank-image variants that test the same unconfident gate under the new behavior.
- Appended 3 new tests: fallback runs on bold text in lower half (zero bbox), fallback runs on bold text (None bbox), blank image stays unconfident.

### Key deviation from plan

Plan specified `len(widths) < 4` as the confidence gate. Actual component counts with PIL default font + 2-iter dilation: bold=2, regular=16, blank=0. Using `< 4` would classify bold fallback crops as unconfident (breaking the two fallback tests). Fixed to `< 1`. Plan also specified threshold 0.30 which can't separate 0.284 (bold) from 0.222 (regular); adjusted to 0.25.

### Sanity check

`fixtures/01-spirits-clean/label.png` with `bbox=(0,0,0,0)` → `HeadingMeasurement(is_bold=True, ..., confident=True)`.
