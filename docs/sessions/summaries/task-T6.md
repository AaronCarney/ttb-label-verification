## Task T6 — BatchWorker

**3 cycles, 3 commits, 10 tests passing.**

### Cycle A — Skeleton + FR-401
- Created `app/batch/worker.py`: pull-based producer/consumer via `BoundedQueue`, first-label-individual (item 0 never waits for lookahead window), cancel-in-finally deadlock guard.
- Created `tests/test_batch_worker_skeleton.py`: 4 tests — single-item end-to-end, multi-item result recording, FR-401 timing assertion (<0.5s), deadlock regression guard.
- All 4 GREEN first run. No code adjustments needed.

### Cycle B — Lookahead (test-only)
- Created `tests/test_batch_worker_lookahead.py`: 2 tests — queue saturation at k+1=4 (FR-403), pre-fetch qsize assertion mid-evaluation (FR-402).
- Both GREEN without any worker code change — existing implementation already supported.

### Cycle C — Anomaly + Override
- Created `tests/test_batch_worker_anomaly_override.py`: 4 tests — anomaly-advisory fires at 5/10 threshold (FR-405), grep guard for `.audit_trail.overrides` absence (FR-404 negative), mutation-continues test (FR-404 positive), stream-end exactly-once ordering.
- All 4 GREEN first run. No schema field-name deviations.

### Files
- `app/batch/worker.py` — BatchWorker implementation
- `tests/test_batch_worker_skeleton.py` — 4 tests
- `tests/test_batch_worker_lookahead.py` — 2 tests
- `tests/test_batch_worker_anomaly_override.py` — 4 tests

### Deviations
None.
