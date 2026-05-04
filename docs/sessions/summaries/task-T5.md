# Task T5 — FakeEvaluator + conftest helpers

STATUS: COMPLETE

## What was done
- Created `tests/_fakes/evaluator.py` — `FakeEvaluator` protocol-compatible test double with per-call latency + canned envelopes.
- `tests/_fakes/__init__.py` already existed (E5 marker); not modified.
- Appended E6 batch helpers to `tests/conftest.py`: `_stub_disposition_envelope`, `_fake_evaluator`, `_reset_reason_code_cache` fixture.
- Created `tests/test_fake_evaluator.py` — 5 tests covering: envelope ordering, per-call latency, depletion error, factory helper, schema round-trip.

## Pre-flight findings
- `_stub_label` was present in conftest (line 39) — no duplicate needed.
- No collisions for any new helpers.
- `AuditRecord` and `Metrics` field shapes matched plan exactly.
- `tests/_fakes/__init__.py` existed with different docstring — left unchanged per append-only rule.

## Test result
`uv run --active pytest tests/test_fake_evaluator.py -v` → 5/5 PASSED

## Commit
`c30dca7` — test(e6): FakeEvaluator + _fake_evaluator + _stub_disposition_envelope conftest helpers
