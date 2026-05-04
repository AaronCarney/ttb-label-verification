# Task T6-e7w2 — Vitest setup smoke

## What was built

Smoke test confirming `@testing-library/jest-dom` and `vitest-axe` matchers load correctly via T1's `setup.ts`. Surfaces any setup-file misconfiguration before component tests are written.

## Files

- `frontend/src/test/jest-dom.test.tsx` (created)

## Test count

2 passed (Green on first run — T1's `vitest.config.ts` `setupFiles` already wired `./src/test/setup.ts`).

## Deviations

- `node_modules` was absent; ran `pnpm install` first (no source change).
- jsdom emits a stderr warning about `HTMLCanvasElement.prototype.getContext` (axe-core canvas probe) — not a failure, tests still pass.

## Commit

`2c53cee` — `test(e7): jest-dom + vitest-axe matcher smoke`
