# Task 13 — HF Space deploy + UI smoke

## What was built

Env-gated smoke tests for the deployed HF Space (4 tests, all skip when `TTB_DEPLOY_URL` is unset) plus a RUNBOOK provisioning section documenting the one-time HF Space setup steps and decision rationale for the default URL.

## Files created/modified

- `tests/test_deploy_healthz.py` — CREATED (4 smoke tests: healthz, UI shell, static island bundle, TLS)
- `DEMO-RUNBOOK.md` — MODIFIED (appended `## Initial deployment setup` section after `## Re-record protocol`)
- `docs/sessions/summaries/task-13.md` — CREATED (this file)

## Test count

- T13 focused: 4 skipped (TTB_DEPLOY_URL not set), 0 failed, 0 errored
- T10 + T13 combined: 3 passed, 4 skipped

## Deviations

None. Implemented verbatim from plan. Post-commit verify hook timed out (>60s) — pre-commit test run confirmed green state before commit.
