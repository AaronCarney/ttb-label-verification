## Task 1 — Fixture completion (fill gaps; no overwrites)

**What was built:** Filled all missing fixture assets for six single-label fixtures (notes.md, expected.json, label.png) and added a provenance test suite that enforces structural completeness. Four Pillow build scripts generate deterministic label images for fixtures 03, 04, 06, and 07.

**Files created:**
- `fixtures/01-spirits-clean/notes.md`
- `fixtures/02-bourbon-stones-throw/expected.json`
- `fixtures/02-bourbon-stones-throw/notes.md`
- `fixtures/03-warning-title-case/label.png` (via build script)
- `fixtures/03-warning-title-case/notes.md`
- `fixtures/04-low-res-blurry/label.png` (via build script)
- `fixtures/04-low-res-blurry/notes.md`
- `fixtures/06-abv-out-of-tolerance/label.png` (via build script)
- `fixtures/06-abv-out-of-tolerance/notes.md`
- `fixtures/07-borderline-confidence/expected.json`
- `fixtures/07-borderline-confidence/label.png` (via build script)
- `fixtures/07-borderline-confidence/notes.md`
- `scripts/build_fixture_03.py`
- `scripts/build_fixture_04.py`
- `scripts/build_fixture_06.py`
- `scripts/build_fixture_07.py`
- `tests/test_demo_fixture_provenance.py`

**Tests added:** 13 (6 × has_required_files + 6 × expected_json_parses + 1 borderline-band marker). All 13 pass.

**Deviations:** None. All existing committed files were left untouched.

**Commit:** `433d149`
