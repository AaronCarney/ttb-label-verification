## Session Directive

> **MANDATORY:** Resume by dispatching `parallel-plan-executor` against the **APPROVED v0.4** L2 plan. Do not re-plan or re-review.

E7 (UI — Jinja2 shell + React island) has a fully reviewed, executor-ready L2 plan committed to `feat/e7-ui` in this worktree. Plan-review (parallel mode) completed cleanly — Pass 2 architectural APPROVED at iter-2; Pass 1 structural WARNINGS_ONLY at iter-2 (all 9 fixed across iter-1 + iter-2). The plan is ready for parallel-plan-executor.

## Application Context

TTB Label Verification take-home prototype (FastAPI + React). E7 is the UI epoch (Jinja2 shells + React island, 17 PRD §5.6 components). Running in **parallel** with another session implementing E5/E6 on `main` of `/home/context/projects/takehome` (DO NOT touch). All E7 tests use canned envelope JSON fixtures (T3) — no E5/E6 dependency.

## Position

- **Repo (worktree):** `/home/context/projects/takehome-e7` (symlinked at `projects/takehome-e7`)
- **Branch:** `feat/e7-ui`
- **HEAD:** `f0c6e73` (plan v0.4 — plan-review iter-2)
- **Plan:** `docs/plans/ttb-label-verification-epoch-7-l2.md` (5515 lines, 34 tasks, 8 waves: W1=4, W2=3, W3=6, W4=6, W5=5, W6a=2, W6b=2, W7=5, W8=1)
- **Test baseline:** 375 passed (`uv run --python 3.12 pytest -x -q` from worktree root)

## Plan Versions Committed This Session

```
f0c6e73 docs(e7): plan-review iter-2 — §10 reciprocity (T7→T33, T3→T31) (v0.4)
a670893 docs(e7): plan-review iter-1 — apply 7 warnings + 2 critical + 2 recs (v0.3)
5d9f3a7 docs(e7): L2 plan v0.2 — parallel-planning audit (W6 split + conftest fix)
c38f31b docs(e7): L2 plan v0.1 — 34 tasks, 8 waves, canned-envelope TDD
```

## Plan-Review Outcome

- **Mode:** Parallel (5476 lines, 34 tasks, structural risk = none)
- **Pass 1 Structural — APPROVED at iter-2.** Iter-1 fixed 7 warnings: W6a/W6b per-task `**Wave:**` header bumps; T27 Owns adds `single.test.tsx`; §4 conftest fixture list cleanup; Wave 7 prologue rewrite; T3 §10 row filename fix; T29/T30/T32 §10 deps add T3; T27 §10 deps add T5. Iter-2 fixed 2 §10 reciprocity gaps: T33 deps add T7 (and T7 blocks add T33); T31 deps add T3.
- **Pass 2 Architectural — APPROVED at iter-1.** Two criticals applied: (C1) ORDER INVARIANT comment in T27's `_REASON_CODES` documenting that `O → w → ENTER` lands on `WARNING.STYLE.HEADING_NOT_BOLD_CAPS` because `filtered[highlight=0]` is the first W-prefixed entry — corpus-order invariant explicitly named; manual a11y-smoke step 7 narration corrected. (C2) Refactored T27/T28 `_mount` → `export function mount()`; tests now call `mount()` per `it` block (avoids Vitest module-cache silently skipping the second test's render). Two recs applied: (R1) T33 consumes `pnpm_built_island` fixture instead of running its own pnpm install + build; (R5) T26 `useBatchStream` got a FRAMING ASSUMPTION comment per PRD §6.3. R2 (Vite version pinning) and R6 (T29 init-script ordering) deferred — `pnpm-lock.yaml` covers reproducibility; init script's body already polls.

## What's Next

1. **`/clear`**, then dispatch `parallel-plan-executor` against `docs/plans/ttb-label-verification-epoch-7-l2.md`. Per olorin standards, this is the only allowed L2 executor.
2. The executor will run the 8 waves with up to 6 concurrent subagents per wave. Wave plan: W1=T1–T4 (4); W2=T5–T7 (3); W3=T8–T13 (6); W4=T14–T19 (6); W5=T20–T24 (5); W6a=T25–T26 (2); W6b=T27–T28 (2); W7=T29–T33 (5); W8=T34 (1, sequential — final island build).
3. After all 34 tasks land green: `cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest -x -q` (expect ≈409); `cd frontend && pnpm test`; `pnpm build && cd .. && git diff --exit-code app/ui/static/island/`.
4. Push: `git -C /home/context/projects/takehome-e7 push -u origin feat/e7-ui`. **DO NOT MERGE.** The user rebases/merges once E5/E6 also land on `main`.

## Constraints/Blockers (UNCHANGED from prior session)

- **HARD: forbidden files (E5/E6 ownership):** `app/services/**`, `app/api/{labels,batches,overrides,healthz}.py`, `app/batch/**`, `app/api/raw.py`. Plan honors this throughout. Escalate to L1 (wire-contract issue) if any task surfaces a need.
- **HARD: no merge to `main` from `feat/e7-ui`.** Push only.
- **HARD: olorin standards** — no SDD; only `parallel-plan-executor`. Conventional commits ≤72 chars. Commit per TDD cycle. Files <300 lines.
- **HARD: Python 3.12** in this worktree (uv default 3.14 is paddlepaddle-incompatible). Always `uv run --python 3.12`.
- **CONTEXT: wire-divergence escalation** — if a canned envelope diverges from what E5/E6 produces, escalate to L1; do NOT silently rework fixtures.
- **CONTEXT: Playwright in CI** — T7 adds `playwright` + `pytest-playwright` to dev deps and runs `playwright install chromium` (~170 MB download).
- **CONTEXT: built-bundle commit invariant** — T33 enforces `pnpm build && git diff --exit-code app/ui/static/island/` returns 0.
- **CONTEXT: 17-component inventory frozen** by PRD §5.6.
- **OPEN QUESTION:** if E6's SSE framing differs (e.g., named events with `event:` lines), T26 hook needs adjustment at integration time — comment now flags this in the hook source.

## Key Files

- **L2 plan (APPROVED):** `/home/context/projects/takehome-e7/docs/plans/ttb-label-verification-epoch-7-l2.md` v0.4
- **L1 sub-doc:** `/home/context/projects/takehome-e7/docs/plans/ttb-label-verification-epoch-7-ui.md`
- **L1 index:** `/home/context/projects/takehome-e7/docs/plans/ttb-label-verification-epochs.md` v0.4
- **PRD:** `/home/context/projects/takehome-e7/docs/PRD.md` (§5.6, §6.2, §6.3)
- **ARCH:** `/home/context/projects/takehome-e7/docs/ARCHITECTURE.md` (§4.2.1, §7, §8.4, §14.1)
- **Wire schemas (locked):** `/home/context/projects/takehome-e7/app/schemas/wire/{disposition,batch}.py`, `app/schemas/{audit,metrics}.py`
- **Reason-code registry:** `/home/context/projects/takehome-e7/rules/reason_codes.yaml`

--- End Progress ---
