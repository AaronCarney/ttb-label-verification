## Task 11 — FR-704 Borderline-Band + Fixture-02/07 AC Cases

Added FR-704 borderline-band test (fixture-07) and extended the AC parametrize table with fixture-02 and fixture-07 rows; all new tests xfail behind `_OCR_REPLAY_GAP` / `_UPSTREAM_VISION_REPLAY` markers, which is the correct success path until E3 lands an OCR-replay seam.

### Files
- `tests/test_borderline_band_fr704.py` — CREATED (FR-704 / D-017 assertion)
- `tests/test_ac_fixture_coverage.py` — MODIFIED (lines 60-65; 4→6 parametrize rows)

### Test Results
- 1 passed (fixture-04 short-circuit, no OCR needed)
- 6 xfailed (all `_UPSTREAM_VISION_REPLAY` / `_OCR_REPLAY_GAP` cases)
- 0 failed / 0 errors

### Deviations
None. Post-commit verify hook timed out (>60 s background suite); focused pre-commit run was clean.
