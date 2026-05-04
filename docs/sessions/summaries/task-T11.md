## T11 — Lifespan Teardown Eviction (NFR-DATA-001/002, AC #11)

STATUS: COMPLETE

- Created `tests/test_batch_eviction.py` verbatim per plan.
- Test validates that `app.state.batches` and `app.state.buses` are both `{}` after lifespan context exits.
- Result: 1 PASSED (0.19s). Commit: `c58fa9f`.
