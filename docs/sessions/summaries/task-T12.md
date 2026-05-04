# Task T12 — LOOKAHEAD_K env-override AC #10

**STATUS: COMPLETE**

## What was done
- Created `tests/test_lookahead_k_env_override.py` verbatim from the L2 plan.
- 3 tests: parametrized k=2 and k=4 overrides + default=3 when env absent.
- All 3 passed GREEN on first run (0.20s).
- Committed: `9a5db08` — `test(e6): LOOKAHEAD_K env-override AC #10 (k=2, k=4, default=3)`

## Key assertions verified
- `in_flight.lookahead_k == k_value` for k=2 and k=4
- `in_flight.queue.maxsize == k_value + 1`
- Default k=3 → `queue.maxsize == 4` when `LOOKAHEAD_K` env absent
