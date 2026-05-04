## Task T1 — InFlightBatch mutable companion

**What was built:** `InFlightBatch` dataclass — mutable per-batch state companion to the frozen `BatchInFlightState` Pydantic model. Owns the `BoundedQueue`, `recent_dispositions` sliding window (maxlen=10), `calls` ring buffer (maxlen=200), per-label `results` map, and `current_index` cursor. `record_result()` advances the cursor. `snapshot()` rebuilds a frozen `BatchInFlightState` from runtime state.

**Files:**
- `app/batch/__init__.py` — package marker
- `app/batch/state.py` — `InFlightBatch` dataclass
- `tests/test_in_flight_batch.py` — 5 tests

**Test results:** 4/5 pass. 5th test (`test_in_flight_batch_record_result_updates_results_and_advances_index`) fails with `ImportError: cannot import name '_stub_disposition_envelope' from 'tests.conftest'` — that helper is owned by T5 and not yet landed. Will GREEN once T5 commits.

**Commit:** `a9065e5`
