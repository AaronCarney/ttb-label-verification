# Task T15 (E5) — POST /labels endpoint + build_evaluator DI factory

## Outcome
COMPLETE — 3 tests added, all pass. 1 commit. Full suite 463/463 green.

## Files
- `app/api/labels.py` (new) — POST /labels: multipart parse, magic-byte MIME sniff (PNG/JPEG only), JSON validation, delegate to Evaluator.
- `app/deps.py` (additive) — `build_evaluator(settings)` factory wiring vision + rules + orchestrator + SessionCache(128). Existing factories untouched.
- `app/main.py` (additive) — register labels router inside `create_app()` after healthz.
- `tests/test_post_labels_endpoint.py` (new) — 3 tests: happy-path, TIFF reject, malformed-JSON reject.

## Validation
- Magic-byte sniff for content-type → 400 on unsupported MIME.
- `Application(**json.loads(...))` wrapped in `(JSONDecodeError, ValueError, TypeError)` → 400 `rejected_input: ...`.
- All other exceptions propagate to Evaluator's chokepoint (P4 → needs_review).

## Test result
- Focused: `uv run pytest tests/test_post_labels_endpoint.py -v` → 3/3 pass.
- Full: `uv run pytest -x -q` → 463 passed (was 459; +4 net new from this wave including T18 sibling).

## Path A
TDD one cycle, no deviations. Test → red → implement → green → commit.

## Status
`STATUS: COMPLETE — 463 tests pass; T15 endpoint + DI factory + router registration committed.`
