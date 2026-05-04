# Task T2 — BoundedQueue

## What Was Built

Typed wrapper around `asyncio.Queue(maxsize=k+1)` enforcing FR-403 pull-based demand.

## Files

- `app/batch/queue.py` — `BoundedQueue(Generic[T])` with `lookahead_k` constructor, `maxsize`, `saturated`, `qsize()`, `put()`, `get()`
- `tests/test_bounded_queue.py` — 4 async tests covering construction, FIFO order, saturation blocking, and producer unblock on drain

## Test Count

4 added, 4 passing.

## Deviations

None. PEP 420 namespace packages resolved `app.batch` without `__init__.py` as expected.
