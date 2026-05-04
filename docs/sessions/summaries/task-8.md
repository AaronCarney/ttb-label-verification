# Task 8 — Demo Envelope Snapshotter

## What Was Built

A demo envelope snapshotter script (`scripts/snapshot_demo_envelopes.py`) that runs the live evaluator against each fixture and writes `DispositionEnvelope` JSON to `demo/cached/<fid>/envelope.json` in canonical form (sorted keys, 2-space indent, trailing newline). A `--canonicalize-only` mode re-parses and rewrites existing snapshots for CI idempotency checks.

## Files Created

- `scripts/snapshot_demo_envelopes.py` — snapshotter with live + canonicalize-only modes
- `demo/cached/.gitkeep` — placeholder for the cache directory
- `tests/test_envelope_snapshot.py` — 2 tests: parse validation + idempotency round-trip

## Test Count

2 tests, 2 passing.

## Deviations

None. Live snapshot path (default mode) deferred to post-merge T14 as specified in L1 — requires `OPENAI_API_KEY`. Canonicalize-only mode fully exercised by tests.
