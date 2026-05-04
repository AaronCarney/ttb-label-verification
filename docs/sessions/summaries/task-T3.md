## Task T3 — AnomalyDetector (FR-405)

**Status:** COMPLETE

**Files created:**
- `app/batch/anomaly.py` — AnomalyAdvisory dataclass + AnomalyDetector sliding M-of-N window
- `tests/test_anomaly_detector.py` — 9 TDD tests

**Result:** 9/9 tests GREEN. Committed: `1b225bc`.

**Notes:** PEP 420 namespace packages resolved `app.batch.anomaly` without needing `__init__.py` from T1.
