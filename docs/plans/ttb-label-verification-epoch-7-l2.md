# TTB Label Verification — Epoch 7 (UI: Jinja2 Shell + React Island) — L2 Implementation Plan

> **Version:** v0.4 (2026-05-04) — plan-review iter-2 (§10 reciprocity warnings); architectural pass APPROVED; ready for parallel-plan-executor. See §9.
>
> **For agentic workers:** REQUIRED EXECUTOR: `parallel-plan-executor`. Per olorin CLAUDE.md, `superpowers:subagent-driven-development` is obsolete and fully replaced by `parallel-plan-executor` (which injects the `task-executor` skill body for TDD enforcement). Each task lands as one Red→Green→Commit cycle inside an isolated subagent (a few bundled tasks contain 2–3 cycles, called out explicitly). Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Parent L1:** [`ttb-label-verification-epoch-7-ui.md`](./ttb-label-verification-epoch-7-ui.md) (v0.1)
> **L1 index:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md) (v0.4)
> **E5 L2 (structural template):** [`ttb-label-verification-epoch-5-l2.md`](./ttb-label-verification-epoch-5-l2.md) (v0.5)
> **PRD:** [`docs/PRD.md`](../PRD.md) — §5.6 (FR-500–511 UX), §6.2 (single-label envelope), §6.3 (batch envelope + SSE), §15.2 (a11y design targets), AC-FR-803, AC-NFR-A11Y-001, NFR-UX-001-004, NFR-A11Y-001-005
> **ARCH:** [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — §4.2.1 (Web layer), §7 (stack), §8.4 (non-substitutable seams), §14.1 (repo layout)
> **ADRs in scope:** D-013 (FastAPI + Jinja2 + React-island stack), D-019 (DEV_MODE raw drawer)

---

## 0. Concurrency context: this branch is `feat/e7-ui`, parallel to E5/E6 on `main`

This plan is being executed in a **git worktree at `/home/context/projects/takehome-e7`** on branch `feat/e7-ui`, running in parallel with another session implementing E5 (Application Service + Audit + single-label flow) and E6 (Batch + SSE + Override) on `main`. The wire schemas E7 consumes (`app/schemas/wire/disposition.py` for §6.2, `app/schemas/wire/batch.py` for §6.3) **already shipped in E1** and are the locked contract this plan binds to. The runtime that *produces* those envelopes (`app/api/labels.py`, `app/api/batches.py`, `app/api/overrides.py`, `app/services/evaluator.py`, `app/batch/*`) is being written concurrently and **does not yet exist** in this worktree. This plan therefore:

1. Builds every UI component, hook, template, and end-to-end test against **canned envelope JSON fixtures** committed under `tests/fixtures/envelopes/`. Each fixture is hand-built from PRD §6.2 / §6.3 and round-trip-validated against the E1 Pydantic schemas at the start of the plan (T3) — so the fixtures are wire-conformant by construction, not by E5/E6 production trace.
2. **Forbidden files** (owned by the parallel session, must NOT be touched): `app/services/*`, `app/api/labels.py`, `app/api/batches.py`, `app/api/overrides.py`, `app/api/healthz.py`, `app/batch/*`. The plan never modifies any of these. Where a Playwright test needs to fire a `POST /labels`-shaped request, it uses Playwright `route.fulfill()` to intercept the request *in the browser* and return a canned envelope — the request never reaches a server route, so the absence of those files is fine.
3. **Allowed surface (this plan's scope):** `frontend/**` (entire — fresh scaffold), `app/ui/templates/**`, `app/ui/static/island/**` (built bundle artifacts), `app/api/ui.py` (new — page-shell GET routes only; not labels/batches/overrides), `app/main.py` (additive: register `ui.router` + `StaticFiles` mount), `pyproject.toml` (additive: `playwright` + `pytest-playwright` in dev group), `uv.lock` (regenerated), `.gitignore` (additive: ignore `frontend/node_modules/`, `frontend/.vite/`, `frontend/dist/` — already present; no change needed), `tests/test_ui_*.py`, `tests/test_a11y_axe.py`, `tests/test_keyboard_model.py`, `tests/test_reflow_320px.py`, `tests/test_disposition_pill_wcag_141.py`, `tests/test_island_build_clean.py`, `tests/test_typescript_envelope_drift.py`, `tests/conftest.py` (additive Playwright fixtures), `tests/fixtures/envelopes/**`, `tests/manual/a11y-smoke.md` (new file).
4. **Wire-divergence escalation.** If during implementation a fixture is found to diverge from what the parallel E5/E6 session is producing, that is a wire-contract issue — escalate to L1 (update epochs L1 + E7 L1 sub-doc), do **NOT** silently rework the fixture; the L1 update may also affect E5/E6.

**No merge to main from this plan.** After all tasks land green and CI is clean, the branch is pushed to origin and waits for the user to rebase/merge once E5/E6 are also on main.

---

## 1. Goal

Ship the reviewer-facing UI surface — Jinja2 server-rendered page shells + React + TypeScript island in `frontend/` (built bundle committed to `app/ui/static/island/`). After E7:

- All **17 components** from PRD §5.6 / T8 are implemented as shadcn/ui-derived React + TypeScript components with Vitest sibling tests covering positive/negative render, keyboard interaction (where applicable), and ARIA semantics.
- The **`O / J / K / ENTER / ESC` keyboard contract** is implemented via a single `useKeyboardShortcuts` hook; AC-FR-803 (canonical override completes in 3 keystrokes: `O → reason → ENTER`) holds.
- The **`useBatchStream` SSE consumer hook** subscribes to `/batches/{batch_id}/stream`, dispatches per-label events into a `useReducer` store, and survives StrictMode double-invocation.
- **USWDS color tokens** are mapped to shadcn/ui CSS variables in a single tokens file.
- **WCAG 2.0 Level AA** clears axe-core CI on every demo fixture envelope (AC-NFR-A11Y-001) — zero violations.
- **FR-511 disposition pill** uses color + shape + text — verified structurally by a DOM-class assertion.
- **NFR-A11Y-004 prefers-reduced-motion**: every animation is gated; verified by Playwright with the media-feature override.
- **NFR-A11Y-005 reflow at 320 CSS px**: verified by Playwright at the 320 viewport.
- The **built island bundle** (`app/ui/static/island/`) is committed; the CI gate `pnpm build && git diff --exit-code app/ui/static/island/` returns 0 (R-5 mitigation).
- The **manual NVDA + VoiceOver smoke checklist** is committed under `tests/manual/a11y-smoke.md` as a release-time human check (out of CI).

After E7, reviewers running the deployed prototype with E5/E6 merged will see exactly the surface PRD §5.6 specifies — field cards, citation chips, evidence panels, override drawer, batch table, queue position, anomaly toasts, raw-JSON drawer (DEV_MODE) — and the experience clears WCAG AA without manual intervention on every PR.

## 2. Architecture

A single **`frontend/`** Vite + React 18 + TypeScript project producing two entry-point bundles, both written to `app/ui/static/island/`:

- `single.tsx` — single-label review island. Mounts on `<div id="root" data-mode="single">` rendered by `single.html`. Reads canned envelope from `<script id="envelope" type="application/json">…</script>` injected by Jinja in dev/test, or fetches from `POST /labels` in production (the production fetch path lands in E5/E8 — this plan only wires the empty-state-aware mount).
- `batch.tsx` — batch review island. Mounts on `<div id="root" data-mode="batch">` rendered by `batch.html`. Reads `batch_id` from a `data-batch-id` attribute and subscribes via `useBatchStream` to `/batches/{batch_id}/stream`; in tests, Playwright `route.fulfill()` stubs the SSE stream.

The Jinja layer (`app/ui/templates/{base,single,batch}.html`) is server-rendered at request time by FastAPI; the only Jinja responsibilities are: (a) produce the document shell with USWDS tokens preloaded, (b) render the `<noscript>` fallback that points at the `POST /labels` JSON API, (c) inject the `<script type="module" src="/static/island/single.js">` (or `batch.js`) reference, (d) optionally embed a server-side canned envelope for SSR-driven first-paint of single-label review.

The 17 components decompose into **primitives** (no component dependencies — `DispositionPill`, `ConfidenceIndicator`, `CitationChip`, `Alert`, `Toast`, `LiveRegion`), **containers** (compose primitives — `FieldCard`, `BboxOverlay`, `EvidencePanel`, `RuleVerdict`, `AISuggestionBlock`, `NeedsBetterPhotoCard`), and **complex/drawers** (depend on primitives + hooks — `OverrideDrawer`, `ReasonCodePicker`, `RawJSONDrawer`, `BatchTable`, `QueuePosition`). Hooks (`useKeyboardShortcuts`, `useBatchStream`) sit alongside.

**No state library.** Component-local state via `useState`/`useReducer`. The single-label mode threads the envelope through props from the entry point; the batch mode uses `useReducer` keyed by `label_ref` so SSE events accumulate without re-render storms.

**Tests at three layers:**
- *Unit (Vitest, in `frontend/`)* — every component + every hook has a sibling `*.test.tsx` covering positive/negative/keyboard/ARIA. Run via `pnpm test`.
- *Server-side a11y / keyboard / reflow (Playwright + axe-core, in `tests/`)* — full-page checks against canned envelopes; Playwright fires up a short-lived FastAPI instance that serves the built island and Jinja shell. Browser-side `route.fulfill()` stubs `POST /labels` and SSE so no E5/E6 runtime is needed.
- *Manual (NVDA + VoiceOver smoke, `tests/manual/a11y-smoke.md`)* — release-time check.

**Tech stack (matches D-013):**

| Layer | Choice | Notes |
|---|---|---|
| Frontend framework | **React 18** (`react@^18.3`, `react-dom@^18.3`) | StrictMode-correct hooks; concurrent features unused. |
| Language | **TypeScript 5** (`typescript@^5.6`) | Strict mode; no `any` outside generated/types. |
| Bundler | **Vite 5** (`vite@^5.4`, `@vitejs/plugin-react@^4.3`) | Two entry points; output to `app/ui/static/island/`. |
| UI primitives | **shadcn/ui** (copy-paste; we own the source under `frontend/src/components/ui/`) + **Radix UI** (`@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`, `@radix-ui/react-tooltip`, `@radix-ui/react-popover`) | WAI-ARIA APG focus management for drawers / overlays / popovers. |
| CSS | **Tailwind CSS 3** (`tailwindcss@^3.4`, `postcss`, `autoprefixer`) + **USWDS color tokens** mapped to shadcn CSS variables | Single tokens file owns the layered cascade. |
| Icons | **lucide-react** (`lucide-react@^0.453`) | Tree-shakeable; no Font Awesome / Heroicons. |
| Class utility | **clsx** + **tailwind-merge** (`clsx@^2`, `tailwind-merge@^2`) | Standard shadcn `cn()` helper. |
| Test runner (JS) | **Vitest** (`vitest@^2.1`) + **@testing-library/react@^16** + **@testing-library/jest-dom@^6** + **@testing-library/user-event@^14** + **jsdom@^25** + **vitest-axe@^0.1** | Component-level a11y via vitest-axe; Vitest runs in `frontend/`. |
| Test runner (E2E) | **Playwright** (`playwright@^1.48`) + **pytest-playwright@^0.6** + **axe-core@^4.10** (loaded as a `<script>` tag in Playwright tests from `frontend/node_modules/axe-core/axe.min.js`) | Real browser; full-page WCAG checks against canned envelopes via `route.fulfill()`. |
| Package manager | **pnpm 9** | `pnpm-lock.yaml` committed; no `node_modules` committed. |

**No dynamic provider / global state library**. **No SSR framework** beyond plain Jinja string-templating. **No router** (the page shell is Jinja-routed; the island is page-mode-specific via `data-mode`).

**Hard scope boundary (what this plan does NOT touch):**

- `app/services/**`, `app/api/labels.py`, `app/api/batches.py`, `app/api/overrides.py`, `app/api/healthz.py`, `app/batch/**`, `app/api/raw.py` — these are owned by E5/E6 (and the parallel session is implementing them on `main`). The plan **never** imports them, edits them, or registers their routers.
- `app/schemas/**` — the E1 wire schemas are the locked contract; the plan reads them but never modifies them.
- `app/rules/**`, `app/orchestrator/**`, `app/vision/**` — engine internals unrelated to UI.

The plan **does** modify `app/main.py` (additive: import `ui.router` and `StaticFiles`, register both inside `create_app`); the modification is a 4-line addition that touches no existing logic and is asserted by a fresh test (T7) that the existing `/healthz` route still returns 200.

## 3. Conventions used in this plan

- **Frontend project root.** All `frontend/`-relative paths resolve from `/home/context/projects/takehome-e7/frontend/`. All `app/`, `tests/`, `docs/` paths resolve from the worktree root.
- **TypeScript strictness.** `tsconfig.json` sets `"strict": true`, `"noUncheckedIndexedAccess": true`, `"noImplicitOverride": true`. No `any` outside the generated types module (which has none anyway). Components use discriminated unions where appropriate (e.g., `ai_suggestion.present === true` narrows `task | text | model_disposition` to non-null).
- **Component file shape.** Every component file under `frontend/src/components/` exports the component as a named export and defines a `Props` type (or interface) above the component. No default exports. Sibling test file co-located (`Foo.tsx` + `Foo.test.tsx`).
- **shadcn/ui primitives** (`Button`, `Card`, `Dialog`, `Tooltip`, `Badge`) live under `frontend/src/components/ui/` (copied source per shadcn convention). Application components live under `frontend/src/components/`. Hooks under `frontend/src/hooks/`. Types under `frontend/src/types/`. SSE under `frontend/src/sse/`. Tokens under `frontend/src/tokens/`.
- **Tailwind layer convention.** USWDS tokens emit as `--uswds-*` CSS vars on `:root` (light) and `:root[data-theme="dark"]` (dark). shadcn's `--primary`, `--background`, `--foreground` etc. are declared in terms of `--uswds-*` so the cascade is single-source. No dark mode in MVP; the `data-theme="dark"` block is structural placeholder.
- **`cn()` helper.** `frontend/src/lib/cn.ts` exports `cn(...inputs: ClassValue[])` returning `twMerge(clsx(inputs))`. Used by every component to compose Tailwind class strings safely.
- **ARIA semantics.** Every component documents its ARIA role in a comment on its main JSX element. Components that use Radix primitives inherit Radix's WAI-ARIA conformance. Custom overlays (`BboxOverlay`) declare `role`, `tabIndex`, `aria-pressed`, `aria-label` explicitly and assert them in their Vitest test.
- **Vitest test recipe.** Every test file uses this skeleton. The `renderWithProviders` helper just wraps in `<React.StrictMode>` so double-invocation is exercised in unit tests too. Components that need a `LiveRegion` ancestor declare it locally in the test (the entry-point provides it in production).

  ```tsx
  // frontend/src/test/render.tsx
  import { render } from "@testing-library/react";
  import * as React from "react";
  
  export function renderWithProviders(ui: React.ReactElement) {
    return render(<React.StrictMode>{ui}</React.StrictMode>);
  }
  ```

- **vitest-axe pattern.** Each component test ends with one `axe(container)` assertion to catch component-level a11y regressions. Full-page WCAG audits are handled by Playwright in `tests/`.
- **Playwright pattern.** Python tests under `tests/test_a11y_axe.py` etc. start a `uvicorn` instance via a `pytest-playwright` fixture; the fixture serves the Jinja shell + built island; tests use `page.route("**/labels", lambda r: r.fulfill(json=canned_envelope))` to stub the data layer. The axe-core script is added per-page via `page.add_script_tag(path="frontend/node_modules/axe-core/axe.min.js")` and run via `page.evaluate("() => window.axe.run({runOnly: ['wcag2a', 'wcag2aa']})")`.
- **Conventional Commits ≤72 chars.** Every commit uses `feat|fix|test|docs|chore|refactor: <subject>` format. Per-task commit messages are explicit in each task.
- **File size discipline (CLAUDE.md).** Every component file targets <200 lines, hard ceiling 300. Tests target <300 lines. The plan splits when ceilings would be exceeded.
- **No global state / no Redux / no Zustand.** `useReducer` for the batch table store; component-local `useState` everywhere else.
- **No fetching from `POST /labels` directly in this plan.** The single-label island reads its envelope from a `<script id="envelope" type="application/json">` block injected by Jinja (when present); when absent (production runtime once E5/E8 lands), it shows an empty/loading state. The PRODUCTION fetch implementation is out of E7 scope (it lands in E5 or E8 wiring).
- **Forbidden imports.** No file under `frontend/` imports anything from `app/`. No file under `app/api/ui.py` imports anything from `app/services/`, `app/orchestrator/`, `app/vision/`, or `app/rules/` — `ui.py` is template-rendering only.

## 4. File map

Every file the plan creates or modifies, paired with the task that owns it. Disjoint file ownership across waves is the parallel-plan-executor invariant; tasks within a wave never share write surface.

| Path | Created/modified by | Responsibility |
|---|---|---|
| `frontend/package.json` | T1 | pnpm manifest; deps + scripts (`dev`, `build`, `test`). |
| `frontend/pnpm-lock.yaml` | T1 | pnpm lockfile (regenerated by `pnpm install`; committed). |
| `frontend/tsconfig.json` | T1 | Strict TS config; targets ES2022. |
| `frontend/tsconfig.node.json` | T1 | TS config for `vite.config.ts`. |
| `frontend/vite.config.ts` | T1 | Two entry points (`single.tsx`, `batch.tsx`); `build.outDir: '../app/ui/static/island'`. |
| `frontend/tailwind.config.ts` | T1 | Tailwind config; content globs for `src/**/*.{ts,tsx}`; theme extends with USWDS tokens. |
| `frontend/postcss.config.js` | T1 | postcss + autoprefixer. |
| `frontend/.eslintrc.cjs` | T1 | Optional lint config (eslint-config-react). May be skipped — Vitest covers regressions. |
| `frontend/index.html` | T1 | (Vite dev-only landing page; not used in production but required by Vite dev server.) |
| `frontend/src/lib/cn.ts` | T1 | `cn()` helper. |
| `frontend/src/test/setup.ts` | T1 | Vitest setup: imports `@testing-library/jest-dom` and registers `vitest-axe` extensions. |
| `frontend/src/test/render.tsx` | T1 | `renderWithProviders` helper. |
| `frontend/src/test/smoke.test.tsx` | T1 | One-line smoke test that the runner works. |
| `frontend/vitest.config.ts` | T1 | Vitest config; jsdom; setupFiles = `src/test/setup.ts`. |
| `frontend/src/tokens/uswds-tokens.css` | T2 | USWDS color tokens as `--uswds-*` vars. |
| `frontend/src/tokens/globals.css` | T2 | Tailwind directives + shadcn CSS variable layer (mapped from USWDS). |
| `frontend/src/tokens/uswds-tokens.test.ts` | T2 | Asserts CSS file contains the required token names (drift canary). |
| `tests/fixtures/envelopes/single/01-spirits-clean.json` | T3 | Canned PRD §6.2 happy-path envelope. |
| `tests/fixtures/envelopes/single/02-bourbon-stones-throw.json` | T3 | Brand AI suggestion present (FR-300 trigger). |
| `tests/fixtures/envelopes/single/03-warning-title-case.json` | T3 | `fail` disposition; `WARNING.STYLE.HEADING_NOT_BOLD_CAPS`. |
| `tests/fixtures/envelopes/single/04-low-res-blurry.json` | T3 | `needs_review` + `WARNING.LEGIBILITY.LOW_RESOLUTION` (NeedsBetterPhotoCard). |
| `tests/fixtures/envelopes/single/06-abv-out-of-tolerance.json` | T3 | `fail` + `ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND`. |
| `tests/fixtures/envelopes/single/07-borderline-confidence.json` | T3 | `needs_review` via FR-704 min-aggregation; `BRAND.NAME.NEEDS_REVIEW` + AI suggestion. |
| `tests/fixtures/envelopes/batch/05-batch-of-50-envelope.json` | T3 | PRD §6.3 `BatchEnvelope` with 5 items (subset of fixture-05 to keep the plan tractable). |
| `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl` | T3 | Per-label SSE event sequence: 5 events, each a §6.2 envelope augmented with `batch_id` + `queue_position`. |
| `tests/test_canned_envelopes_round_trip.py` | T3 | Asserts every JSON fixture deserializes to `DispositionEnvelope` / `BatchEnvelope`. |
| `app/ui/templates/base.html` | T4 | Global page shell: header, USWDS tokens preload, skip-link, footer, `<noscript>` fallback. |
| `app/ui/templates/single.html` | T4 | Single-label review page; mounts `<div id="root" data-mode="single">`; embeds canned envelope script tag. |
| `app/ui/templates/batch.html` | T4 | Batch review page; mounts `<div id="root" data-mode="batch" data-batch-id="…">`. |
| `app/api/ui.py` | T4 | `GET /` (or `/single`) and `GET /batch/{batch_id}` page-shell routes. **Template rendering only.** No engine imports. |
| `app/main.py` | T4 | Additive: import `ui.router`; register `StaticFiles` mount at `/static`; register `ui.router`. |
| `tests/test_ui_routes.py` | T4 | Asserts `GET /` and `GET /batch/abc-123` return 200 + correct `data-mode`; `/healthz` still 200. |
| `frontend/src/types/envelopes.ts` | T5 | TypeScript types hand-mirrored from `app/schemas/wire/disposition.py` + `app/schemas/wire/batch.py`. |
| `tests/test_typescript_envelope_drift.py` | T5 | Greps Pydantic schema fields and asserts each appears in the .ts file. |
| `frontend/src/types/sse.ts` | T5 | `BatchSSEEvent` type wrapping per-label envelope + `batch_id` + `queue_position`. |
| `frontend/src/test/setup-vitest.test.tsx` | T6 | Vitest smoke (asserts `expect.toBeInTheDocument` extension is registered). (Folded into T1 if simpler — kept separate for parallel split.) |
| `tests/conftest.py` | T7 | Additive: Playwright + uvicorn fixtures (`live_server`, `live_server_url`, `pnpm_built_island`). |
| `pyproject.toml` | T7 | Additive: `playwright` + `pytest-playwright` in `[dependency-groups] dev`. |
| `tests/test_playwright_harness_smoke.py` | T7 | Asserts the Playwright fixture launches and serves the Jinja shell. |
| `frontend/src/components/DispositionPill.tsx` (+ `.test.tsx`) | T8 | FR-511 — color + shape + text. |
| `frontend/src/components/ConfidenceIndicator.tsx` (+ `.test.tsx`) | T9 | FR-510 — numeric + tri-state band. |
| `frontend/src/components/CitationChip.tsx` (+ `.test.tsx`) | T10 | FR-502 — chip with click → opens `EvidencePanel`. |
| `frontend/src/components/Alert.tsx` (+ `.test.tsx`) | T11 | FR-506 — WCAG 4.1.3 status-message pattern. |
| `frontend/src/components/Toast.tsx` (+ `.test.tsx`) | T12 | FR-506 — transient confirmations. |
| `frontend/src/components/LiveRegion.tsx` (+ `.test.tsx`) | T13 | FR-507 — `aria-live="polite"` announcer. |
| `frontend/src/components/FieldCard.tsx` (+ `.test.tsx`) | T14 | FR-500 — single field card. |
| `frontend/src/components/BboxOverlay.tsx` (+ `.test.tsx`) | T15 | FR-501 — SVG over `<img>`; ARIA + keyboard. |
| `frontend/src/components/EvidencePanel.tsx` (+ `.test.tsx`) | T16 | FR-502 — regulation text + extracted evidence. |
| `frontend/src/components/RuleVerdict.tsx` (+ `.test.tsx`) | T17 | FR-500/503 — deterministic verdict, visibly separated. |
| `frontend/src/components/AISuggestionBlock.tsx` (+ `.test.tsx`) | T18 | FR-503 — AI suggestion, never as verdict. |
| `frontend/src/components/NeedsBetterPhotoCard.tsx` (+ `.test.tsx`) | T19 | FR-505 — first-class disposition. |
| `frontend/src/components/ReasonCodePicker.tsx` (+ `.test.tsx`) | T20 | FR-504 — typeahead w/ prefix-uniqueness resolution. |
| `frontend/src/components/RawJSONDrawer.tsx` (+ `.test.tsx`) | T21 | FR-508 — DEV_MODE-gated. |
| `frontend/src/components/QueuePosition.tsx` (+ `.test.tsx`) | T22 | FR-406 — current/total + ARIA. |
| `frontend/src/components/BatchTable.tsx` (+ `.test.tsx`) | T23 | FR-509 — sortable + keyboard-selectable. |
| `frontend/src/hooks/useKeyboardShortcuts.ts` (+ `.test.ts`) | T24 | `O / J / K / Enter / Esc` keyboard model. |
| `frontend/src/components/OverrideDrawer.tsx` (+ `.test.tsx`) | T25 | FR-504/803 — 3-keystroke override drawer. |
| `frontend/src/sse/useBatchStream.ts` (+ `.test.ts`) | T26 | SSE consumer hook. |
| `frontend/src/single.tsx` | T27 | Single-label island entry point. |
| `frontend/src/batch.tsx` | T28 | Batch island entry point. |
| `tests/test_a11y_axe.py` | T29 | Playwright + axe-core; zero AA violations on every fixture envelope. |
| `tests/test_keyboard_model.py` | T30 | 3-keystroke override + `J/K` navigation. |
| `tests/test_reflow_320px.py` | T31 | Layout reflow at 320 CSS px; no 2-D scroll. |
| `tests/test_disposition_pill_wcag_141.py` | T32 | DOM-class + text assertion (color + shape + text). |
| `tests/test_island_build_clean.py` | T33 | `pnpm build && git diff --exit-code app/ui/static/island/`. |
| `tests/manual/a11y-smoke.md` | T33 | NVDA + VoiceOver checklist (manual). |
| `app/ui/static/island/single.js`, `single.css`, `batch.js`, `batch.css`, `*.map` | T34 | Built bundle artifacts (committed). |

## 5. Wave dependency graph

| Wave | Tasks | Concurrent | Depends on |
|---|---|---|---|
| 1 | T1, T2, T3, T4 | 4 (executor cap = 6) | — |
| 2 | T5, T6, T7 | 3 | W1 |
| 3 | T8, T9, T10, T11, T12, T13 | **6 (cap)** | W2 |
| 4 | T14, T15, T16, T17, T18, T19 | **6 (cap)** | W3 |
| 5 | T20, T21, T22, T23, T24 | 5 | W3 (most), W4 (T23 reads DispositionPill from W3 only) |
| 6a | T25, T26 | 2 | W5 |
| 6b | T27, T28 | 2 | W6a |
| 7 | T29, T30, T31, T32, T33 | 5 | W6b |
| 8 | T34 | 1 (sequential, final) | W7 |

**Wave-level dependency notes:**
- W3 primitives have **no inter-task dependencies** within the wave (each is a leaf component) — full executor parallelism.
- W4 containers each depend on one or more W3 primitives. Within the wave, no two W4 tasks share a write surface (each task creates its own `Foo.tsx` + `Foo.test.tsx`).
- W5: T20–T23 are leaf components or compose-only; T24 (`useKeyboardShortcuts`) is a pure hook with no component deps.
- **W6 split into W6a / W6b** (parallel-planning audit, v0.2): T27 imports T25 `OverrideDrawer` and T28 imports T26 `useBatchStream` — running all four tasks in one wave is a same-wave race because T27 / T28 read symbols that T25 / T26 are creating concurrently. W6a (T25 `OverrideDrawer` reads T20 + T24; T26 `useBatchStream` reads T1 + T5) lands first; W6b (T27 single entry point; T28 batch entry point) follows.
- W7 tests depend on all components + entry points being on disk. **Conftest race fix (v0.2):** the `pnpm_built_island` Playwright session fixture now lives in T7 (W2) alongside `live_server` — T29/T30/T31/T32 all consume it as a read-only dependency, so no two W7 tasks contend on `tests/conftest.py`. T33 also depends on T34's build, so T33's test is structured to RUN the build itself (`pnpm build`) and assert the diff is clean — meaning T33 doesn't *depend* on a prior commit of `app/ui/static/island/`, it produces the diff fresh.
- **W8 is mechanical and sequential**: run `pnpm build`, stage the artifacts, commit. No new test code; ensures `tests/test_island_build_clean.py` is green on the *post-T34* state.

## 6. Pre-flight: verify worktree baseline

Before T1, the executor (or human) confirms:

- Worktree at `/home/context/projects/takehome-e7`, branch `feat/e7-ui`.
- `uv run pytest -x -q` from worktree root → 375 passed (matches the baseline captured at worktree creation).
- `git status --short` → empty.
- `pnpm` is on PATH; `pnpm --version` → 9.x. If absent, install: `npm install -g pnpm@9` (one-time machine setup; not part of the plan).
- `playwright --version` is NOT yet on PATH (T7 adds it via `uv sync`).

---

## 7. Tasks

> **Task ID convention.** T1–T34 (single sequence). Each task heading lists its **wave**, **dependencies**, and **owned files**. Steps use `- [ ]` checkboxes. Every task ends in a single `git commit` (or 2–3 commits for explicitly-bundled multi-cycle tasks; called out in the heading).


### Task T1 — Frontend scaffold (pnpm + Vite + Tailwind + Vitest)

**Wave:** 1
**Depends on:** —
**Owns (creates):** `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/postcss.config.js`, `frontend/index.html`, `frontend/vitest.config.ts`, `frontend/src/lib/cn.ts`, `frontend/src/test/setup.ts`, `frontend/src/test/render.tsx`, `frontend/src/test/smoke.test.tsx`.

This is the largest single task in the plan because the frontend project is being scaffolded from scratch. It is **one Red→Green→Commit cycle** because everything must land together for `pnpm install && pnpm test` to work. The "test" is the smoke test in `src/test/smoke.test.tsx` — Red is "no package.json, pnpm install fails", Green is "smoke test passes".

- [ ] **Step 1: Write the smoke test (Red — file does not yet exist; the test runner does not yet exist either, but writing the test first locks the contract).**

  Create `frontend/src/test/smoke.test.tsx`:

  ```tsx
  import { describe, it, expect } from "vitest";
  import { renderWithProviders } from "./render";

  describe("vitest smoke", () => {
    it("renders a div", () => {
      const { container } = renderWithProviders(<div data-testid="x">hello</div>);
      expect(container.querySelector('[data-testid="x"]')).not.toBeNull();
    });
  });
  ```

- [ ] **Step 2: Verify the smoke test cannot yet run (Red).**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test 2>&1 | tail -5
  ```

  Expected: `pnpm: command not found` or `ENOENT package.json`. Either is fine — the point is "the test runner cannot start because nothing is wired yet".

- [ ] **Step 3: Create `frontend/package.json`.**

  ```json
  {
    "name": "ttb-label-island",
    "private": true,
    "version": "0.0.0",
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "tsc -b && vite build",
      "test": "vitest run",
      "test:watch": "vitest"
    },
    "dependencies": {
      "@radix-ui/react-dialog": "^1.1.2",
      "@radix-ui/react-dropdown-menu": "^2.1.2",
      "@radix-ui/react-popover": "^1.1.2",
      "@radix-ui/react-tooltip": "^1.1.4",
      "clsx": "^2.1.1",
      "lucide-react": "^0.453.0",
      "react": "^18.3.1",
      "react-dom": "^18.3.1",
      "tailwind-merge": "^2.5.4"
    },
    "devDependencies": {
      "@testing-library/jest-dom": "^6.6.3",
      "@testing-library/react": "^16.0.1",
      "@testing-library/user-event": "^14.5.2",
      "@types/react": "^18.3.12",
      "@types/react-dom": "^18.3.1",
      "@vitejs/plugin-react": "^4.3.3",
      "autoprefixer": "^10.4.20",
      "axe-core": "^4.10.2",
      "jsdom": "^25.0.1",
      "postcss": "^8.4.49",
      "tailwindcss": "^3.4.14",
      "typescript": "^5.6.3",
      "vite": "^5.4.10",
      "vitest": "^2.1.4",
      "vitest-axe": "^0.1.0"
    }
  }
  ```

- [ ] **Step 4: Create `frontend/tsconfig.json`.**

  ```json
  {
    "compilerOptions": {
      "target": "ES2022",
      "useDefineForClassFields": true,
      "lib": ["ES2022", "DOM", "DOM.Iterable"],
      "module": "ESNext",
      "skipLibCheck": true,
      "moduleResolution": "bundler",
      "allowImportingTsExtensions": true,
      "resolveJsonModule": true,
      "isolatedModules": true,
      "noEmit": true,
      "jsx": "react-jsx",
      "strict": true,
      "noUnusedLocals": true,
      "noUnusedParameters": true,
      "noUncheckedIndexedAccess": true,
      "noImplicitOverride": true,
      "noFallthroughCasesInSwitch": true,
      "esModuleInterop": true,
      "types": ["vitest/globals"]
    },
    "include": ["src"],
    "references": [{ "path": "./tsconfig.node.json" }]
  }
  ```

- [ ] **Step 5: Create `frontend/tsconfig.node.json`.**

  ```json
  {
    "compilerOptions": {
      "composite": true,
      "skipLibCheck": true,
      "module": "ESNext",
      "moduleResolution": "bundler",
      "allowSyntheticDefaultImports": true,
      "strict": true
    },
    "include": ["vite.config.ts", "vitest.config.ts", "tailwind.config.ts", "postcss.config.js"]
  }
  ```

- [ ] **Step 6: Create `frontend/vite.config.ts`.**

  Output goes to `app/ui/static/island/` (relative to the worktree root, i.e. `../app/ui/static/island/` from `frontend/`). Two entry points — `single.tsx` and `batch.tsx`. CSS is split per entry.

  ```ts
  import { defineConfig } from "vite";
  import react from "@vitejs/plugin-react";
  import { resolve } from "node:path";

  export default defineConfig({
    plugins: [react()],
    build: {
      outDir: resolve(__dirname, "../app/ui/static/island"),
      emptyOutDir: true,
      manifest: false,
      sourcemap: true,
      rollupOptions: {
        input: {
          single: resolve(__dirname, "src/single.tsx"),
          batch: resolve(__dirname, "src/batch.tsx"),
        },
        output: {
          entryFileNames: "[name].js",
          assetFileNames: "[name][extname]",
          chunkFileNames: "chunks/[name]-[hash].js",
        },
      },
    },
  });
  ```

- [ ] **Step 7: Create `frontend/vitest.config.ts`.**

  ```ts
  import { defineConfig } from "vitest/config";
  import react from "@vitejs/plugin-react";

  export default defineConfig({
    plugins: [react()],
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
      globals: true,
      css: true,
    },
  });
  ```

- [ ] **Step 8: Create `frontend/tailwind.config.ts`.**

  USWDS tokens are referenced symbolically; the actual values land in T2's `uswds-tokens.css` and are bridged into Tailwind via CSS variables.

  ```ts
  import type { Config } from "tailwindcss";

  export default {
    content: ["./src/**/*.{ts,tsx,html}"],
    theme: {
      extend: {
        colors: {
          // shadcn-compatible variables; values bound in src/tokens/globals.css
          background: "hsl(var(--background))",
          foreground: "hsl(var(--foreground))",
          primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
          destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
          warning: { DEFAULT: "hsl(var(--warning))", foreground: "hsl(var(--warning-foreground))" },
          muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
          border: "hsl(var(--border))",
          ring: "hsl(var(--ring))",
        },
        borderRadius: {
          lg: "var(--radius)",
          md: "calc(var(--radius) - 2px)",
          sm: "calc(var(--radius) - 4px)",
        },
      },
    },
    plugins: [],
  } satisfies Config;
  ```

- [ ] **Step 9: Create `frontend/postcss.config.js`.**

  ```js
  export default {
    plugins: {
      tailwindcss: {},
      autoprefixer: {},
    },
  };
  ```

- [ ] **Step 10: Create `frontend/index.html` (Vite dev entry only — production uses Jinja).**

  ```html
  <!doctype html>
  <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>TTB Label Verification — Dev</title>
    </head>
    <body>
      <div id="root" data-mode="single"></div>
      <script type="module" src="/src/single.tsx"></script>
    </body>
  </html>
  ```

- [ ] **Step 11: Create `frontend/src/lib/cn.ts`.**

  ```ts
  import { clsx, type ClassValue } from "clsx";
  import { twMerge } from "tailwind-merge";

  export function cn(...inputs: ClassValue[]): string {
    return twMerge(clsx(inputs));
  }
  ```

- [ ] **Step 12: Create `frontend/src/test/setup.ts`.**

  ```ts
  import "@testing-library/jest-dom/vitest";
  import { expect } from "vitest";
  import * as matchers from "vitest-axe/matchers";

  expect.extend(matchers);
  ```

- [ ] **Step 13: Create `frontend/src/test/render.tsx`.**

  ```tsx
  import { render, type RenderResult } from "@testing-library/react";
  import * as React from "react";

  export function renderWithProviders(ui: React.ReactElement): RenderResult {
    return render(<React.StrictMode>{ui}</React.StrictMode>);
  }
  ```

- [ ] **Step 14: Install + run smoke test (Green).**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm install && pnpm test
  ```

  Expected output (last two lines):

  ```
  Test Files  1 passed (1)
       Tests  1 passed (1)
  ```

  If `pnpm install` errors on a peer-dep, prefer `pnpm install --strict-peer-dependencies=false` over downgrading versions, then re-pin in pnpm-lock.

- [ ] **Step 15: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add frontend/package.json frontend/pnpm-lock.yaml frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/vitest.config.ts frontend/tailwind.config.ts frontend/postcss.config.js frontend/index.html frontend/src/lib/cn.ts frontend/src/test/setup.ts frontend/src/test/render.tsx frontend/src/test/smoke.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): frontend scaffold — Vite + React + TS + Tailwind + Vitest"
  ```

---

### Task T2 — USWDS tokens + Tailwind globals

**Wave:** 1
**Depends on:** —
**Owns (creates):** `frontend/src/tokens/uswds-tokens.css`, `frontend/src/tokens/globals.css`, `frontend/src/tokens/uswds-tokens.test.ts`.

USWDS color tokens encode the federal-government-friendly palette. shadcn-compatible CSS variables (`--background`, `--foreground`, `--primary`, etc.) are bound to USWDS tokens so the cascade is single-source.

- [ ] **Step 1: Write the failing test (Red) — `frontend/src/tokens/uswds-tokens.test.ts`.**

  ```ts
  import { describe, it, expect } from "vitest";
  import { readFileSync } from "node:fs";
  import { resolve } from "node:path";

  const tokensCss = readFileSync(
    resolve(__dirname, "uswds-tokens.css"),
    "utf-8",
  );
  const globalsCss = readFileSync(
    resolve(__dirname, "globals.css"),
    "utf-8",
  );

  describe("USWDS token presence", () => {
    it.each([
      "--uswds-base-darkest",
      "--uswds-primary",
      "--uswds-primary-darker",
      "--uswds-primary-vivid",
      "--uswds-secondary",
      "--uswds-success",
      "--uswds-warning",
      "--uswds-error",
      "--uswds-info",
    ])("declares %s", (token) => {
      expect(tokensCss).toContain(token);
    });
  });

  describe("shadcn variable bridging", () => {
    it.each([
      "--background",
      "--foreground",
      "--primary",
      "--primary-foreground",
      "--destructive",
      "--warning",
      "--muted",
      "--border",
      "--ring",
      "--radius",
    ])("declares %s", (variable) => {
      expect(globalsCss).toContain(variable);
    });

    it("includes Tailwind directives", () => {
      expect(globalsCss).toMatch(/@tailwind base/);
      expect(globalsCss).toMatch(/@tailwind components/);
      expect(globalsCss).toMatch(/@tailwind utilities/);
    });
  });
  ```

- [ ] **Step 2: Run the test — it should fail because the CSS files don't exist.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/tokens/
  ```

  Expected: `ENOENT: no such file or directory, open '.../uswds-tokens.css'`.

- [ ] **Step 3: Create `frontend/src/tokens/uswds-tokens.css`.**

  Values are USWDS v3 standard tokens (HSL form for shadcn compatibility; spec at https://designsystem.digital.gov/design-tokens/color/system-tokens/). Approximated to nearest HSL with the canonical USWDS hex equivalents in comments.

  ```css
  /* USWDS v3 system color tokens — HSL form for shadcn compatibility.
     Source: https://designsystem.digital.gov/design-tokens/color/system-tokens/ */
  :root {
    /* Neutrals (USWDS "base" family) */
    --uswds-base-lightest: 240 9% 96%;   /* #f0f0f0 */
    --uswds-base-lighter:  240 4% 88%;   /* #dfe1e2 */
    --uswds-base-light:    240 3% 75%;   /* #a9aeb1 */
    --uswds-base:          210 8% 49%;   /* #71767a */
    --uswds-base-dark:     210 9% 31%;   /* #565c65 */
    --uswds-base-darker:   213 18% 22%;  /* #3d4551 */
    --uswds-base-darkest:  213 28% 14%;  /* #1b1b1b */
    --uswds-ink:           213 28% 14%;  /* #1b1b1b */
    --uswds-white:         0 0% 100%;

    /* Primary (USWDS "blue" family — federal default) */
    --uswds-primary-lighter: 209 71% 90%; /* #d9e8f6 */
    --uswds-primary-light:   209 65% 73%; /* #73b3e7 */
    --uswds-primary:         209 64% 41%; /* #005ea2 */
    --uswds-primary-vivid:   211 79% 36%; /* #0050d8 */
    --uswds-primary-dark:    211 76% 28%; /* #1a4480 */
    --uswds-primary-darker:  214 56% 21%; /* #162e51 */

    /* Secondary (USWDS "red" family) */
    --uswds-secondary-lighter: 359 100% 95%;
    --uswds-secondary-light:   358 73% 79%;
    --uswds-secondary:         356 67% 49%; /* #d83933 */
    --uswds-secondary-dark:    355 79% 35%; /* #b50909 */
    --uswds-secondary-darker:  351 75% 22%;

    /* State colors */
    --uswds-success-light:   97 56% 80%;
    --uswds-success:         99 52% 32%;  /* #00a91c */
    --uswds-success-dark:    99 64% 19%;
    --uswds-warning-light:   45 100% 84%;
    --uswds-warning:         44 100% 50%; /* #ffbe2e */
    --uswds-warning-dark:    36 100% 31%; /* #936f38 */
    --uswds-error-lighter:   359 100% 92%;
    --uswds-error:           356 67% 49%; /* #d54309 */
    --uswds-error-dark:      355 79% 35%; /* #b50909 */
    --uswds-info-light:      198 100% 90%;
    --uswds-info:            198 65% 39%; /* #00bde3 */
    --uswds-info-dark:       198 100% 24%;

    /* Disposition palette (E7-specific; layered atop USWDS state tokens) */
    --uswds-disposition-pass:         var(--uswds-success);
    --uswds-disposition-fail:         var(--uswds-error);
    --uswds-disposition-needs-review: var(--uswds-warning-dark);
  }
  ```

- [ ] **Step 4: Create `frontend/src/tokens/globals.css`.**

  ```css
  @import "./uswds-tokens.css";

  @tailwind base;
  @tailwind components;
  @tailwind utilities;

  /* shadcn-compatible variable layer — bound to USWDS tokens so the cascade has
     a single source. */
  :root {
    --background: var(--uswds-white);
    --foreground: var(--uswds-base-darkest);

    --primary: var(--uswds-primary);
    --primary-foreground: var(--uswds-white);

    --destructive: var(--uswds-error);
    --destructive-foreground: var(--uswds-white);

    --warning: var(--uswds-warning-dark);
    --warning-foreground: var(--uswds-white);

    --muted: var(--uswds-base-lightest);
    --muted-foreground: var(--uswds-base-dark);

    --border: var(--uswds-base-lighter);
    --ring: var(--uswds-primary-vivid);

    --radius: 0.375rem;
  }

  /* Body baseline — senior-friendly defaults per NFR-UX-001 (73-year-old benchmark):
     readable line-height, generous default font, high-contrast text. */
  html {
    font-size: 18px;
    line-height: 1.5;
  }

  body {
    background: hsl(var(--background));
    color: hsl(var(--foreground));
    font-family: system-ui, -apple-system, "Segoe UI", "Public Sans", sans-serif;
  }

  /* Skip link — visually hidden until focused (NFR-A11Y-002 keyboard-operable). */
  .skip-link {
    position: absolute;
    top: -100px;
    left: 0;
    padding: 0.5rem 1rem;
    background: hsl(var(--foreground));
    color: hsl(var(--background));
    z-index: 50;
  }
  .skip-link:focus {
    top: 0;
  }

  /* Focus visible — strong outline for keyboard users. */
  :focus-visible {
    outline: 3px solid hsl(var(--ring));
    outline-offset: 2px;
  }

  /* Reduced-motion gate (NFR-A11Y-004). All component animations sit under
     @media (prefers-reduced-motion: no-preference); this rule is the canary. */
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```

- [ ] **Step 5: Run the test (Green).**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/tokens/
  ```

  Expected: 11 passing tests (9 USWDS tokens + 9 shadcn vars + 1 Tailwind directives = 19; or however the `it.each` groups). Confirm `Test Files  1 passed`.

- [ ] **Step 6: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add frontend/src/tokens/uswds-tokens.css frontend/src/tokens/globals.css frontend/src/tokens/uswds-tokens.test.ts
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): USWDS color tokens + shadcn theme bridge"
  ```

---

### Task T3 — Canned envelope JSON fixtures + Pydantic round-trip

**Wave:** 1
**Depends on:** — (uses already-shipped E1 schemas under `app/schemas/wire/`)
**Owns (creates):** 6 single-label fixtures + 1 batch fixture + 1 SSE event-sequence file under `tests/fixtures/envelopes/`, plus `tests/test_canned_envelopes_round_trip.py`.

The 6 single fixtures and the batch fixture cover the dispositions / surfaces the rest of the plan needs to render. They are **hand-built** from PRD §6.2 / §6.3 and validated against the E1 Pydantic schemas (`DispositionEnvelope`, `BatchEnvelope`). Once green, every later task that needs envelope data **reads from these files** and never fabricates inline JSON.

The fixture set is intentionally smaller than fixtures 01–07 (one fixture per disposition + AI-suggestion variant): the 7-fixture coverage required by AC-NFR-A11Y-001 is satisfied by the Playwright a11y test (T29) parametrizing across the canned set + permuted variants — not by 7 distinct hand-built JSONs.

- [ ] **Step 1: Write the failing test (Red) — `tests/test_canned_envelopes_round_trip.py`.**

  ```python
  """T3: every canned envelope JSON deserializes to its locked E1 schema.
  
  These fixtures are the foundation of the E7 UI test suite. If E5/E6 produce
  envelopes with shapes that diverge from these files, that's a wire-contract
  issue — escalate to L1 (do NOT silently rework the fixture).
  """
  from __future__ import annotations
  
  import json
  from pathlib import Path
  
  import pytest
  
  from app.schemas.wire.batch import BatchEnvelope
  from app.schemas.wire.disposition import DispositionEnvelope
  
  
  FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "envelopes"
  SINGLE_DIR = FIXTURE_ROOT / "single"
  BATCH_DIR = FIXTURE_ROOT / "batch"
  
  
  @pytest.mark.parametrize(
      "fixture_name",
      [
          "01-spirits-clean.json",
          "02-bourbon-stones-throw.json",
          "03-warning-title-case.json",
          "04-low-res-blurry.json",
          "06-abv-out-of-tolerance.json",
          "07-borderline-confidence.json",
      ],
  )
  def test_single_envelope_round_trip(fixture_name: str) -> None:
      payload = json.loads((SINGLE_DIR / fixture_name).read_text())
      envelope = DispositionEnvelope.model_validate(payload)
      # Round-trip: serialize back to dict and assert no drift on a sentinel field.
      assert envelope.evaluation_id == payload["evaluation_id"]
      assert envelope.disposition == payload["disposition"]
  
  
  def test_batch_envelope_round_trip() -> None:
      payload = json.loads((BATCH_DIR / "05-batch-of-50-envelope.json").read_text())
      envelope = BatchEnvelope.model_validate(payload)
      assert envelope.batch_id == payload["batch_id"]
      assert len(envelope.items) == len(payload["items"])
  
  
  def test_sse_events_each_round_trip() -> None:
      """Each line of the SSE event sequence is a valid §6.2 envelope augmented
      with batch_id + queue_position. We strip those two fields and assert the
      remainder satisfies DispositionEnvelope (extra='forbid' would block the
      naive shape; we therefore validate via model_construct_then_assert)."""
      lines = (BATCH_DIR / "05-batch-of-50-events.jsonl").read_text().splitlines()
      assert len(lines) == 5
      for line in lines:
          payload = json.loads(line)
          # SSE-augmented fields — strip before round-trip.
          assert isinstance(payload.pop("batch_id"), str)
          assert isinstance(payload.pop("queue_position"), int)
          envelope = DispositionEnvelope.model_validate(payload)
          assert envelope.disposition in {"pass", "fail", "needs_review"}
  ```

- [ ] **Step 2: Run the test (expect ImportError + missing fixture errors).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_canned_envelopes_round_trip.py -x
  ```

  Expected: `FileNotFoundError` on the first fixture path.

- [ ] **Step 3: Create `tests/fixtures/envelopes/single/01-spirits-clean.json` (happy path).**

  ```json
  {
    "evaluation_id": "00000000-0000-4000-8000-000000000001",
    "label_ref": "fixture-01-front",
    "disposition": "pass",
    "disposition_confidence": {"band": "high", "numeric": 0.94},
    "fields": [
      {
        "field_name": "brand_name",
        "extracted_value": "Stone's Throw",
        "expected_value": "Stone's Throw",
        "evidence": {"bbox": [120, 240, 800, 120], "crop_ref": "crop-brand-001", "extraction_confidence": 0.96},
        "rule_findings": [
          {"rule_id": "common.brand.exact_or_normalized", "cfr_citation": "27 CFR §5.64", "disposition": "pass", "reason_code": "BRAND.NAME.MATCH", "plain_language_explanation": "Brand name matches application after normalization."}
        ],
        "ai_suggestion": {"present": false, "task": null, "text": null, "model_disposition": null},
        "field_confidence": {"band": "high", "numeric": 0.94}
      },
      {
        "field_name": "alcohol_content",
        "extracted_value": "40% ALC/VOL",
        "expected_value": "40% ALC/VOL",
        "evidence": {"bbox": [180, 1200, 400, 60], "crop_ref": "crop-abv-001", "extraction_confidence": 0.97},
        "rule_findings": [
          {"rule_id": "spirits.alcohol_content.tolerance", "cfr_citation": "27 CFR §5.65(b)", "disposition": "pass", "reason_code": "ALCOHOL_CONTENT.TOLERANCE.IN_BAND", "plain_language_explanation": "ABV statement within tolerance band."}
        ],
        "ai_suggestion": {"present": false, "task": null, "text": null, "model_disposition": null},
        "field_confidence": {"band": "high", "numeric": 0.97}
      },
      {
        "field_name": "warning",
        "extracted_value": "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL...",
        "expected_value": "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL...",
        "evidence": {"bbox": [80, 1500, 920, 280], "crop_ref": "crop-warning-001", "extraction_confidence": 0.91},
        "rule_findings": [
          {"rule_id": "common.warning.verbatim", "cfr_citation": "27 CFR §16.21", "disposition": "pass", "reason_code": "WARNING.VERBATIM.MATCH", "plain_language_explanation": "Health warning matches §16.21 verbatim."}
        ],
        "ai_suggestion": {"present": false, "task": null, "text": null, "model_disposition": null},
        "field_confidence": {"band": "high", "numeric": 0.91}
      }
    ],
    "audit_trail": {
      "evaluation_id": "00000000-0000-4000-8000-000000000001",
      "rule_set_version": "0.1.0",
      "model_version": "gpt-4o-2024-08-06",
      "prompt_version": "v1",
      "input_hash": "0000000000000000000000000000000000000000000000000000000000000001",
      "output_hash": "0000000000000000000000000000000000000000000000000000000000000002",
      "started_at": "2026-04-01T12:00:00.000Z",
      "completed_at": "2026-04-01T12:00:01.230Z",
      "per_rule_trace": [
        {"rule_id": "common.brand.exact_or_normalized", "disposition": "pass", "evidence_ref": "crop-brand-001"},
        {"rule_id": "spirits.alcohol_content.tolerance", "disposition": "pass", "evidence_ref": "crop-abv-001"},
        {"rule_id": "common.warning.verbatim", "disposition": "pass", "evidence_ref": "crop-warning-001"}
      ],
      "overrides": []
    },
    "metrics": {
      "total_duration_ms": 1230,
      "per_rule_durations_ms": [
        {"rule_id": "common.brand.exact_or_normalized", "duration_ms": 8},
        {"rule_id": "spirits.alcohol_content.tolerance", "duration_ms": 12},
        {"rule_id": "common.warning.verbatim", "duration_ms": 15}
      ],
      "vision_duration_ms": 720,
      "orchestrator_duration_ms": 480
    }
  }
  ```

- [ ] **Step 4: Create `tests/fixtures/envelopes/single/02-bourbon-stones-throw.json` (brand AI-suggestion present).**

  ```json
  {
    "evaluation_id": "00000000-0000-4000-8000-000000000002",
    "label_ref": "fixture-02-front",
    "disposition": "pass",
    "disposition_confidence": {"band": "medium", "numeric": 0.78},
    "fields": [
      {
        "field_name": "brand_name",
        "extracted_value": "STONE'S THROW",
        "expected_value": "Stone's Throw",
        "evidence": {"bbox": [120, 240, 800, 120], "crop_ref": "crop-brand-002", "extraction_confidence": 0.83},
        "rule_findings": [
          {"rule_id": "common.brand.exact_or_normalized", "cfr_citation": "27 CFR §5.64", "disposition": "needs_review", "reason_code": "BRAND.NAME.NEEDS_REVIEW", "plain_language_explanation": "Brand match falls in the borderline band — orchestrator disambiguates."}
        ],
        "ai_suggestion": {"present": true, "task": "brand_borderline", "text": "Apostrophe normalization brings extracted brand 'STONE'S THROW' into agreement with application 'Stone's Throw'. Surface formatting differs from application but identity is consistent.", "model_disposition": "pass"},
        "field_confidence": {"band": "medium", "numeric": 0.78}
      },
      {
        "field_name": "class_type",
        "extracted_value": "STRAIGHT BOURBON WHISKEY",
        "expected_value": "STRAIGHT BOURBON WHISKEY",
        "evidence": {"bbox": [200, 380, 720, 80], "crop_ref": "crop-class-002", "extraction_confidence": 0.95},
        "rule_findings": [
          {"rule_id": "spirits.class_type.soi_match", "cfr_citation": "27 CFR §5 Subpart I", "disposition": "pass", "reason_code": "CLASS_TYPE.SOI.MATCH", "plain_language_explanation": "Class designation matches Standard of Identity for Bourbon."}
        ],
        "ai_suggestion": {"present": false, "task": null, "text": null, "model_disposition": null},
        "field_confidence": {"band": "high", "numeric": 0.95}
      }
    ],
    "audit_trail": {
      "evaluation_id": "00000000-0000-4000-8000-000000000002",
      "rule_set_version": "0.1.0",
      "model_version": "gpt-4o-2024-08-06",
      "prompt_version": "v1",
      "input_hash": "0000000000000000000000000000000000000000000000000000000000000003",
      "output_hash": "0000000000000000000000000000000000000000000000000000000000000004",
      "started_at": "2026-04-01T12:01:00.000Z",
      "completed_at": "2026-04-01T12:01:02.110Z",
      "per_rule_trace": [
        {"rule_id": "common.brand.exact_or_normalized", "disposition": "needs_review", "evidence_ref": "crop-brand-002"},
        {"rule_id": "spirits.class_type.soi_match", "disposition": "pass", "evidence_ref": "crop-class-002"}
      ],
      "overrides": []
    },
    "metrics": {
      "total_duration_ms": 2110,
      "per_rule_durations_ms": [
        {"rule_id": "common.brand.exact_or_normalized", "duration_ms": 12},
        {"rule_id": "spirits.class_type.soi_match", "duration_ms": 9}
      ],
      "vision_duration_ms": 750,
      "orchestrator_duration_ms": 1340
    }
  }
  ```

- [ ] **Step 5: Create `tests/fixtures/envelopes/single/03-warning-title-case.json` (fail).**

  ```json
  {
    "evaluation_id": "00000000-0000-4000-8000-000000000003",
    "label_ref": "fixture-03-front",
    "disposition": "fail",
    "disposition_confidence": {"band": "high", "numeric": 0.92},
    "fields": [
      {
        "field_name": "warning",
        "extracted_value": "Government Warning: (1) According to the Surgeon General...",
        "expected_value": "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL...",
        "evidence": {"bbox": [80, 1500, 920, 280], "crop_ref": "crop-warning-003", "extraction_confidence": 0.92},
        "rule_findings": [
          {"rule_id": "common.warning.heading_style", "cfr_citation": "27 CFR §16.21(a)", "disposition": "fail", "reason_code": "WARNING.STYLE.HEADING_NOT_BOLD_CAPS", "plain_language_explanation": "Health warning heading is not in bold capital letters as required by §16.21(a)."}
        ],
        "ai_suggestion": {"present": false, "task": null, "text": null, "model_disposition": null},
        "field_confidence": {"band": "high", "numeric": 0.92}
      }
    ],
    "audit_trail": {
      "evaluation_id": "00000000-0000-4000-8000-000000000003",
      "rule_set_version": "0.1.0",
      "model_version": "gpt-4o-2024-08-06",
      "prompt_version": "v1",
      "input_hash": "0000000000000000000000000000000000000000000000000000000000000005",
      "output_hash": "0000000000000000000000000000000000000000000000000000000000000006",
      "started_at": "2026-04-01T12:02:00.000Z",
      "completed_at": "2026-04-01T12:02:00.840Z",
      "per_rule_trace": [
        {"rule_id": "common.warning.heading_style", "disposition": "fail", "evidence_ref": "crop-warning-003"}
      ],
      "overrides": []
    },
    "metrics": {
      "total_duration_ms": 840,
      "per_rule_durations_ms": [{"rule_id": "common.warning.heading_style", "duration_ms": 22}],
      "vision_duration_ms": 690,
      "orchestrator_duration_ms": 0
    }
  }
  ```

- [ ] **Step 6: Create `tests/fixtures/envelopes/single/04-low-res-blurry.json` (needs-better-photo).**

  ```json
  {
    "evaluation_id": "00000000-0000-4000-8000-000000000004",
    "label_ref": "fixture-04-front",
    "disposition": "needs_review",
    "disposition_confidence": {"band": "low", "numeric": 0.31},
    "fields": [
      {
        "field_name": "warning",
        "extracted_value": "",
        "expected_value": "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON GENERAL...",
        "evidence": {"bbox": [0, 0, 0, 0], "crop_ref": "crop-warning-004", "extraction_confidence": 0.0},
        "rule_findings": [
          {"rule_id": "common.warning.legibility_gate", "cfr_citation": "27 CFR §16.21", "disposition": "needs_review", "reason_code": "WARNING.LEGIBILITY.LOW_RESOLUTION", "plain_language_explanation": "Image resolution is below the threshold required to verify the health warning. A higher-resolution photo is needed."}
        ],
        "ai_suggestion": {"present": false, "task": null, "text": null, "model_disposition": null},
        "field_confidence": {"band": "low", "numeric": 0.31}
      }
    ],
    "audit_trail": {
      "evaluation_id": "00000000-0000-4000-8000-000000000004",
      "rule_set_version": "0.1.0",
      "model_version": null,
      "prompt_version": null,
      "input_hash": "0000000000000000000000000000000000000000000000000000000000000007",
      "output_hash": "0000000000000000000000000000000000000000000000000000000000000008",
      "started_at": "2026-04-01T12:03:00.000Z",
      "completed_at": "2026-04-01T12:03:00.180Z",
      "per_rule_trace": [
        {"rule_id": "common.warning.legibility_gate", "disposition": "needs_review", "evidence_ref": "crop-warning-004"}
      ],
      "overrides": []
    },
    "metrics": {
      "total_duration_ms": 180,
      "per_rule_durations_ms": [{"rule_id": "common.warning.legibility_gate", "duration_ms": 4}],
      "vision_duration_ms": 175,
      "orchestrator_duration_ms": 0
    }
  }
  ```

- [ ] **Step 7: Create `tests/fixtures/envelopes/single/06-abv-out-of-tolerance.json` (fail).**

  ```json
  {
    "evaluation_id": "00000000-0000-4000-8000-000000000006",
    "label_ref": "fixture-06-front",
    "disposition": "fail",
    "disposition_confidence": {"band": "high", "numeric": 0.96},
    "fields": [
      {
        "field_name": "alcohol_content",
        "extracted_value": "45% ALC/VOL",
        "expected_value": "40% ALC/VOL",
        "evidence": {"bbox": [180, 1200, 400, 60], "crop_ref": "crop-abv-006", "extraction_confidence": 0.97},
        "rule_findings": [
          {"rule_id": "spirits.alcohol_content.tolerance", "cfr_citation": "27 CFR §5.65(b)", "disposition": "fail", "reason_code": "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND", "plain_language_explanation": "Label states 45% ALC/VOL, application is 40% ALC/VOL. Difference (5.0%) exceeds the ±0.3% tolerance band."}
        ],
        "ai_suggestion": {"present": false, "task": null, "text": null, "model_disposition": null},
        "field_confidence": {"band": "high", "numeric": 0.97}
      }
    ],
    "audit_trail": {
      "evaluation_id": "00000000-0000-4000-8000-000000000006",
      "rule_set_version": "0.1.0",
      "model_version": "gpt-4o-2024-08-06",
      "prompt_version": "v1",
      "input_hash": "0000000000000000000000000000000000000000000000000000000000000009",
      "output_hash": "000000000000000000000000000000000000000000000000000000000000000a",
      "started_at": "2026-04-01T12:04:00.000Z",
      "completed_at": "2026-04-01T12:04:00.890Z",
      "per_rule_trace": [
        {"rule_id": "spirits.alcohol_content.tolerance", "disposition": "fail", "evidence_ref": "crop-abv-006"}
      ],
      "overrides": []
    },
    "metrics": {
      "total_duration_ms": 890,
      "per_rule_durations_ms": [{"rule_id": "spirits.alcohol_content.tolerance", "duration_ms": 18}],
      "vision_duration_ms": 740,
      "orchestrator_duration_ms": 0
    }
  }
  ```

- [ ] **Step 8: Create `tests/fixtures/envelopes/single/07-borderline-confidence.json` (needs_review with AI suggestion).**

  ```json
  {
    "evaluation_id": "00000000-0000-4000-8000-000000000007",
    "label_ref": "fixture-07-front",
    "disposition": "needs_review",
    "disposition_confidence": {"band": "low", "numeric": 0.49},
    "fields": [
      {
        "field_name": "brand_name",
        "extracted_value": "STONES THROW",
        "expected_value": "Stone's Throw",
        "evidence": {"bbox": [120, 240, 800, 120], "crop_ref": "crop-brand-007", "extraction_confidence": 0.49},
        "rule_findings": [
          {"rule_id": "common.brand.exact_or_normalized", "cfr_citation": "27 CFR §5.64", "disposition": "needs_review", "reason_code": "BRAND.NAME.NEEDS_REVIEW", "plain_language_explanation": "Borderline match — apostrophe absent in extracted text; orchestrator disambiguation requested."}
        ],
        "ai_suggestion": {"present": true, "task": "brand_borderline", "text": "Confidence floor applied: extraction band low but normalized identity matches. Recommending reviewer confirmation rather than auto-pass.", "model_disposition": "needs_review"},
        "field_confidence": {"band": "low", "numeric": 0.49}
      }
    ],
    "audit_trail": {
      "evaluation_id": "00000000-0000-4000-8000-000000000007",
      "rule_set_version": "0.1.0",
      "model_version": "gpt-4o-2024-08-06",
      "prompt_version": "v1",
      "input_hash": "000000000000000000000000000000000000000000000000000000000000000b",
      "output_hash": "000000000000000000000000000000000000000000000000000000000000000c",
      "started_at": "2026-04-01T12:05:00.000Z",
      "completed_at": "2026-04-01T12:05:01.760Z",
      "per_rule_trace": [
        {"rule_id": "common.brand.exact_or_normalized", "disposition": "needs_review", "evidence_ref": "crop-brand-007"}
      ],
      "overrides": []
    },
    "metrics": {
      "total_duration_ms": 1760,
      "per_rule_durations_ms": [{"rule_id": "common.brand.exact_or_normalized", "duration_ms": 14}],
      "vision_duration_ms": 720,
      "orchestrator_duration_ms": 1020
    }
  }
  ```

- [ ] **Step 9: Create `tests/fixtures/envelopes/batch/05-batch-of-50-envelope.json` (PRD §6.3 batch envelope).**

  ```json
  {
    "batch_id": "00000000-0000-4000-8000-00000000b005",
    "agent_id": "session-batch-005",
    "submitted_at": "2026-04-01T12:10:00.000Z",
    "items": [
      {"label_ref": "batch-005-item-01", "application_ref": "app-batch-005-01"},
      {"label_ref": "batch-005-item-02", "application_ref": "app-batch-005-02"},
      {"label_ref": "batch-005-item-03", "application_ref": "app-batch-005-03"},
      {"label_ref": "batch-005-item-04", "application_ref": "app-batch-005-04"},
      {"label_ref": "batch-005-item-05", "application_ref": "app-batch-005-05"}
    ]
  }
  ```

- [ ] **Step 10: Create `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl` (5 SSE events; one envelope per line).**

  Each line is a complete `DispositionEnvelope` augmented with `batch_id` + `queue_position`. The plan deliberately keeps these short (1 field each) since the SSE consumer test only exercises the surrounding push/dispatch mechanics; the visual richness is exercised by the single fixtures.

  ```jsonl
  {"batch_id":"00000000-0000-4000-8000-00000000b005","queue_position":1,"evaluation_id":"00000000-0000-4000-8000-000005000001","label_ref":"batch-005-item-01","disposition":"pass","disposition_confidence":{"band":"high","numeric":0.93},"fields":[{"field_name":"brand_name","extracted_value":"Item 01","expected_value":"Item 01","evidence":{"bbox":[0,0,100,40],"crop_ref":"crop-005-01","extraction_confidence":0.93},"rule_findings":[{"rule_id":"common.brand.exact_or_normalized","cfr_citation":"27 CFR §5.64","disposition":"pass","reason_code":"BRAND.NAME.MATCH","plain_language_explanation":"OK."}],"ai_suggestion":{"present":false,"task":null,"text":null,"model_disposition":null},"field_confidence":{"band":"high","numeric":0.93}}],"audit_trail":{"evaluation_id":"00000000-0000-4000-8000-000005000001","rule_set_version":"0.1.0","model_version":null,"prompt_version":null,"input_hash":"0000000000000000000000000000000000000000000000000000000000000101","output_hash":"0000000000000000000000000000000000000000000000000000000000000102","started_at":"2026-04-01T12:10:01.000Z","completed_at":"2026-04-01T12:10:02.100Z","per_rule_trace":[{"rule_id":"common.brand.exact_or_normalized","disposition":"pass","evidence_ref":"crop-005-01"}],"overrides":[]},"metrics":{"total_duration_ms":1100,"per_rule_durations_ms":[{"rule_id":"common.brand.exact_or_normalized","duration_ms":10}],"vision_duration_ms":700,"orchestrator_duration_ms":0}}
  {"batch_id":"00000000-0000-4000-8000-00000000b005","queue_position":2,"evaluation_id":"00000000-0000-4000-8000-000005000002","label_ref":"batch-005-item-02","disposition":"fail","disposition_confidence":{"band":"high","numeric":0.95},"fields":[{"field_name":"alcohol_content","extracted_value":"50% ALC/VOL","expected_value":"40% ALC/VOL","evidence":{"bbox":[0,0,100,40],"crop_ref":"crop-005-02","extraction_confidence":0.95},"rule_findings":[{"rule_id":"spirits.alcohol_content.tolerance","cfr_citation":"27 CFR §5.65(b)","disposition":"fail","reason_code":"ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND","plain_language_explanation":"Out of band."}],"ai_suggestion":{"present":false,"task":null,"text":null,"model_disposition":null},"field_confidence":{"band":"high","numeric":0.95}}],"audit_trail":{"evaluation_id":"00000000-0000-4000-8000-000005000002","rule_set_version":"0.1.0","model_version":null,"prompt_version":null,"input_hash":"0000000000000000000000000000000000000000000000000000000000000201","output_hash":"0000000000000000000000000000000000000000000000000000000000000202","started_at":"2026-04-01T12:10:02.000Z","completed_at":"2026-04-01T12:10:03.300Z","per_rule_trace":[{"rule_id":"spirits.alcohol_content.tolerance","disposition":"fail","evidence_ref":"crop-005-02"}],"overrides":[]},"metrics":{"total_duration_ms":1300,"per_rule_durations_ms":[{"rule_id":"spirits.alcohol_content.tolerance","duration_ms":15}],"vision_duration_ms":730,"orchestrator_duration_ms":0}}
  {"batch_id":"00000000-0000-4000-8000-00000000b005","queue_position":3,"evaluation_id":"00000000-0000-4000-8000-000005000003","label_ref":"batch-005-item-03","disposition":"needs_review","disposition_confidence":{"band":"medium","numeric":0.62},"fields":[{"field_name":"brand_name","extracted_value":"Item 03","expected_value":"Item 03","evidence":{"bbox":[0,0,100,40],"crop_ref":"crop-005-03","extraction_confidence":0.62},"rule_findings":[{"rule_id":"common.brand.exact_or_normalized","cfr_citation":"27 CFR §5.64","disposition":"needs_review","reason_code":"BRAND.NAME.NEEDS_REVIEW","plain_language_explanation":"Borderline."}],"ai_suggestion":{"present":true,"task":"brand_borderline","text":"Borderline match.","model_disposition":"needs_review"},"field_confidence":{"band":"medium","numeric":0.62}}],"audit_trail":{"evaluation_id":"00000000-0000-4000-8000-000005000003","rule_set_version":"0.1.0","model_version":"gpt-4o-2024-08-06","prompt_version":"v1","input_hash":"0000000000000000000000000000000000000000000000000000000000000301","output_hash":"0000000000000000000000000000000000000000000000000000000000000302","started_at":"2026-04-01T12:10:03.000Z","completed_at":"2026-04-01T12:10:04.450Z","per_rule_trace":[{"rule_id":"common.brand.exact_or_normalized","disposition":"needs_review","evidence_ref":"crop-005-03"}],"overrides":[]},"metrics":{"total_duration_ms":1450,"per_rule_durations_ms":[{"rule_id":"common.brand.exact_or_normalized","duration_ms":11}],"vision_duration_ms":680,"orchestrator_duration_ms":760}}
  {"batch_id":"00000000-0000-4000-8000-00000000b005","queue_position":4,"evaluation_id":"00000000-0000-4000-8000-000005000004","label_ref":"batch-005-item-04","disposition":"pass","disposition_confidence":{"band":"high","numeric":0.91},"fields":[{"field_name":"brand_name","extracted_value":"Item 04","expected_value":"Item 04","evidence":{"bbox":[0,0,100,40],"crop_ref":"crop-005-04","extraction_confidence":0.91},"rule_findings":[{"rule_id":"common.brand.exact_or_normalized","cfr_citation":"27 CFR §5.64","disposition":"pass","reason_code":"BRAND.NAME.MATCH","plain_language_explanation":"OK."}],"ai_suggestion":{"present":false,"task":null,"text":null,"model_disposition":null},"field_confidence":{"band":"high","numeric":0.91}}],"audit_trail":{"evaluation_id":"00000000-0000-4000-8000-000005000004","rule_set_version":"0.1.0","model_version":null,"prompt_version":null,"input_hash":"0000000000000000000000000000000000000000000000000000000000000401","output_hash":"0000000000000000000000000000000000000000000000000000000000000402","started_at":"2026-04-01T12:10:04.000Z","completed_at":"2026-04-01T12:10:05.150Z","per_rule_trace":[{"rule_id":"common.brand.exact_or_normalized","disposition":"pass","evidence_ref":"crop-005-04"}],"overrides":[]},"metrics":{"total_duration_ms":1150,"per_rule_durations_ms":[{"rule_id":"common.brand.exact_or_normalized","duration_ms":9}],"vision_duration_ms":710,"orchestrator_duration_ms":0}}
  {"batch_id":"00000000-0000-4000-8000-00000000b005","queue_position":5,"evaluation_id":"00000000-0000-4000-8000-000005000005","label_ref":"batch-005-item-05","disposition":"needs_review","disposition_confidence":{"band":"low","numeric":0.34},"fields":[{"field_name":"warning","extracted_value":"","expected_value":"GOVERNMENT WARNING:...","evidence":{"bbox":[0,0,0,0],"crop_ref":"crop-005-05","extraction_confidence":0.0},"rule_findings":[{"rule_id":"common.warning.legibility_gate","cfr_citation":"27 CFR §16.21","disposition":"needs_review","reason_code":"WARNING.LEGIBILITY.LOW_RESOLUTION","plain_language_explanation":"Low resolution."}],"ai_suggestion":{"present":false,"task":null,"text":null,"model_disposition":null},"field_confidence":{"band":"low","numeric":0.34}}],"audit_trail":{"evaluation_id":"00000000-0000-4000-8000-000005000005","rule_set_version":"0.1.0","model_version":null,"prompt_version":null,"input_hash":"0000000000000000000000000000000000000000000000000000000000000501","output_hash":"0000000000000000000000000000000000000000000000000000000000000502","started_at":"2026-04-01T12:10:05.000Z","completed_at":"2026-04-01T12:10:05.220Z","per_rule_trace":[{"rule_id":"common.warning.legibility_gate","disposition":"needs_review","evidence_ref":"crop-005-05"}],"overrides":[]},"metrics":{"total_duration_ms":220,"per_rule_durations_ms":[{"rule_id":"common.warning.legibility_gate","duration_ms":5}],"vision_duration_ms":215,"orchestrator_duration_ms":0}}
  ```

- [ ] **Step 11: Run the round-trip test (Green).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_canned_envelopes_round_trip.py -v
  ```

  Expected: 8 passed.

- [ ] **Step 12: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add tests/fixtures/envelopes/ tests/test_canned_envelopes_round_trip.py
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): canned envelope fixtures + Pydantic round-trip"
  ```

---

### Task T4 — Jinja shells + UI router + main.py wiring

**Wave:** 1
**Depends on:** —
**Owns (creates):** `app/ui/templates/base.html`, `app/ui/templates/single.html`, `app/ui/templates/batch.html`, `app/api/ui.py`, `tests/test_ui_routes.py`.
**Owns (modifies):** `app/main.py` (additive — register `ui.router` + `StaticFiles` mount).

The Jinja shells are server-rendered shells with no engine wiring; they exist to (a) declare the `<div id="root">` mount point with the right `data-mode`, (b) serve a `<noscript>` fallback per L1 §2.6, (c) load the built island JS via `<script type="module" src="/static/island/{single|batch}.js">`. The router has zero engine imports.

This task includes a small `main.py` change. The change is **strictly additive** (one import block + two registration calls); the existing `/healthz` route remains, asserted by Step 1's test.

- [ ] **Step 1: Write the failing test (Red) — `tests/test_ui_routes.py`.**

  ```python
  """T4: page-shell GET routes and the StaticFiles mount.
  
  These routes serve Jinja2 shells only; engine logic lives in E5/E6 routes.
  The test guards: (a) /healthz is unaffected by the additive UI registration,
  (b) GET / returns the single-mode shell with data-mode="single",
  (c) GET /batch/{batch_id} returns the batch shell with data-mode="batch" and
      data-batch-id="{batch_id}",
  (d) /static/island/.gitkeep is served (proves the StaticFiles mount works).
  """
  from __future__ import annotations
  
  import pytest
  from fastapi.testclient import TestClient
  
  from app.main import create_app
  
  
  @pytest.fixture
  def client() -> TestClient:
      return TestClient(create_app())
  
  
  def test_healthz_still_passes(client: TestClient) -> None:
      response = client.get("/healthz")
      assert response.status_code == 200
  
  
  def test_single_page_shell(client: TestClient) -> None:
      response = client.get("/")
      assert response.status_code == 200
      assert "text/html" in response.headers["content-type"]
      assert 'id="root"' in response.text
      assert 'data-mode="single"' in response.text
      assert "/static/island/single.js" in response.text
      # noscript fallback per L1 §2.6.
      assert "<noscript>" in response.text
      assert "POST /labels" in response.text
  
  
  def test_batch_page_shell(client: TestClient) -> None:
      response = client.get("/batch/abc-123")
      assert response.status_code == 200
      assert 'data-mode="batch"' in response.text
      assert 'data-batch-id="abc-123"' in response.text
      assert "/static/island/batch.js" in response.text
  
  
  def test_static_island_mount(client: TestClient) -> None:
      """The StaticFiles mount serves files under app/ui/static/. The .gitkeep
      placeholder proves the mount works before the real bundle lands (T34)."""
      response = client.get("/static/island/.gitkeep")
      assert response.status_code == 200
  
  
  def test_uswds_skip_link_present(client: TestClient) -> None:
      """NFR-A11Y-002 keyboard-operable end-to-end: the 'Skip to main content'
      link must be the first focusable element on every page."""
      response = client.get("/")
      assert 'class="skip-link"' in response.text
      assert "Skip to main content" in response.text
  ```

- [ ] **Step 2: Run the test (Red).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_ui_routes.py -x
  ```

  Expected: ImportError on `app.api.ui` or 404 on `/`. Either is fine.

- [ ] **Step 3: Create `app/ui/templates/base.html`.**

  ```html
  {# app/ui/templates/base.html — global page shell.
     Owners: E7 (L1 §2.1).
     ARIA semantics — skip-link to #main, footer landmark. USWDS tokens preloaded
     from /static/island/single.css (or batch.css; Jinja interpolates per page). #}
  <!doctype html>
  <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <meta name="color-scheme" content="light only" />
      <title>{% block title %}TTB Label Verification{% endblock %}</title>
      <link rel="stylesheet" href="/static/island/{% block bundle_name %}single{% endblock %}.css" />
    </head>
    <body>
      <a class="skip-link" href="#main">Skip to main content</a>
      <header role="banner">
        <h1>TTB Label Verification</h1>
        <p>Reviewer console — prototype</p>
      </header>
      <main id="main" role="main">
        {% block content %}{% endblock %}
      </main>
      <noscript>
        <p><strong>JavaScript is required for the reviewer UI.</strong> For
        programmatic submissions, use the API at <code>POST /labels</code>.
        See the project README for details.</p>
      </noscript>
      <footer role="contentinfo">
        <p>TTB AI-Powered Alcohol Label Verification — prototype.
        <a href="https://www.ttb.gov/labeling">TTB labeling regulations</a>.</p>
      </footer>
      <script type="module" src="/static/island/{% block bundle_name_script %}single{% endblock %}.js"></script>
    </body>
  </html>
  ```

- [ ] **Step 4: Create `app/ui/templates/single.html`.**

  ```html
  {% extends "base.html" %}
  {% block title %}Review label — TTB Label Verification{% endblock %}
  {% block bundle_name %}single{% endblock %}
  {% block bundle_name_script %}single{% endblock %}
  {% block content %}
    <div id="root" data-mode="single">
      <p>Loading review surface…</p>
    </div>
    {% if envelope_json %}
    <script id="envelope" type="application/json">{{ envelope_json | safe }}</script>
    {% endif %}
  {% endblock %}
  ```

- [ ] **Step 5: Create `app/ui/templates/batch.html`.**

  ```html
  {% extends "base.html" %}
  {% block title %}Batch review — TTB Label Verification{% endblock %}
  {% block bundle_name %}batch{% endblock %}
  {% block bundle_name_script %}batch{% endblock %}
  {% block content %}
    <div id="root" data-mode="batch" data-batch-id="{{ batch_id }}">
      <p>Connecting to batch stream…</p>
    </div>
  {% endblock %}
  ```

- [ ] **Step 6: Create `app/api/ui.py`.**

  ```python
  """Page-shell GET routes for the React island.
  
  This module is template-rendering only. It does NOT import from
  ``app.services``, ``app.orchestrator``, ``app.vision``, or ``app.rules``.
  Engine logic lives in the JSON API routes (``app.api.labels``,
  ``app.api.batches``, ``app.api.overrides``), which are owned by E5/E6.
  """
  from __future__ import annotations
  
  from pathlib import Path
  
  from fastapi import APIRouter, Request
  from fastapi.responses import HTMLResponse
  from fastapi.templating import Jinja2Templates
  
  
  _TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "ui" / "templates"
  templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
  
  router = APIRouter(tags=["ui"])
  
  
  @router.get("/", response_class=HTMLResponse)
  async def single_page_shell(request: Request) -> HTMLResponse:
      """Render the single-label review shell. The React island handles all
      reviewer interaction client-side; the shell is a static document."""
      return templates.TemplateResponse(
          request=request,
          name="single.html",
          context={"envelope_json": None},
      )
  
  
  @router.get("/batch/{batch_id}", response_class=HTMLResponse)
  async def batch_page_shell(request: Request, batch_id: str) -> HTMLResponse:
      """Render the batch review shell for a given batch_id. The React island
      subscribes via SSE to ``/batches/{batch_id}/stream`` (E6 endpoint)."""
      return templates.TemplateResponse(
          request=request,
          name="batch.html",
          context={"batch_id": batch_id},
      )
  ```

- [ ] **Step 7: Modify `app/main.py` (additive only — registers `ui.router` + StaticFiles mount).**

  Insert after the `from app.api.healthz import router as healthz_router` line:

  ```python
  from app.api.ui import router as ui_router
  from fastapi.staticfiles import StaticFiles
  ```

  Inside `create_app(...)`, after `application.include_router(healthz_router)`:

  ```python
      application.include_router(ui_router)
      _static_dir = Path(__file__).resolve().parent / "ui" / "static"
      application.mount(
          "/static",
          StaticFiles(directory=str(_static_dir)),
          name="static",
      )
  ```

  Also add `from pathlib import Path` to the top imports if not already present.

  Final `app/main.py` should look like:

  ```python
  """FastAPI application factory. Source: ARCH §14.3.
  
  Boot sequence (E1 + E7 additions):
  1. Read ``Settings``.
  2. Configure logging (JSON-line stdout + redaction filter).
  3. Construct the FastAPI app.
  4. Register routers: /healthz (E1), UI page shells (E7).
  5. Mount static files at /static (E7).
  
  Later epochs add: rule-loader startup, vision/orchestrator wiring, label/batch/
  override/eval routes, SSE.
  """
  from __future__ import annotations
  
  import logging
  from collections.abc import AsyncIterator
  from contextlib import asynccontextmanager
  from pathlib import Path
  
  from fastapi import FastAPI
  from fastapi.staticfiles import StaticFiles
  
  from app.api.healthz import router as healthz_router
  from app.api.ui import router as ui_router
  from app.config import Settings
  from app.logging import configure_logging
  
  
  def create_app(settings: Settings | None = None) -> FastAPI:
      settings = settings or Settings()
      configure_logging(settings)
  
      @asynccontextmanager
      async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
          logging.getLogger("app.main").info(
              "app_startup",
              extra={
                  "reason_code": "ENGINE.OK.NONE",
                  "rule_set_version": "0.0.0",
                  "model_version": settings.llm_model_snapshot,
                  "prompt_version": settings.prompt_version,
              },
          )
          yield
  
      application = FastAPI(
          title="TTB Label Verification (prototype)",
          version=settings.app_version,
          lifespan=_lifespan,
      )
      application.include_router(healthz_router)
      application.include_router(ui_router)
      _static_dir = Path(__file__).resolve().parent / "ui" / "static"
      application.mount(
          "/static",
          StaticFiles(directory=str(_static_dir)),
          name="static",
      )
  
      return application
  
  
  app: FastAPI = create_app()
  ```

- [ ] **Step 8: Run the test (Green).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_ui_routes.py -v
  ```

  Expected: 5 passed.

- [ ] **Step 9: Run the full suite to verify no regression on E1/E2/E3/E4 tests (375 baseline + 8 new fixture round-trips from T3 + 5 new UI route tests = 388).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest -x -q
  ```

  Expected: 388 passed.

- [ ] **Step 10: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add app/ui/templates/base.html app/ui/templates/single.html app/ui/templates/batch.html app/api/ui.py app/main.py tests/test_ui_routes.py
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): Jinja shells + UI router + StaticFiles mount"
  ```

---

### Task T5 — TypeScript envelope types + drift test

**Wave:** 2
**Depends on:** T1
**Owns (creates):** `frontend/src/types/envelopes.ts`, `frontend/src/types/sse.ts`, `tests/test_typescript_envelope_drift.py`.

The TypeScript types are hand-mirrored from `app/schemas/wire/disposition.py` and `app/schemas/wire/batch.py`. The drift test greps the Pydantic schema field names and asserts each one appears in the TS file. This is a CI canary; it does NOT prevent every drift but it catches field renames.

- [ ] **Step 1: Write the drift test (Red) — `tests/test_typescript_envelope_drift.py`.**

  ```python
  """T5: hand-mirrored TS envelope types track Pydantic schema field names.
  
  This is a fast structural canary, not a full type-isomorphism check. If a
  field is renamed in app/schemas/wire/*.py, this test surfaces the drift; the
  fix is a one-line edit in frontend/src/types/envelopes.ts.
  """
  from __future__ import annotations
  
  import re
  from pathlib import Path
  
  ROOT = Path(__file__).resolve().parent.parent
  TS_PATH = ROOT / "frontend" / "src" / "types" / "envelopes.ts"
  PYDANTIC_FILES = [
      ROOT / "app" / "schemas" / "wire" / "disposition.py",
      ROOT / "app" / "schemas" / "wire" / "batch.py",
      ROOT / "app" / "schemas" / "audit.py",
      ROOT / "app" / "schemas" / "metrics.py",
  ]
  
  # Fields whose names the TS file is required to contain. These are field
  # IDENTIFIERS as written in Pydantic source (e.g. ``label_ref:``); the regex
  # captures lines like ``    label_ref: str`` or ``    label_ref: Literal[...]``.
  _FIELD_RE = re.compile(r"^\s{4}([a-z_][a-z0-9_]*):\s", re.MULTILINE)
  
  
  def _pydantic_fields() -> set[str]:
      out: set[str] = set()
      for p in PYDANTIC_FILES:
          source = p.read_text()
          out |= set(_FIELD_RE.findall(source))
      return out
  
  
  def test_typescript_envelopes_file_exists() -> None:
      assert TS_PATH.exists(), f"missing {TS_PATH}"
  
  
  def test_typescript_envelopes_mirror_pydantic_fields() -> None:
      ts = TS_PATH.read_text()
      missing: list[str] = []
      for field in sorted(_pydantic_fields()):
          # Skip fields with names that conflict with TS reserved-word patterns
          # or are intentionally renamed (none today, but keep the hook).
          if field in {}:
              continue
          # The field name must appear at least once in the TS file (as a
          # property declaration or a comment hook).
          if field not in ts:
              missing.append(field)
      assert not missing, f"TypeScript envelope types missing fields: {missing}"
  ```

- [ ] **Step 2: Run the test (Red).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_typescript_envelope_drift.py -x
  ```

  Expected: `AssertionError: missing /.../envelopes.ts`.

- [ ] **Step 3: Create `frontend/src/types/envelopes.ts`.**

  ```ts
  /** PRD §6.2 / §6.3 wire types — hand-mirrored from app/schemas/wire/.
   *  Drift canary: tests/test_typescript_envelope_drift.py. */
  
  export type Band = "high" | "medium" | "low";
  export type Disposition = "pass" | "fail" | "needs_review";
  export type RuleDisposition = "pass" | "fail" | "needs_review";
  
  export interface ConfidenceBand {
    band: Band;
    numeric: number;
  }
  
  export interface FieldEvidenceWire {
    bbox: [number, number, number, number];
    crop_ref: string;
    extraction_confidence: number;
  }
  
  export interface RuleFindingWire {
    rule_id: string;
    cfr_citation: string;
    disposition: RuleDisposition;
    reason_code: string;
    plain_language_explanation: string;
  }
  
  export type AISuggestionTask =
    | "brand_borderline"
    | "reasoning_enrichment"
    | "ocr_reconciliation";
  
  export type AISuggestion =
    | { present: false; task: null; text: null; model_disposition: null }
    | {
        present: true;
        task: AISuggestionTask;
        text: string;
        model_disposition: "pass" | "needs_review" | null;
      };
  
  export interface AISuggestionWire {
    present: boolean;
    task: AISuggestionTask | null;
    text: string | null;
    model_disposition: "pass" | "needs_review" | null;
  }
  
  export type FieldName =
    | "brand_name"
    | "class_type"
    | "alcohol_content"
    | "net_contents"
    | "warning"
    | "name_address"
    | "country_of_origin";
  
  export interface FieldFindingWire {
    field_name: FieldName;
    extracted_value: string;
    expected_value: string;
    evidence: FieldEvidenceWire;
    rule_findings: RuleFindingWire[];
    ai_suggestion: AISuggestionWire;
    field_confidence: ConfidenceBand;
  }
  
  export interface PerRuleTraceEntry {
    rule_id: string;
    disposition: "pass" | "fail" | "needs_review" | "not_applicable";
    evidence_ref: string;
  }
  
  export interface OverrideEntry {
    field_name: string;
    original_disposition: "pass" | "fail" | "needs_review";
    applied_disposition: "pass" | "fail" | "needs_review";
    reason_code: string;
    justification_text: string | null;
    reviewer_id: string;
    timestamp: string;
  }
  
  export interface AuditRecord {
    evaluation_id: string;
    rule_set_version: string;
    model_version: string | null;
    prompt_version: string | null;
    input_hash: string;
    output_hash: string;
    started_at: string;
    completed_at: string;
    per_rule_trace: PerRuleTraceEntry[];
    overrides: OverrideEntry[];
  }
  
  export interface PerRuleDurationEntry {
    rule_id: string;
    duration_ms: number;
  }
  
  export interface Metrics {
    total_duration_ms: number;
    per_rule_durations_ms: PerRuleDurationEntry[];
    vision_duration_ms: number;
    orchestrator_duration_ms: number;
  }
  
  export interface DispositionEnvelope {
    evaluation_id: string;
    label_ref: string;
    disposition: Disposition;
    disposition_confidence: ConfidenceBand;
    fields: FieldFindingWire[];
    audit_trail: AuditRecord;
    metrics: Metrics;
  }
  
  export interface BatchItemRef {
    label_ref: string;
    application_ref: string;
  }
  
  export interface BatchEnvelope {
    batch_id: string;
    agent_id: string;
    submitted_at: string;
    items: BatchItemRef[];
  }
  ```

- [ ] **Step 4: Create `frontend/src/types/sse.ts`.**

  ```ts
  import type { DispositionEnvelope } from "./envelopes";
  
  /** Per-label SSE event: a §6.2 envelope augmented with batch_id +
   *  queue_position. The augmentation lives at the SSE layer; the underlying
   *  envelope shape is unmodified. */
  export interface BatchSSEEvent extends DispositionEnvelope {
    batch_id: string;
    queue_position: number;
  }
  ```

- [ ] **Step 5: Run the drift test (Green).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_typescript_envelope_drift.py -v
  ```

  Expected: 2 passed.

- [ ] **Step 6: Run TS type-check on the frontend (sanity).**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm exec tsc -b
  ```

  Expected: no output (clean compile).

- [ ] **Step 7: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add frontend/src/types/envelopes.ts frontend/src/types/sse.ts tests/test_typescript_envelope_drift.py
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): TS envelope types + Pydantic drift canary"
  ```

---

### Task T6 — Vitest setup smoke (sanity check on test infra)

**Wave:** 2
**Depends on:** T1
**Owns (creates):** `frontend/src/test/jest-dom.test.tsx` (a tiny smoke that confirms the vitest-axe and jest-dom matchers loaded — `expect(el).toBeInTheDocument()` and `expect(html).toHaveNoViolations()`).

This task is small but explicit: it surfaces any setup-file misconfiguration BEFORE we start writing 17 components that depend on those matchers.

- [ ] **Step 1: Write the smoke test (Red — there's nothing wrong yet, but the assertion exercises the extension).**

  Create `frontend/src/test/jest-dom.test.tsx`:

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "./render";
  
  describe("vitest infra", () => {
    it("registers @testing-library/jest-dom matchers", () => {
      const { getByTestId } = renderWithProviders(
        <button type="button" data-testid="b" aria-label="ok">click</button>,
      );
      const el = getByTestId("b");
      expect(el).toBeInTheDocument();
      expect(el).toHaveAccessibleName("ok");
    });
  
    it("registers vitest-axe and runs against a clean tree", async () => {
      const { container } = renderWithProviders(
        <main>
          <h1>Hello</h1>
          <p>World</p>
        </main>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Run it (Green expected — T1 already wired the setup).**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/test/jest-dom.test.tsx
  ```

  Expected: 2 passed.

  If the run fails with `expect(...).toBeInTheDocument is not a function`, T1's `setup.ts` did not load — check `vitest.config.ts` `test.setupFiles`.

- [ ] **Step 3: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add frontend/src/test/jest-dom.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): jest-dom + vitest-axe matcher smoke"
  ```

---

### Task T7 — Playwright dependency add + uvicorn live-server fixture

**Wave:** 2
**Depends on:** T1, T4
**Owns (modifies):** `pyproject.toml`, `tests/conftest.py`.
**Owns (creates):** `tests/test_playwright_harness_smoke.py`.

Add `playwright` and `pytest-playwright` to dev deps; add a session-scoped `live_server` fixture that starts uvicorn against `app.main:app` on a random port and tears it down at session end. Subsequent Playwright tests (T29–T32) consume this fixture.

- [ ] **Step 1: Append `[dependency-groups.dev]` entries in `pyproject.toml`.**

  Edit the existing `dev` group (currently lists pytest, pytest-asyncio, taskipy, respx). Add two lines:

  ```toml
  [dependency-groups]
  dev = [
      "pytest >= 8.3",
      "pytest-asyncio >= 0.24",
      "taskipy >= 1.13",
      "respx >= 0.21",
      "playwright >= 1.48",
      "pytest-playwright >= 0.6",
  ]
  ```

- [ ] **Step 2: Run `uv sync`.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv sync --python 3.12 --group dev
  ```

  Expected: `playwright` and `pytest-playwright` installed.

- [ ] **Step 3: Install Playwright Chromium browser binary.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 playwright install chromium
  ```

  Expected: Chromium browser downloaded to `~/.cache/ms-playwright/`.

- [ ] **Step 4: Write the smoke test (Red) — `tests/test_playwright_harness_smoke.py`.**

  ```python
  """T7: Playwright harness smoke — fixture starts uvicorn and serves /."""
  from __future__ import annotations
  
  import pytest
  from playwright.sync_api import Page
  
  
  @pytest.mark.usefixtures("live_server")
  def test_playwright_loads_single_shell(page: Page, live_server_url: str) -> None:
      page.goto(f"{live_server_url}/")
      # The Jinja shell renders before the island JS runs (404 on bundle is OK).
      content = page.content()
      assert 'id="root"' in content
      assert 'data-mode="single"' in content
  
  
  @pytest.mark.usefixtures("live_server")
  def test_playwright_loads_batch_shell(page: Page, live_server_url: str) -> None:
      page.goto(f"{live_server_url}/batch/abc-123")
      content = page.content()
      assert 'data-mode="batch"' in content
      assert 'data-batch-id="abc-123"' in content
  ```

- [ ] **Step 5: Add the `live_server` fixture to `tests/conftest.py`. The fixture is session-scoped to keep startup cost out of every test.**

  Append (or create with) the following block inside `tests/conftest.py`:

  ```python
  """Shared pytest fixtures."""
  from __future__ import annotations
  
  import shutil
  import socket
  import subprocess
  import threading
  import time
  from collections.abc import Iterator
  from pathlib import Path
  
  import pytest
  import uvicorn
  
  from app.main import create_app
  
  
  def _free_port() -> int:
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
          s.bind(("127.0.0.1", 0))
          return s.getsockname()[1]
  
  
  class _LiveServer:
      def __init__(self) -> None:
          self.port = _free_port()
          self.url = f"http://127.0.0.1:{self.port}"
          self._server: uvicorn.Server | None = None
          self._thread: threading.Thread | None = None
  
      def start(self) -> None:
          config = uvicorn.Config(
              app=create_app(),
              host="127.0.0.1",
              port=self.port,
              log_level="warning",
              loop="asyncio",
          )
          self._server = uvicorn.Server(config)
          self._thread = threading.Thread(
              target=self._server.run, daemon=True
          )
          self._thread.start()
          # Poll until the server accepts connections (≤2 s).
          deadline = time.time() + 2.0
          while time.time() < deadline:
              with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                  if s.connect_ex(("127.0.0.1", self.port)) == 0:
                      return
              time.sleep(0.05)
          raise RuntimeError(
              f"uvicorn did not bind to {self.port} within 2 s"
          )
  
      def stop(self) -> None:
          if self._server is not None:
              self._server.should_exit = True
          if self._thread is not None:
              self._thread.join(timeout=2.0)
  
  
  @pytest.fixture(scope="session")
  def live_server() -> Iterator[_LiveServer]:
      server = _LiveServer()
      server.start()
      yield server
      server.stop()
  
  
  @pytest.fixture(scope="session")
  def live_server_url(live_server: _LiveServer) -> str:
      return live_server.url
  
  
  @pytest.fixture(scope="session")
  def pnpm_built_island() -> Path:
      """Build the React island once per session; return the output dir.
  
      Consumed by T29/T30/T31/T32 (Wave 7). Lives in T7 (Wave 2) instead of
      Wave 7 to keep tests/conftest.py owned by a single task — otherwise
      multiple W7 tasks would race on the same file.
      """
      root = Path(__file__).resolve().parent.parent
      frontend = root / "frontend"
      pnpm = shutil.which("pnpm")
      if pnpm is None:
          pytest.skip("pnpm not on PATH")
      subprocess.run([pnpm, "install", "--frozen-lockfile"], cwd=frontend, check=True)
      subprocess.run([pnpm, "build"], cwd=frontend, check=True)
      out_dir = root / "app" / "ui" / "static" / "island"
      assert (out_dir / "single.js").exists(), "vite build did not produce single.js"
      return out_dir
  ```

  **Important:** check whether `tests/conftest.py` already exists with content. If yes, **append** the three fixtures (`live_server`, `live_server_url`, `pnpm_built_island`) — do not overwrite the existing file. The Playwright `page` fixture comes from `pytest-playwright` (no manual definition needed). The `pnpm_built_island` fixture is consumed by Wave 7 tests (T29–T32) but introduced here in T7 (W2) to avoid a same-wave conftest race within W7.

- [ ] **Step 6: Run the smoke test (Green).**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_playwright_harness_smoke.py -v
  ```

  Expected: 2 passed. If `pytest-playwright` complains about missing browsers, re-run Step 3.

- [ ] **Step 7: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add pyproject.toml uv.lock tests/conftest.py tests/test_playwright_harness_smoke.py
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): add Playwright + uvicorn live-server fixture"
  ```

---

## Wave 3 — Primitives (6 parallel)

Wave 3 ships the six leaf components — no inter-component dependencies. Each task creates exactly two files (`<Name>.tsx` + `<Name>.test.tsx`) and lands a single Red→Green→Commit cycle. Every test ends with a `vitest-axe` check; every component imports `cn()` from `frontend/src/lib/cn.ts`.

### Task T8 — DispositionPill (FR-511 — color + shape + text)

**Wave:** 3
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/DispositionPill.tsx`, `frontend/src/components/DispositionPill.test.tsx`.

The pill MUST encode disposition through three independent perceptual channels: color (background hue), shape (a unique geometric class — checkmark / x / question mark icon), and text. WCAG 1.4.1 (Use of Color) bans color as the sole channel; FR-511 makes that explicit. The DOM-level structural test (T32) asserts the shape via the icon's `data-shape` attribute.

- [ ] **Step 1: Write the failing test (Red) — `frontend/src/components/DispositionPill.test.tsx`.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { DispositionPill } from "./DispositionPill";
  
  describe("DispositionPill", () => {
    it.each([
      ["pass", "Pass", "check"],
      ["fail", "Fail", "x"],
      ["needs_review", "Needs review", "question"],
    ] as const)("renders %s with text + shape", (disposition, label, shape) => {
      const { getByRole } = renderWithProviders(
        <DispositionPill disposition={disposition} />,
      );
      const pill = getByRole("status");
      expect(pill).toHaveTextContent(label);
      expect(pill.querySelector(`[data-shape="${shape}"]`)).not.toBeNull();
    });
  
    it("encodes disposition in three channels (FR-511)", () => {
      const { getByRole } = renderWithProviders(
        <DispositionPill disposition="fail" />,
      );
      const pill = getByRole("status");
      // 1) Text channel.
      expect(pill).toHaveTextContent(/Fail/i);
      // 2) Shape channel — distinct icon per disposition.
      expect(pill.querySelector('[data-shape="x"]')).not.toBeNull();
      // 3) Color channel — applied as a Tailwind class for "fail".
      expect(pill.className).toMatch(/destructive|error/);
    });
  
    it("exposes aria-label for screen readers", () => {
      const { getByRole } = renderWithProviders(
        <DispositionPill disposition="needs_review" />,
      );
      expect(getByRole("status")).toHaveAttribute(
        "aria-label",
        "Disposition: Needs review",
      );
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <>
          <DispositionPill disposition="pass" />
          <DispositionPill disposition="fail" />
          <DispositionPill disposition="needs_review" />
        </>,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Run the test (Red).**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/DispositionPill
  ```

  Expected: `Cannot find module './DispositionPill'`.

- [ ] **Step 3: Create `frontend/src/components/DispositionPill.tsx`.**

  ```tsx
  import { Check, HelpCircle, X } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  import type { Disposition } from "../types/envelopes";
  
  export interface DispositionPillProps {
    disposition: Disposition;
    className?: string;
  }
  
  // FR-511 / WCAG 1.4.1: encode disposition in COLOR + SHAPE + TEXT.
  // shape is asserted structurally by tests/test_disposition_pill_wcag_141.py.
  const _META: Record<
    Disposition,
    { label: string; shape: "check" | "x" | "question"; bg: string; fg: string; Icon: React.ComponentType<{ "aria-hidden"?: boolean; className?: string }> }
  > = {
    pass: {
      label: "Pass",
      shape: "check",
      bg: "bg-[hsl(var(--uswds-success))]",
      fg: "text-white",
      Icon: Check,
    },
    fail: {
      label: "Fail",
      shape: "x",
      bg: "bg-destructive",
      fg: "text-destructive-foreground",
      Icon: X,
    },
    needs_review: {
      label: "Needs review",
      shape: "question",
      bg: "bg-warning",
      fg: "text-warning-foreground",
      Icon: HelpCircle,
    },
  };
  
  export function DispositionPill({ disposition, className }: DispositionPillProps): React.JSX.Element {
    const meta = _META[disposition];
    return (
      <span
        role="status"
        aria-label={`Disposition: ${meta.label}`}
        className={cn(
          "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold",
          meta.bg,
          meta.fg,
          className,
        )}
      >
        <meta.Icon aria-hidden className="h-4 w-4" />
        <span data-shape={meta.shape} aria-hidden="true" />
        <span>{meta.label}</span>
      </span>
    );
  }
  ```

- [ ] **Step 4: Run the test (Green).**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/DispositionPill
  ```

  Expected: 4 passed (5 if `it.each` counts the parametrized cases as 3 + others = 6).

- [ ] **Step 5: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add frontend/src/components/DispositionPill.tsx frontend/src/components/DispositionPill.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): DispositionPill — color + shape + text (FR-511)"
  ```

---

### Task T9 — ConfidenceIndicator (FR-510 — numeric + tri-state band)

**Wave:** 3
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/ConfidenceIndicator.tsx` + `.test.tsx`.

Numeric (0.00–1.00, two decimals) + a 3-state band visualization (high / medium / low).

- [ ] **Step 1: Write the failing test (Red).**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { ConfidenceIndicator } from "./ConfidenceIndicator";
  
  describe("ConfidenceIndicator", () => {
    it("shows numeric (2 decimals) and band label", () => {
      const { getByRole } = renderWithProviders(
        <ConfidenceIndicator band="high" numeric={0.94} />,
      );
      const el = getByRole("group");
      expect(el).toHaveTextContent("0.94");
      expect(el).toHaveTextContent(/High/i);
    });
  
    it.each(["high", "medium", "low"] as const)("renders %s band with aria-valuetext", (band) => {
      const { getByRole } = renderWithProviders(
        <ConfidenceIndicator band={band} numeric={0.5} />,
      );
      const meter = getByRole("meter");
      expect(meter).toHaveAttribute("aria-valuemin", "0");
      expect(meter).toHaveAttribute("aria-valuemax", "1");
      expect(meter).toHaveAttribute("aria-valuenow", "0.5");
      expect(meter).toHaveAttribute(
        "aria-valuetext",
        expect.stringContaining(band),
      );
    });
  
    it("clamps display values out of [0,1]", () => {
      const { getByRole } = renderWithProviders(
        <ConfidenceIndicator band="low" numeric={1.5} />,
      );
      expect(getByRole("meter")).toHaveAttribute("aria-valuenow", "1");
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <ConfidenceIndicator band="medium" numeric={0.62} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/ConfidenceIndicator.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  import type { Band } from "../types/envelopes";
  
  export interface ConfidenceIndicatorProps {
    band: Band;
    numeric: number;
    className?: string;
  }
  
  const _BAND_LABEL: Record<Band, string> = {
    high: "High",
    medium: "Medium",
    low: "Low",
  };
  
  const _BAND_BAR: Record<Band, string> = {
    high: "w-full bg-[hsl(var(--uswds-success))]",
    medium: "w-2/3 bg-[hsl(var(--uswds-warning-dark))]",
    low: "w-1/3 bg-destructive",
  };
  
  export function ConfidenceIndicator({ band, numeric, className }: ConfidenceIndicatorProps): React.JSX.Element {
    const clamped = Math.max(0, Math.min(1, numeric));
    return (
      <div
        role="group"
        aria-label={`Confidence: ${_BAND_LABEL[band]} (${clamped.toFixed(2)})`}
        className={cn("flex items-center gap-2", className)}
      >
        <span className="text-sm font-medium tabular-nums">
          {clamped.toFixed(2)}
        </span>
        <div className="h-2 w-24 overflow-hidden rounded-full bg-muted" aria-hidden>
          <div className={cn("h-full transition-[width]", _BAND_BAR[band])} />
        </div>
        <span
          role="meter"
          aria-valuemin={0}
          aria-valuemax={1}
          aria-valuenow={clamped}
          aria-valuetext={`${_BAND_LABEL[band]} (${band})`}
          className="text-sm"
        >
          {_BAND_LABEL[band]}
        </span>
      </div>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/ConfidenceIndicator
  git -C /home/context/projects/takehome-e7 add frontend/src/components/ConfidenceIndicator.tsx frontend/src/components/ConfidenceIndicator.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): ConfidenceIndicator — numeric + tri-state (FR-510)"
  ```

---

### Task T10 — CitationChip (FR-502)

**Wave:** 3
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/CitationChip.tsx` + `.test.tsx`.

A pressable chip rendering a CFR citation; on click invokes `onOpen()` which (in `EvidencePanel`'s composition) opens the evidence panel.

- [ ] **Step 1: Write the test.**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { CitationChip } from "./CitationChip";
  
  describe("CitationChip", () => {
    it("renders citation text inside a button", () => {
      const { getByRole } = renderWithProviders(
        <CitationChip citation="27 CFR §5.65(b)" onOpen={() => {}} />,
      );
      const btn = getByRole("button");
      expect(btn).toHaveTextContent("27 CFR §5.65(b)");
    });
  
    it("calls onOpen on click and Enter", async () => {
      const onOpen = vi.fn();
      const { getByRole } = renderWithProviders(
        <CitationChip citation="27 CFR §16.21" onOpen={onOpen} />,
      );
      const btn = getByRole("button");
      const user = userEvent.setup();
      await user.click(btn);
      btn.focus();
      await user.keyboard("{Enter}");
      expect(onOpen).toHaveBeenCalledTimes(2);
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <CitationChip citation="27 CFR §4.33" onOpen={() => {}} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/CitationChip.tsx`.**

  ```tsx
  import { BookOpen } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface CitationChipProps {
    citation: string;
    onOpen: () => void;
    className?: string;
  }
  
  export function CitationChip({ citation, onOpen, className }: CitationChipProps): React.JSX.Element {
    return (
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          "inline-flex items-center gap-1 rounded-md border border-border bg-muted px-2 py-1 text-xs font-medium hover:bg-[hsl(var(--uswds-primary-lighter))] focus-visible:ring-2 focus-visible:ring-ring",
          className,
        )}
      >
        <BookOpen aria-hidden className="h-3 w-3" />
        <span>{citation}</span>
      </button>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/CitationChip
  git -C /home/context/projects/takehome-e7 add frontend/src/components/CitationChip.tsx frontend/src/components/CitationChip.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): CitationChip — CFR citation chip (FR-502)"
  ```

---

### Task T11 — Alert (FR-506)

**Wave:** 3
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/Alert.tsx` + `.test.tsx`.

System-level alerts (e.g., format-rejection). Implements WCAG 4.1.3 status-message pattern (`role="alert"` + `aria-live="assertive"` for errors, `role="status"` + `aria-live="polite"` for info).

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { Alert } from "./Alert";
  
  describe("Alert", () => {
    it("renders with role=alert for severity=error", () => {
      const { getByRole } = renderWithProviders(
        <Alert severity="error" title="Format rejected" message="WebP not supported." />,
      );
      const el = getByRole("alert");
      expect(el).toHaveAttribute("aria-live", "assertive");
      expect(el).toHaveTextContent(/Format rejected/);
      expect(el).toHaveTextContent(/WebP not supported/);
    });
  
    it("renders with role=status for severity=info", () => {
      const { getByRole } = renderWithProviders(
        <Alert severity="info" title="Heads up" message="The model is warming." />,
      );
      const el = getByRole("status");
      expect(el).toHaveAttribute("aria-live", "polite");
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <>
          <Alert severity="error" title="A" message="B" />
          <Alert severity="info" title="C" message="D" />
          <Alert severity="warning" title="E" message="F" />
        </>,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/Alert.tsx`.**

  ```tsx
  import { AlertCircle, Info, AlertTriangle } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export type AlertSeverity = "info" | "warning" | "error";
  
  export interface AlertProps {
    severity: AlertSeverity;
    title: string;
    message: string;
    className?: string;
  }
  
  const _META: Record<AlertSeverity, { role: "alert" | "status"; live: "assertive" | "polite"; bg: string; Icon: React.ComponentType<{ "aria-hidden"?: boolean; className?: string }> }> = {
    error: { role: "alert", live: "assertive", bg: "bg-destructive/10 border-destructive text-destructive", Icon: AlertCircle },
    warning: { role: "status", live: "polite", bg: "bg-warning/10 border-warning text-warning", Icon: AlertTriangle },
    info: { role: "status", live: "polite", bg: "bg-[hsl(var(--uswds-info-light))] border-[hsl(var(--uswds-info))] text-[hsl(var(--uswds-info-dark))]", Icon: Info },
  };
  
  export function Alert({ severity, title, message, className }: AlertProps): React.JSX.Element {
    const m = _META[severity];
    return (
      <div
        role={m.role}
        aria-live={m.live}
        className={cn("flex items-start gap-3 rounded-md border p-4", m.bg, className)}
      >
        <m.Icon aria-hidden className="h-5 w-5 mt-0.5 shrink-0" />
        <div>
          <p className="font-semibold">{title}</p>
          <p className="text-sm">{message}</p>
        </div>
      </div>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/Alert
  git -C /home/context/projects/takehome-e7 add frontend/src/components/Alert.tsx frontend/src/components/Alert.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): Alert — WCAG 4.1.3 status-message pattern (FR-506)"
  ```

---

### Task T12 — Toast (FR-506 — transient)

**Wave:** 3
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/Toast.tsx` + `.test.tsx`.

Transient confirmation surface. Auto-dismisses after `duration` ms (default 4000 ms; reduced-motion users see a static toast that lingers until manually dismissed).

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { Toast } from "./Toast";
  
  describe("Toast", () => {
    beforeEach(() => vi.useFakeTimers());
    afterEach(() => vi.useRealTimers());
  
    it("renders with role=status and aria-live=polite", () => {
      const { getByRole } = renderWithProviders(
        <Toast message="Override saved." />,
      );
      const el = getByRole("status");
      expect(el).toHaveAttribute("aria-live", "polite");
      expect(el).toHaveTextContent("Override saved.");
    });
  
    it("calls onDismiss after the default duration (4000 ms)", () => {
      const onDismiss = vi.fn();
      renderWithProviders(<Toast message="Saved" onDismiss={onDismiss} />);
      vi.advanceTimersByTime(4000);
      expect(onDismiss).toHaveBeenCalledTimes(1);
    });
  
    it("respects custom duration", () => {
      const onDismiss = vi.fn();
      renderWithProviders(
        <Toast message="x" duration={1000} onDismiss={onDismiss} />,
      );
      vi.advanceTimersByTime(999);
      expect(onDismiss).not.toHaveBeenCalled();
      vi.advanceTimersByTime(1);
      expect(onDismiss).toHaveBeenCalled();
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(<Toast message="Hi" />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/Toast.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface ToastProps {
    message: string;
    duration?: number;
    onDismiss?: () => void;
    className?: string;
  }
  
  export function Toast({ message, duration = 4000, onDismiss, className }: ToastProps): React.JSX.Element {
    React.useEffect(() => {
      if (!onDismiss) return;
      const t = setTimeout(onDismiss, duration);
      return () => clearTimeout(t);
    }, [duration, onDismiss]);
  
    return (
      <div
        role="status"
        aria-live="polite"
        className={cn(
          "rounded-md border border-border bg-foreground px-4 py-2 text-sm text-background shadow-md",
          className,
        )}
      >
        {message}
      </div>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/Toast
  git -C /home/context/projects/takehome-e7 add frontend/src/components/Toast.tsx frontend/src/components/Toast.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): Toast — transient confirmation (FR-506)"
  ```

---

### Task T13 — LiveRegion (FR-507)

**Wave:** 3
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/LiveRegion.tsx` + `.test.tsx`.

A controlled `aria-live="polite"` region. Consumers push messages via the `messages` prop; the component renders the latest as visible text (sr-only) so screen readers announce it. The single-page entry point sets up one `LiveRegion` at the root and threads an enqueue callback through context (or props).

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { LiveRegion } from "./LiveRegion";
  
  describe("LiveRegion", () => {
    it("renders aria-live=polite by default", () => {
      const { getByRole } = renderWithProviders(<LiveRegion message="Saved" />);
      const el = getByRole("status");
      expect(el).toHaveAttribute("aria-live", "polite");
      expect(el).toHaveTextContent("Saved");
    });
  
    it("supports aria-live=assertive when politeness=assertive", () => {
      const { getByRole } = renderWithProviders(
        <LiveRegion politeness="assertive" message="Critical" />,
      );
      const el = getByRole("alert");
      expect(el).toHaveAttribute("aria-live", "assertive");
    });
  
    it("is visually hidden but exposed to AT", () => {
      const { getByRole } = renderWithProviders(<LiveRegion message="x" />);
      expect(getByRole("status").className).toMatch(/sr-only|absolute/);
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(<LiveRegion message="Hello" />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/LiveRegion.tsx`.**

  Tailwind doesn't ship `sr-only` by default; we use the standard "visually hidden" recipe inline.

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export type Politeness = "polite" | "assertive";
  
  export interface LiveRegionProps {
    message: string;
    politeness?: Politeness;
    className?: string;
  }
  
  // Visually hidden but exposed to AT (NFR-A11Y-002 / NFR-A11Y-003).
  const _SR_ONLY = "absolute -m-px h-px w-px overflow-hidden whitespace-nowrap border-0 p-0 [clip:rect(0,0,0,0)]";
  
  export function LiveRegion({ message, politeness = "polite", className }: LiveRegionProps): React.JSX.Element {
    const role = politeness === "assertive" ? "alert" : "status";
    return (
      <div
        role={role}
        aria-live={politeness}
        aria-atomic="true"
        className={cn(_SR_ONLY, className)}
      >
        {message}
      </div>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/LiveRegion
  git -C /home/context/projects/takehome-e7 add frontend/src/components/LiveRegion.tsx frontend/src/components/LiveRegion.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): LiveRegion — aria-live announcer (FR-507)"
  ```

---

## Wave 4 — Containers (6 parallel)

Each container task: write Vitest test → implement component → run → commit. Tests follow the same skeleton (positive render, negative render, ARIA assertion, axe). To keep the plan tight, the test code blocks for W4 onward elide repetitive imports and only show the unique parts; the shared imports at the top of every `.test.tsx` are ALWAYS:

```tsx
import { describe, it, expect } from "vitest";
import { axe } from "vitest-axe";
import { renderWithProviders } from "../test/render";
```

(Plus `vi` and `userEvent` where the test exercises interaction; called out per task.)

### Task T14 — FieldCard (FR-500)

**Wave:** 4
**Depends on:** T8 (DispositionPill), T9 (ConfidenceIndicator), T10 (CitationChip)
**Owns (creates):** `frontend/src/components/FieldCard.tsx` + `.test.tsx`.

A field card per common field. Composes: field name, extracted vs. expected (visibly separated), `RuleVerdict` (T17), `AISuggestionBlock` (T18, when `present`), `CitationChip` (T10), `ConfidenceIndicator` (T9), `DispositionPill` (T8) for the per-field disposition derived from the worst rule finding.

T14 ships the FieldCard container; T17 and T18 (W4 same wave) are sibling components that the FieldCard renders. To avoid a wave-internal dependency, FieldCard accepts already-rendered React nodes for the verdict and AI suggestion via props (`verdict?: ReactNode; aiSuggestion?: ReactNode`). The single.tsx entry point (T27) wires them. This decoupling keeps W4 a pure 6-parallel wave.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { FieldCard } from "./FieldCard";
  import type { FieldFindingWire } from "../types/envelopes";
  
  const _stub: FieldFindingWire = {
    field_name: "brand_name",
    extracted_value: "Stone's Throw",
    expected_value: "Stone's Throw",
    evidence: { bbox: [0, 0, 100, 50], crop_ref: "x", extraction_confidence: 0.9 },
    rule_findings: [
      {
        rule_id: "common.brand.exact_or_normalized",
        cfr_citation: "27 CFR §5.64",
        disposition: "pass",
        reason_code: "BRAND.NAME.MATCH",
        plain_language_explanation: "OK",
      },
    ],
    ai_suggestion: { present: false, task: null, text: null, model_disposition: null },
    field_confidence: { band: "high", numeric: 0.94 },
  };
  
  describe("FieldCard", () => {
    it("renders field name as a labelled section", () => {
      const { getByRole } = renderWithProviders(<FieldCard field={_stub} />);
      // section landmark with aria-label naming the field.
      expect(getByRole("region", { name: /brand_name/i })).toBeInTheDocument();
    });
  
    it("displays extracted and expected values", () => {
      const { getByText } = renderWithProviders(<FieldCard field={_stub} />);
      expect(getByText(/Stone's Throw/)).toBeInTheDocument();
    });
  
    it("renders custom verdict node when supplied", () => {
      const { getByText } = renderWithProviders(
        <FieldCard field={_stub} verdict={<span>VERDICT_NODE</span>} />,
      );
      expect(getByText("VERDICT_NODE")).toBeInTheDocument();
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(<FieldCard field={_stub} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Implement `frontend/src/components/FieldCard.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  import type { FieldFindingWire } from "../types/envelopes";
  import { ConfidenceIndicator } from "./ConfidenceIndicator";
  import { CitationChip } from "./CitationChip";
  import { DispositionPill } from "./DispositionPill";
  
  export interface FieldCardProps {
    field: FieldFindingWire;
    verdict?: React.ReactNode;
    aiSuggestion?: React.ReactNode;
    onCitationOpen?: (citation: string) => void;
    className?: string;
  }
  
  function _fieldDisposition(field: FieldFindingWire): "pass" | "fail" | "needs_review" {
    const dispositions = field.rule_findings.map((r) => r.disposition);
    if (dispositions.includes("fail")) return "fail";
    if (dispositions.includes("needs_review")) return "needs_review";
    return "pass";
  }
  
  export function FieldCard({ field, verdict, aiSuggestion, onCitationOpen, className }: FieldCardProps): React.JSX.Element {
    const fieldDisp = _fieldDisposition(field);
    return (
      <section
        role="region"
        aria-label={`Field: ${field.field_name}`}
        className={cn("rounded-lg border border-border bg-background p-4 space-y-3", className)}
      >
        <header className="flex items-center justify-between gap-3">
          <h3 className="text-base font-semibold">{field.field_name.replace(/_/g, " ")}</h3>
          <DispositionPill disposition={fieldDisp} />
        </header>
        <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="font-medium text-muted-foreground">Extracted</dt>
            <dd className="break-words">{field.extracted_value || <em>(empty)</em>}</dd>
          </div>
          <div>
            <dt className="font-medium text-muted-foreground">Expected</dt>
            <dd className="break-words">{field.expected_value || <em>(empty)</em>}</dd>
          </div>
        </dl>
        {verdict ?? null}
        {aiSuggestion ?? null}
        <footer className="flex flex-wrap items-center gap-3">
          <ConfidenceIndicator band={field.field_confidence.band} numeric={field.field_confidence.numeric} />
          <div className="flex flex-wrap gap-2">
            {field.rule_findings.map((rf) => (
              <CitationChip
                key={rf.rule_id}
                citation={rf.cfr_citation}
                onOpen={() => onCitationOpen?.(rf.cfr_citation)}
              />
            ))}
          </div>
        </footer>
      </section>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/FieldCard
  git -C /home/context/projects/takehome-e7 add frontend/src/components/FieldCard.tsx frontend/src/components/FieldCard.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): FieldCard — field card container (FR-500)"
  ```

---

### Task T15 — BboxOverlay (FR-501)

**Wave:** 4
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/BboxOverlay.tsx` + `.test.tsx`.

SVG over `<img>` with `<g role="button" tabindex="0" aria-pressed>` per box (per ARCH §7 — Canvas was rejected). Each box is keyboard-focusable; pressing Enter/Space toggles `aria-pressed`.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { BboxOverlay } from "./BboxOverlay";
  
  const _bboxes = [
    { id: "a", bbox: [10, 10, 50, 30] as [number, number, number, number], label: "Brand" },
    { id: "b", bbox: [70, 80, 40, 20] as [number, number, number, number], label: "ABV" },
  ];
  
  describe("BboxOverlay", () => {
    it("renders one focusable button per bbox", () => {
      const { getAllByRole } = renderWithProviders(
        <BboxOverlay imageSrc="/x.png" imageWidth={200} imageHeight={150} bboxes={_bboxes} />,
      );
      const btns = getAllByRole("button");
      expect(btns).toHaveLength(2);
      btns.forEach((b) => expect(b).toHaveAttribute("tabindex", "0"));
    });
  
    it("toggles aria-pressed on Enter and Space", async () => {
      const { getAllByRole } = renderWithProviders(
        <BboxOverlay imageSrc="/x.png" imageWidth={200} imageHeight={150} bboxes={_bboxes} />,
      );
      const user = userEvent.setup();
      const first = getAllByRole("button")[0]!;
      first.focus();
      expect(first).toHaveAttribute("aria-pressed", "false");
      await user.keyboard("{Enter}");
      expect(first).toHaveAttribute("aria-pressed", "true");
      await user.keyboard(" ");
      expect(first).toHaveAttribute("aria-pressed", "false");
    });
  
    it("calls onSelect with the box id on activation", async () => {
      const onSelect = vi.fn();
      const { getAllByRole } = renderWithProviders(
        <BboxOverlay
          imageSrc="/x.png"
          imageWidth={200}
          imageHeight={150}
          bboxes={_bboxes}
          onSelect={onSelect}
        />,
      );
      const user = userEvent.setup();
      await user.click(getAllByRole("button")[1]!);
      expect(onSelect).toHaveBeenCalledWith("b");
    });
  
    it("has alt text on the underlying image", () => {
      const { getByRole } = renderWithProviders(
        <BboxOverlay imageSrc="/x.png" imageWidth={200} imageHeight={150} bboxes={_bboxes} altText="Front label" />,
      );
      expect(getByRole("img", { name: /Front label/i })).toBeInTheDocument();
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <BboxOverlay imageSrc="/x.png" imageWidth={200} imageHeight={150} bboxes={_bboxes} altText="Label" />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/BboxOverlay.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface BboxItem {
    id: string;
    bbox: [number, number, number, number];
    label: string;
  }
  
  export interface BboxOverlayProps {
    imageSrc: string;
    imageWidth: number;
    imageHeight: number;
    bboxes: BboxItem[];
    altText?: string;
    onSelect?: (id: string) => void;
    className?: string;
  }
  
  export function BboxOverlay({
    imageSrc,
    imageWidth,
    imageHeight,
    bboxes,
    altText = "Label image",
    onSelect,
    className,
  }: BboxOverlayProps): React.JSX.Element {
    const [pressed, setPressed] = React.useState<Set<string>>(new Set());
  
    const toggle = (id: string) => {
      setPressed((prev) => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      });
      onSelect?.(id);
    };
  
    return (
      <div
        className={cn("relative inline-block", className)}
        style={{ width: imageWidth, maxWidth: "100%" }}
      >
        <img
          src={imageSrc}
          alt={altText}
          width={imageWidth}
          height={imageHeight}
          style={{ display: "block", width: "100%", height: "auto" }}
        />
        <svg
          aria-hidden={false}
          role="presentation"
          viewBox={`0 0 ${imageWidth} ${imageHeight}`}
          preserveAspectRatio="xMidYMid meet"
          className="absolute inset-0 h-full w-full"
        >
          {bboxes.map(({ id, bbox, label }) => {
            const [x, y, w, h] = bbox;
            const isPressed = pressed.has(id);
            return (
              <g
                key={id}
                role="button"
                tabIndex={0}
                aria-pressed={isPressed}
                aria-label={label}
                onClick={() => toggle(id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    toggle(id);
                  }
                }}
                className="cursor-pointer outline-none focus-visible:[outline:3px_solid_hsl(var(--ring))]"
              >
                <rect
                  x={x}
                  y={y}
                  width={w}
                  height={h}
                  fill={isPressed ? "hsl(var(--uswds-primary)/0.18)" : "transparent"}
                  stroke={isPressed ? "hsl(var(--uswds-primary-vivid))" : "hsl(var(--uswds-primary))"}
                  strokeWidth={isPressed ? 3 : 2}
                />
              </g>
            );
          })}
        </svg>
      </div>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/BboxOverlay
  git -C /home/context/projects/takehome-e7 add frontend/src/components/BboxOverlay.tsx frontend/src/components/BboxOverlay.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): BboxOverlay — SVG-over-img + keyboard ARIA (FR-501)"
  ```

---

### Task T16 — EvidencePanel (FR-502)

**Wave:** 4
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/EvidencePanel.tsx` + `.test.tsx`.

A side-by-side panel: cited regulation text on the left, extracted evidence on the right. Renders inside a Radix `Dialog` (modal) when opened from a `CitationChip`.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { EvidencePanel } from "./EvidencePanel";
  
  describe("EvidencePanel", () => {
    it("renders citation header, regulation text, and evidence side by side", () => {
      const { getByText, getByRole } = renderWithProviders(
        <EvidencePanel
          open
          onOpenChange={() => {}}
          citation="27 CFR §5.65(b)"
          regulationText="ABV statement must …"
          evidenceText="Label says: 45% ALC/VOL."
        />,
      );
      expect(getByRole("dialog")).toBeInTheDocument();
      expect(getByText(/27 CFR §5.65/)).toBeInTheDocument();
      expect(getByText(/ABV statement must/)).toBeInTheDocument();
      expect(getByText(/45% ALC\/VOL/)).toBeInTheDocument();
    });
  
    it("calls onOpenChange(false) when the close button is clicked", async () => {
      const onOpenChange = vi.fn();
      const { getByRole } = renderWithProviders(
        <EvidencePanel
          open
          onOpenChange={onOpenChange}
          citation="x"
          regulationText="y"
          evidenceText="z"
        />,
      );
      const user = userEvent.setup();
      await user.click(getByRole("button", { name: /close/i }));
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  
    it("has no axe violations when open", async () => {
      const { container } = renderWithProviders(
        <EvidencePanel open onOpenChange={() => {}} citation="x" regulationText="y" evidenceText="z" />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/EvidencePanel.tsx`.**

  Uses Radix `Dialog` for focus management + ESC + scrim — those are required for WCAG.

  ```tsx
  import * as Dialog from "@radix-ui/react-dialog";
  import { X } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface EvidencePanelProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    citation: string;
    regulationText: string;
    evidenceText: string;
    className?: string;
  }
  
  export function EvidencePanel({
    open,
    onOpenChange,
    citation,
    regulationText,
    evidenceText,
    className,
  }: EvidencePanelProps): React.JSX.Element {
    return (
      <Dialog.Root open={open} onOpenChange={onOpenChange}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50" />
          <Dialog.Content
            aria-describedby="evidence-desc"
            className={cn(
              "fixed left-1/2 top-1/2 z-50 w-[min(960px,90vw)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-background p-6 shadow-lg",
              className,
            )}
          >
            <header className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold">{citation}</Dialog.Title>
              <Dialog.Close
                aria-label="Close"
                className="rounded-md p-1 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
              >
                <X aria-hidden className="h-5 w-5" />
              </Dialog.Close>
            </header>
            <div id="evidence-desc" className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <article aria-label="Regulation text">
                <h3 className="font-semibold text-muted-foreground">Regulation</h3>
                <p className="mt-1 whitespace-pre-wrap">{regulationText}</p>
              </article>
              <article aria-label="Extracted evidence">
                <h3 className="font-semibold text-muted-foreground">Evidence</h3>
                <p className="mt-1 whitespace-pre-wrap">{evidenceText}</p>
              </article>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/EvidencePanel
  git -C /home/context/projects/takehome-e7 add frontend/src/components/EvidencePanel.tsx frontend/src/components/EvidencePanel.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): EvidencePanel — regulation + evidence dialog (FR-502)"
  ```

---

### Task T17 — RuleVerdict (FR-500/503)

**Wave:** 4
**Depends on:** T8 (DispositionPill)
**Owns (creates):** `frontend/src/components/RuleVerdict.tsx` + `.test.tsx`.

Shows the deterministic rule-engine verdict for a single rule. FR-503: the rule verdict and the AI suggestion (`AISuggestionBlock`) MUST be visibly separated and distinctly labelled. RuleVerdict is wrapped in `<section aria-label="Rule verdict">`.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { RuleVerdict } from "./RuleVerdict";
  import type { RuleFindingWire } from "../types/envelopes";
  
  const _rf: RuleFindingWire = {
    rule_id: "common.warning.heading_style",
    cfr_citation: "27 CFR §16.21(a)",
    disposition: "fail",
    reason_code: "WARNING.STYLE.HEADING_NOT_BOLD_CAPS",
    plain_language_explanation: "Heading not in bold caps.",
  };
  
  describe("RuleVerdict", () => {
    it("renders inside a labelled section per FR-503", () => {
      const { getByRole } = renderWithProviders(<RuleVerdict finding={_rf} />);
      expect(getByRole("region", { name: /Rule verdict/i })).toBeInTheDocument();
    });
  
    it("shows reason code, explanation, and disposition pill", () => {
      const { getByText, getByRole } = renderWithProviders(<RuleVerdict finding={_rf} />);
      expect(getByText(/WARNING\.STYLE\.HEADING_NOT_BOLD_CAPS/)).toBeInTheDocument();
      expect(getByText(/Heading not in bold caps/)).toBeInTheDocument();
      expect(getByRole("status", { name: /Fail/i })).toBeInTheDocument();
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(<RuleVerdict finding={_rf} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/RuleVerdict.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  import type { RuleFindingWire } from "../types/envelopes";
  import { DispositionPill } from "./DispositionPill";
  
  export interface RuleVerdictProps {
    finding: RuleFindingWire;
    className?: string;
  }
  
  export function RuleVerdict({ finding, className }: RuleVerdictProps): React.JSX.Element {
    return (
      <section
        role="region"
        aria-label="Rule verdict"
        className={cn(
          "rounded-md border border-border bg-muted/30 p-3 space-y-2",
          className,
        )}
      >
        <header className="flex items-center justify-between">
          <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Rule verdict
          </h4>
          <DispositionPill disposition={finding.disposition} />
        </header>
        <p className="text-sm">{finding.plain_language_explanation}</p>
        <p className="font-mono text-xs text-muted-foreground">{finding.reason_code}</p>
      </section>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/RuleVerdict
  git -C /home/context/projects/takehome-e7 add frontend/src/components/RuleVerdict.tsx frontend/src/components/RuleVerdict.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): RuleVerdict — labelled rule verdict (FR-500/503)"
  ```

---

### Task T18 — AISuggestionBlock (FR-503)

**Wave:** 4
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/AISuggestionBlock.tsx` + `.test.tsx`.

Shows the AI orchestrator's suggestion when `ai_suggestion.present === true`. The block is wrapped in `<aside aria-label="AI suggestion">`, labelled "AI orchestrator (advisory)", and visually styled distinctly from `RuleVerdict` (left-border accent + muted background) so it cannot be mistaken for the verdict (FR-503). Renders nothing when `present === false`.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { AISuggestionBlock } from "./AISuggestionBlock";
  import type { AISuggestionWire } from "../types/envelopes";
  
  const _present: AISuggestionWire = {
    present: true,
    task: "brand_borderline",
    text: "Apostrophe normalization brings extracted brand into agreement.",
    model_disposition: "pass",
  };
  const _absent: AISuggestionWire = {
    present: false,
    task: null,
    text: null,
    model_disposition: null,
  };
  
  describe("AISuggestionBlock", () => {
    it("renders nothing when ai_suggestion.present is false", () => {
      const { container } = renderWithProviders(
        <AISuggestionBlock suggestion={_absent} />,
      );
      expect(container.firstChild).toBeNull();
    });
  
    it("renders inside <aside> with aria-label='AI suggestion'", () => {
      const { getByRole } = renderWithProviders(
        <AISuggestionBlock suggestion={_present} />,
      );
      expect(getByRole("complementary", { name: /AI suggestion/i })).toBeInTheDocument();
    });
  
    it("labels itself 'advisory' to make FR-503 separation explicit", () => {
      const { getByText } = renderWithProviders(
        <AISuggestionBlock suggestion={_present} />,
      );
      expect(getByText(/advisory/i)).toBeInTheDocument();
    });
  
    it("does NOT render anything resembling a disposition pill at the verdict position", () => {
      const { queryByRole } = renderWithProviders(
        <AISuggestionBlock suggestion={_present} />,
      );
      // FR-503: AI suggestion must NEVER be rendered in the verdict role/position.
      // We assert that it does not expose role=status (DispositionPill's role)
      // anywhere inside the AISuggestionBlock subtree.
      expect(queryByRole("status")).toBeNull();
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <AISuggestionBlock suggestion={_present} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/AISuggestionBlock.tsx`.**

  ```tsx
  import { Sparkles } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  import type { AISuggestionWire } from "../types/envelopes";
  
  export interface AISuggestionBlockProps {
    suggestion: AISuggestionWire;
    className?: string;
  }
  
  const _TASK_LABEL: Record<string, string> = {
    brand_borderline: "Brand-name disambiguation",
    reasoning_enrichment: "Reasoning enrichment",
    ocr_reconciliation: "OCR reconciliation",
  };
  
  export function AISuggestionBlock({ suggestion, className }: AISuggestionBlockProps): React.JSX.Element | null {
    if (!suggestion.present) return null;
    const taskLabel = suggestion.task ? _TASK_LABEL[suggestion.task] ?? suggestion.task : "AI suggestion";
    return (
      <aside
        role="complementary"
        aria-label="AI suggestion"
        className={cn(
          // Distinct styling from RuleVerdict: left-border accent + muted bg.
          "rounded-md border-l-4 border-l-[hsl(var(--uswds-info))] border border-border bg-[hsl(var(--uswds-info-light))]/30 p-3 space-y-1",
          className,
        )}
      >
        <header className="flex items-center gap-2">
          <Sparkles aria-hidden className="h-4 w-4 text-[hsl(var(--uswds-info-dark))]" />
          <h4 className="text-sm font-semibold">
            {taskLabel} <span className="font-normal text-muted-foreground">— advisory</span>
          </h4>
        </header>
        <p className="text-sm">{suggestion.text}</p>
      </aside>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/AISuggestionBlock
  git -C /home/context/projects/takehome-e7 add frontend/src/components/AISuggestionBlock.tsx frontend/src/components/AISuggestionBlock.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): AISuggestionBlock — advisory, never verdict (FR-503)"
  ```

---

### Task T19 — NeedsBetterPhotoCard (FR-505)

**Wave:** 4
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/NeedsBetterPhotoCard.tsx` + `.test.tsx`.

A first-class disposition surface (FR-505 is explicit that this is **not** an error message). Shows the structured reason code (`WARNING.LEGIBILITY.*`), a templated applicant message, and a "Copy message" button (FR-505 stretch: templated applicant-message *display* in MVP; the *send* is stretch).

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { NeedsBetterPhotoCard } from "./NeedsBetterPhotoCard";
  
  describe("NeedsBetterPhotoCard", () => {
    it("renders reason code and templated applicant message", () => {
      const { getByText } = renderWithProviders(
        <NeedsBetterPhotoCard
          reasonCode="WARNING.LEGIBILITY.LOW_RESOLUTION"
          applicantMessage="Please re-submit a higher-resolution photo (≥300 DPI)."
        />,
      );
      expect(getByText(/WARNING\.LEGIBILITY\.LOW_RESOLUTION/)).toBeInTheDocument();
      expect(getByText(/higher-resolution photo/)).toBeInTheDocument();
    });
  
    it("renders inside a labelled region (not as an error/alert)", () => {
      const { getByRole, queryByRole } = renderWithProviders(
        <NeedsBetterPhotoCard reasonCode="x" applicantMessage="y" />,
      );
      expect(getByRole("region", { name: /Needs better photo/i })).toBeInTheDocument();
      expect(queryByRole("alert")).toBeNull();
    });
  
    it("copies the templated message to the clipboard via Copy button", async () => {
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, { clipboard: { writeText } });
      const { getByRole } = renderWithProviders(
        <NeedsBetterPhotoCard reasonCode="x" applicantMessage="HELLO" />,
      );
      const user = userEvent.setup();
      await user.click(getByRole("button", { name: /Copy message/i }));
      expect(writeText).toHaveBeenCalledWith("HELLO");
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <NeedsBetterPhotoCard reasonCode="x" applicantMessage="y" />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/NeedsBetterPhotoCard.tsx`.**

  ```tsx
  import { Camera, Copy } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface NeedsBetterPhotoCardProps {
    reasonCode: string;
    applicantMessage: string;
    className?: string;
  }
  
  export function NeedsBetterPhotoCard({ reasonCode, applicantMessage, className }: NeedsBetterPhotoCardProps): React.JSX.Element {
    const [copied, setCopied] = React.useState(false);
    const handleCopy = async () => {
      await navigator.clipboard.writeText(applicantMessage);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };
    return (
      <section
        role="region"
        aria-label="Needs better photo"
        className={cn("rounded-lg border border-warning/40 bg-warning/10 p-4 space-y-3", className)}
      >
        <header className="flex items-center gap-2">
          <Camera aria-hidden className="h-5 w-5" />
          <h3 className="font-semibold">Needs better photo</h3>
        </header>
        <p className="font-mono text-xs text-muted-foreground">{reasonCode}</p>
        <p className="text-sm">{applicantMessage}</p>
        <button
          type="button"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 rounded-md border border-border bg-background px-3 py-1 text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Copy aria-hidden className="h-4 w-4" />
          {copied ? "Copied" : "Copy message"}
        </button>
      </section>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/NeedsBetterPhotoCard
  git -C /home/context/projects/takehome-e7 add frontend/src/components/NeedsBetterPhotoCard.tsx frontend/src/components/NeedsBetterPhotoCard.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): NeedsBetterPhotoCard — first-class disposition (FR-505)"
  ```

---

## Wave 5 — Drawers / Tables / Hooks (5 parallel)

### Task T20 — ReasonCodePicker (FR-504)

**Wave:** 5
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/ReasonCodePicker.tsx` + `.test.tsx`.

A typeahead picker for reason codes (loaded from a static catalog passed as `codes` prop — the catalog mirrors `rules/reason_codes.yaml`). Resolves on a single keystroke when the typed character is a unique prefix (per L1 §2.5 / R-9). Emits `onSelect(code)` when resolved.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { ReasonCodePicker } from "./ReasonCodePicker";
  
  const _codes = [
    { code: "BRAND.NAME.MISMATCH", description: "Brand mismatch" },
    { code: "WARNING.STYLE.HEADING_NOT_BOLD_CAPS", description: "Heading not bold caps" },
    { code: "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND", description: "ABV out of band" },
    { code: "CLASS_TYPE.SOI.NO_MATCH", description: "Class/Type SOI mismatch" },
  ];
  
  describe("ReasonCodePicker", () => {
    it("filters codes by typed prefix (case-insensitive)", async () => {
      const { getByRole, getAllByRole } = renderWithProviders(
        <ReasonCodePicker codes={_codes} onSelect={() => {}} />,
      );
      const input = getByRole("combobox");
      const user = userEvent.setup();
      await user.type(input, "war");
      const options = getAllByRole("option");
      expect(options).toHaveLength(1);
      expect(options[0]).toHaveTextContent(/WARNING\.STYLE/);
    });
  
    it("calls onSelect when a unique-prefix character is typed (R-9)", async () => {
      const onSelect = vi.fn();
      const { getByRole } = renderWithProviders(
        <ReasonCodePicker codes={_codes} onSelect={onSelect} />,
      );
      const user = userEvent.setup();
      const input = getByRole("combobox");
      await user.type(input, "w"); // 'W' is unique to WARNING.* in the corpus.
      expect(onSelect).toHaveBeenCalledWith("WARNING.STYLE.HEADING_NOT_BOLD_CAPS");
    });
  
    it("does not auto-select on ambiguous prefix", async () => {
      const onSelect = vi.fn();
      const ambig = [
        ..._codes,
        { code: "WARNING.LEGIBILITY.LOW_RESOLUTION", description: "Low res" },
      ];
      const { getByRole } = renderWithProviders(
        <ReasonCodePicker codes={ambig} onSelect={onSelect} />,
      );
      const user = userEvent.setup();
      await user.type(getByRole("combobox"), "w");
      expect(onSelect).not.toHaveBeenCalled();
    });
  
    it("ENTER selects the highlighted option", async () => {
      const onSelect = vi.fn();
      const { getByRole } = renderWithProviders(
        <ReasonCodePicker codes={_codes} onSelect={onSelect} />,
      );
      const user = userEvent.setup();
      const input = getByRole("combobox");
      await user.type(input, "br");
      await user.keyboard("{Enter}");
      expect(onSelect).toHaveBeenCalledWith("BRAND.NAME.MISMATCH");
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <ReasonCodePicker codes={_codes} onSelect={() => {}} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/ReasonCodePicker.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface ReasonCodeEntry {
    code: string;
    description: string;
  }
  
  export interface ReasonCodePickerProps {
    codes: ReasonCodeEntry[];
    onSelect: (code: string) => void;
    autoFocus?: boolean;
    className?: string;
  }
  
  export function ReasonCodePicker({
    codes,
    onSelect,
    autoFocus = true,
    className,
  }: ReasonCodePickerProps): React.JSX.Element {
    const [query, setQuery] = React.useState("");
    const [highlight, setHighlight] = React.useState(0);
    const inputRef = React.useRef<HTMLInputElement>(null);
  
    React.useEffect(() => {
      if (autoFocus) inputRef.current?.focus();
    }, [autoFocus]);
  
    const filtered = React.useMemo(() => {
      const q = query.toUpperCase();
      if (!q) return codes;
      return codes.filter((c) => c.code.startsWith(q));
    }, [codes, query]);
  
    // R-9: single-keystroke resolution when the prefix is unique to one code.
    React.useEffect(() => {
      if (query && filtered.length === 1) {
        onSelect(filtered[0]!.code);
      }
    }, [filtered, query, onSelect]);
  
    React.useEffect(() => {
      setHighlight(0);
    }, [filtered.length]);
  
    const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlight((h) => Math.min(h + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlight((h) => Math.max(h - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const sel = filtered[highlight];
        if (sel) onSelect(sel.code);
      }
    };
  
    const listboxId = React.useId();
    return (
      <div className={cn("space-y-2", className)}>
        <input
          ref={inputRef}
          role="combobox"
          aria-expanded={filtered.length > 0}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-activedescendant={filtered[highlight] ? `${listboxId}-${highlight}` : undefined}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Type a reason-code prefix (e.g., W, BR, AL)…"
          className="w-full rounded-md border border-border bg-background px-3 py-2 text-base focus-visible:ring-2 focus-visible:ring-ring"
        />
        <ul
          id={listboxId}
          role="listbox"
          aria-label="Reason codes"
          className="max-h-64 overflow-y-auto rounded-md border border-border"
        >
          {filtered.map((c, i) => (
            <li
              id={`${listboxId}-${i}`}
              key={c.code}
              role="option"
              aria-selected={i === highlight}
              onMouseDown={(e) => {
                e.preventDefault();
                onSelect(c.code);
              }}
              className={cn(
                "cursor-pointer px-3 py-2 text-sm",
                i === highlight && "bg-muted",
              )}
            >
              <div className="font-mono">{c.code}</div>
              <div className="text-xs text-muted-foreground">{c.description}</div>
            </li>
          ))}
          {filtered.length === 0 && (
            <li className="px-3 py-2 text-sm text-muted-foreground">No matches.</li>
          )}
        </ul>
      </div>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/ReasonCodePicker
  git -C /home/context/projects/takehome-e7 add frontend/src/components/ReasonCodePicker.tsx frontend/src/components/ReasonCodePicker.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): ReasonCodePicker — typeahead w/ prefix resolution (FR-504)"
  ```

---

### Task T21 — RawJSONDrawer (FR-508)

**Wave:** 5
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/RawJSONDrawer.tsx` + `.test.tsx`.

DEV_MODE-gated drawer that displays the full audit-trail JSON. The component itself takes `enabled: boolean` (the page-level entry point sources it from a `data-dev-mode="1"` attribute on `<body>`). When `enabled=false`, the drawer renders nothing.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { RawJSONDrawer } from "./RawJSONDrawer";
  
  const _payload = { evaluation_id: "abc", x: 1 };
  
  describe("RawJSONDrawer", () => {
    it("renders nothing when enabled=false", () => {
      const { container } = renderWithProviders(
        <RawJSONDrawer enabled={false} payload={_payload} />,
      );
      expect(container.firstChild).toBeNull();
    });
  
    it("opens a dialog showing pretty-printed JSON when toggled", async () => {
      const { getByRole } = renderWithProviders(
        <RawJSONDrawer enabled={true} payload={_payload} />,
      );
      const user = userEvent.setup();
      await user.click(getByRole("button", { name: /Show raw JSON/i }));
      const dialog = getByRole("dialog");
      expect(dialog).toHaveTextContent(/"evaluation_id"/);
      expect(dialog).toHaveTextContent(/"abc"/);
    });
  
    it("has no axe violations when enabled and closed", async () => {
      const { container } = renderWithProviders(
        <RawJSONDrawer enabled={true} payload={_payload} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/RawJSONDrawer.tsx`.**

  ```tsx
  import * as Dialog from "@radix-ui/react-dialog";
  import { Code, X } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface RawJSONDrawerProps {
    enabled: boolean;
    payload: unknown;
    className?: string;
  }
  
  export function RawJSONDrawer({ enabled, payload, className }: RawJSONDrawerProps): React.JSX.Element | null {
    const [open, setOpen] = React.useState(false);
    if (!enabled) return null;
    return (
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Trigger asChild>
          <button
            type="button"
            className={cn(
              "inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1 text-sm hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring",
              className,
            )}
          >
            <Code aria-hidden className="h-4 w-4" />
            Show raw JSON
          </button>
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50" />
          <Dialog.Content className="fixed right-0 top-0 z-50 h-full w-[min(720px,90vw)] overflow-y-auto bg-background p-6 shadow-lg">
            <header className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold">Raw JSON (DEV_MODE)</Dialog.Title>
              <Dialog.Close aria-label="Close" className="rounded-md p-1 hover:bg-muted">
                <X aria-hidden className="h-5 w-5" />
              </Dialog.Close>
            </header>
            <pre className="mt-4 whitespace-pre-wrap break-all rounded-md bg-muted p-3 font-mono text-xs">
              {JSON.stringify(payload, null, 2)}
            </pre>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/RawJSONDrawer
  git -C /home/context/projects/takehome-e7 add frontend/src/components/RawJSONDrawer.tsx frontend/src/components/RawJSONDrawer.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): RawJSONDrawer — DEV_MODE audit drawer (FR-508)"
  ```

---

### Task T22 — QueuePosition (FR-406)

**Wave:** 5
**Depends on:** T1, T2
**Owns (creates):** `frontend/src/components/QueuePosition.tsx` + `.test.tsx`.

Shows the current label's queue position out of the total batch size (e.g., `3 of 50`). Includes `aria-label` for the announcement.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect } from "vitest";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { QueuePosition } from "./QueuePosition";
  
  describe("QueuePosition", () => {
    it("renders 'N of M' with descriptive aria-label", () => {
      const { getByRole } = renderWithProviders(
        <QueuePosition current={3} total={50} />,
      );
      const el = getByRole("status");
      expect(el).toHaveTextContent("3 of 50");
      expect(el).toHaveAttribute("aria-label", "Reviewing label 3 of 50");
    });
  
    it("clamps current within [1, total]", () => {
      const { getByRole } = renderWithProviders(
        <QueuePosition current={99} total={50} />,
      );
      expect(getByRole("status")).toHaveTextContent("50 of 50");
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(<QueuePosition current={1} total={1} />);
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/QueuePosition.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  
  export interface QueuePositionProps {
    current: number;
    total: number;
    className?: string;
  }
  
  export function QueuePosition({ current, total, className }: QueuePositionProps): React.JSX.Element {
    const safeCurrent = Math.max(1, Math.min(current, total));
    return (
      <span
        role="status"
        aria-label={`Reviewing label ${safeCurrent} of ${total}`}
        className={cn("inline-flex items-center gap-2 rounded-md border border-border bg-muted px-3 py-1 text-sm font-semibold tabular-nums", className)}
      >
        {safeCurrent} of {total}
      </span>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/QueuePosition
  git -C /home/context/projects/takehome-e7 add frontend/src/components/QueuePosition.tsx frontend/src/components/QueuePosition.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): QueuePosition — current/total indicator (FR-406)"
  ```

---

### Task T23 — BatchTable (FR-509)

**Wave:** 5
**Depends on:** T8 (DispositionPill — used per row)
**Owns (creates):** `frontend/src/components/BatchTable.tsx` + `.test.tsx`.

A sortable table — each row has `label_ref`, queue position, disposition pill, and is keyboard-selectable (↑/↓ + Enter). Sortable by `disposition` and `queue_position` columns (clicking the column header toggles the sort).

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { BatchTable } from "./BatchTable";
  import type { BatchSSEEvent } from "../types/sse";
  
  const _stubRow = (i: number, disposition: "pass" | "fail" | "needs_review"): BatchSSEEvent => ({
    batch_id: "B",
    queue_position: i,
    evaluation_id: `e${i}`,
    label_ref: `lbl-${i}`,
    disposition,
    disposition_confidence: { band: "high", numeric: 0.9 },
    fields: [],
    audit_trail: {
      evaluation_id: `e${i}`,
      rule_set_version: "0.1.0",
      model_version: null,
      prompt_version: null,
      input_hash: "x",
      output_hash: "y",
      started_at: "2026-04-01T00:00:00Z",
      completed_at: "2026-04-01T00:00:01Z",
      per_rule_trace: [],
      overrides: [],
    },
    metrics: {
      total_duration_ms: 1000,
      per_rule_durations_ms: [],
      vision_duration_ms: 500,
      orchestrator_duration_ms: 0,
    },
  });
  
  describe("BatchTable", () => {
    const rows = [_stubRow(1, "pass"), _stubRow(2, "fail"), _stubRow(3, "needs_review")];
  
    it("renders one row per item with disposition pill", () => {
      const { getAllByRole } = renderWithProviders(
        <BatchTable rows={rows} onSelect={() => {}} />,
      );
      // 1 header row + 3 data rows = 4.
      expect(getAllByRole("row")).toHaveLength(4);
    });
  
    it("sorts by queue position ascending by default; toggles on header click", async () => {
      const desc = [_stubRow(3, "pass"), _stubRow(1, "fail"), _stubRow(2, "pass")];
      const { getAllByRole, getByRole } = renderWithProviders(
        <BatchTable rows={desc} onSelect={() => {}} />,
      );
      const positions = () =>
        getAllByRole("row").slice(1).map((r) => r.querySelector('[data-col="position"]')?.textContent);
      expect(positions()).toEqual(["1", "2", "3"]);
      const user = userEvent.setup();
      await user.click(getByRole("button", { name: /Sort by Position/i }));
      expect(positions()).toEqual(["3", "2", "1"]);
    });
  
    it("calls onSelect on row click and Enter keypress", async () => {
      const onSelect = vi.fn();
      const { getAllByRole } = renderWithProviders(
        <BatchTable rows={rows} onSelect={onSelect} />,
      );
      const user = userEvent.setup();
      const dataRows = getAllByRole("row").slice(1);
      await user.click(dataRows[1]!);
      expect(onSelect).toHaveBeenLastCalledWith("lbl-2");
      dataRows[2]!.focus();
      await user.keyboard("{Enter}");
      expect(onSelect).toHaveBeenLastCalledWith("lbl-3");
    });
  
    it("has no axe violations", async () => {
      const { container } = renderWithProviders(
        <BatchTable rows={rows} onSelect={() => {}} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/BatchTable.tsx`.**

  ```tsx
  import * as React from "react";
  import { cn } from "../lib/cn";
  import type { BatchSSEEvent } from "../types/sse";
  import { DispositionPill } from "./DispositionPill";
  
  export type SortKey = "position" | "disposition";
  export type SortDir = "asc" | "desc";
  
  export interface BatchTableProps {
    rows: BatchSSEEvent[];
    onSelect: (labelRef: string) => void;
    className?: string;
  }
  
  const _DISPOSITION_RANK: Record<string, number> = {
    pass: 0,
    needs_review: 1,
    fail: 2,
  };
  
  export function BatchTable({ rows, onSelect, className }: BatchTableProps): React.JSX.Element {
    const [sort, setSort] = React.useState<{ key: SortKey; dir: SortDir }>({
      key: "position",
      dir: "asc",
    });
  
    const sorted = React.useMemo(() => {
      const out = [...rows];
      out.sort((a, b) => {
        const av = sort.key === "position" ? a.queue_position : _DISPOSITION_RANK[a.disposition] ?? 0;
        const bv = sort.key === "position" ? b.queue_position : _DISPOSITION_RANK[b.disposition] ?? 0;
        return sort.dir === "asc" ? av - bv : bv - av;
      });
      return out;
    }, [rows, sort]);
  
    const toggleSort = (key: SortKey) => {
      setSort((prev) =>
        prev.key === key
          ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
          : { key, dir: "asc" },
      );
    };
  
    return (
      <table
        className={cn("w-full border-collapse text-sm", className)}
        aria-label="Batch labels"
      >
        <thead>
          <tr className="border-b-2 border-border bg-muted/40 text-left">
            <th scope="col" className="p-2">
              <button type="button" onClick={() => toggleSort("position")} className="font-semibold underline-offset-2 hover:underline">
                Sort by Position {sort.key === "position" ? (sort.dir === "asc" ? "↑" : "↓") : ""}
              </button>
            </th>
            <th scope="col" className="p-2">Label</th>
            <th scope="col" className="p-2">
              <button type="button" onClick={() => toggleSort("disposition")} className="font-semibold underline-offset-2 hover:underline">
                Sort by Disposition {sort.key === "disposition" ? (sort.dir === "asc" ? "↑" : "↓") : ""}
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => (
            <tr
              key={row.evaluation_id}
              role="row"
              tabIndex={0}
              onClick={() => onSelect(row.label_ref)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(row.label_ref);
                }
              }}
              className="cursor-pointer border-b border-border hover:bg-muted/40 focus-visible:[outline:3px_solid_hsl(var(--ring))]"
            >
              <td data-col="position" className="p-2 tabular-nums">{row.queue_position}</td>
              <td className="p-2 font-mono text-xs">{row.label_ref}</td>
              <td className="p-2"><DispositionPill disposition={row.disposition} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/BatchTable
  git -C /home/context/projects/takehome-e7 add frontend/src/components/BatchTable.tsx frontend/src/components/BatchTable.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): BatchTable — sortable + keyboard-selectable (FR-509)"
  ```

---

### Task T24 — useKeyboardShortcuts hook

**Wave:** 5
**Depends on:** T1
**Owns (creates):** `frontend/src/hooks/useKeyboardShortcuts.ts` + `.test.ts`.

A single hook installing document-level listeners for `O`, `J`, `K`, `Escape`. Each handler is opt-in via the props bag; the hook does not mount handlers for keys without a callback. Cleans up on unmount (StrictMode-correct).

- [ ] **Step 1: Test.**

  ```ts
  import { describe, it, expect, vi } from "vitest";
  import { renderHook } from "@testing-library/react";
  import * as React from "react";
  import { useKeyboardShortcuts } from "./useKeyboardShortcuts";
  
  const fireKey = (key: string, target: EventTarget = document) => {
    target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
  };
  
  describe("useKeyboardShortcuts", () => {
    it("invokes onOverride when 'O' is pressed", () => {
      const onOverride = vi.fn();
      renderHook(() => useKeyboardShortcuts({ onOverride }));
      fireKey("o");
      expect(onOverride).toHaveBeenCalledTimes(1);
    });
  
    it("invokes onNext on 'J' and onPrev on 'K'", () => {
      const onNext = vi.fn();
      const onPrev = vi.fn();
      renderHook(() => useKeyboardShortcuts({ onNext, onPrev }));
      fireKey("j");
      fireKey("k");
      expect(onNext).toHaveBeenCalledTimes(1);
      expect(onPrev).toHaveBeenCalledTimes(1);
    });
  
    it("invokes onEscape on 'Escape'", () => {
      const onEscape = vi.fn();
      renderHook(() => useKeyboardShortcuts({ onEscape }));
      fireKey("Escape");
      expect(onEscape).toHaveBeenCalledTimes(1);
    });
  
    it("ignores keys when typing in <input> / <textarea> (preserves 'O' for typing)", () => {
      const onOverride = vi.fn();
      renderHook(() => useKeyboardShortcuts({ onOverride }));
      const input = document.createElement("input");
      document.body.appendChild(input);
      input.focus();
      fireKey("o", input);
      expect(onOverride).not.toHaveBeenCalled();
      document.body.removeChild(input);
    });
  
    it("cleans up listeners on unmount (StrictMode survival)", () => {
      const onOverride = vi.fn();
      const { unmount } = renderHook(() => useKeyboardShortcuts({ onOverride }));
      unmount();
      fireKey("o");
      expect(onOverride).not.toHaveBeenCalled();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/hooks/useKeyboardShortcuts.ts`.**

  ```ts
  import * as React from "react";
  
  export interface KeyboardShortcuts {
    onOverride?: () => void;
    onNext?: () => void;
    onPrev?: () => void;
    onEscape?: () => void;
    onEnter?: () => void;
  }
  
  function _isTypingTarget(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) return false;
    const tag = target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
    if (target.isContentEditable) return true;
    return false;
  }
  
  export function useKeyboardShortcuts(shortcuts: KeyboardShortcuts): void {
    // Stable ref so handler identity doesn't churn each render (StrictMode).
    const ref = React.useRef(shortcuts);
    React.useEffect(() => {
      ref.current = shortcuts;
    }, [shortcuts]);
  
    React.useEffect(() => {
      const handler = (e: KeyboardEvent) => {
        if (_isTypingTarget(e.target)) return;
        const { onOverride, onNext, onPrev, onEscape, onEnter } = ref.current;
        switch (e.key) {
          case "o":
          case "O":
            if (onOverride) {
              e.preventDefault();
              onOverride();
            }
            break;
          case "j":
          case "J":
            if (onNext) {
              e.preventDefault();
              onNext();
            }
            break;
          case "k":
          case "K":
            if (onPrev) {
              e.preventDefault();
              onPrev();
            }
            break;
          case "Escape":
            if (onEscape) onEscape();
            break;
          case "Enter":
            if (onEnter) onEnter();
            break;
        }
      };
      document.addEventListener("keydown", handler);
      return () => document.removeEventListener("keydown", handler);
    }, []);
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/hooks/useKeyboardShortcuts
  git -C /home/context/projects/takehome-e7 add frontend/src/hooks/useKeyboardShortcuts.ts frontend/src/hooks/useKeyboardShortcuts.test.ts
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): useKeyboardShortcuts — O/J/K/Esc model"
  ```

---

## Wave 6 — Composable + entry points (split into W6a + W6b after v0.2 audit)

> **v0.2 split:** W6a (T25, T26) lands first; W6b (T27, T28) lands after W6a's commits. T27 imports T25 `OverrideDrawer`; T28 imports T26 `useBatchStream` — running all four tasks in one wave was a same-wave race. The §5 wave dependency table and §10 Dependency Graph both reflect the split.

### Task T25 — OverrideDrawer (FR-504/803)

**Wave:** 6a
**Depends on:** T20 (ReasonCodePicker), T24 (useKeyboardShortcuts)
**Owns (creates):** `frontend/src/components/OverrideDrawer.tsx` + `.test.tsx`.

The drawer that satisfies AC-FR-803 — `O → reason → ENTER` in 3 keystrokes. The drawer opens on `O` (handled by the parent via `useKeyboardShortcuts`); inside, `ReasonCodePicker` is auto-focused with empty query; the user types one prefix character ("W", "B", "A", …); if unique, `ReasonCodePicker.onSelect` fires, the drawer's local state captures it; pressing `ENTER` submits via `onSubmit({reasonCode, justification: ""})` (FR-804: justification optional in MVP).

The drawer is a Radix Dialog. Closing the drawer (`onOpenChange(false)`) returns focus to the field card via Radix's default focus management.

- [ ] **Step 1: Test.**

  ```tsx
  import { describe, it, expect, vi } from "vitest";
  import userEvent from "@testing-library/user-event";
  import { axe } from "vitest-axe";
  import { renderWithProviders } from "../test/render";
  import { OverrideDrawer } from "./OverrideDrawer";
  
  const _codes = [
    { code: "BRAND.NAME.MISMATCH", description: "Brand mismatch" },
    { code: "WARNING.STYLE.HEADING_NOT_BOLD_CAPS", description: "Heading not bold caps" },
    { code: "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND", description: "ABV out of band" },
  ];
  
  describe("OverrideDrawer", () => {
    it("renders nothing when open=false", () => {
      const { queryByRole } = renderWithProviders(
        <OverrideDrawer open={false} onOpenChange={() => {}} codes={_codes} onSubmit={() => {}} />,
      );
      expect(queryByRole("dialog")).toBeNull();
    });
  
    it("auto-focuses the picker when opened (FR-803 step 1 'O' lands here)", () => {
      const { getByRole } = renderWithProviders(
        <OverrideDrawer open={true} onOpenChange={() => {}} codes={_codes} onSubmit={() => {}} />,
      );
      expect(getByRole("combobox")).toHaveFocus();
    });
  
    it("AC-FR-803: O→reason→ENTER completes in three keystrokes", async () => {
      const onSubmit = vi.fn();
      const { getByRole } = renderWithProviders(
        <OverrideDrawer open={true} onOpenChange={() => {}} codes={_codes} onSubmit={onSubmit} />,
      );
      const user = userEvent.setup();
      // Keystroke 1 ('O') was the parent-level shortcut that opened this drawer.
      // Keystroke 2: type 'W' (unique prefix → picker auto-selects WARNING.*).
      await user.keyboard("w");
      // Keystroke 3: ENTER → submit.
      await user.keyboard("{Enter}");
      expect(onSubmit).toHaveBeenCalledWith({
        reasonCode: "WARNING.STYLE.HEADING_NOT_BOLD_CAPS",
        justification: "",
      });
    });
  
    it("ESC closes the drawer (calls onOpenChange(false))", async () => {
      const onOpenChange = vi.fn();
      renderWithProviders(
        <OverrideDrawer open={true} onOpenChange={onOpenChange} codes={_codes} onSubmit={() => {}} />,
      );
      const user = userEvent.setup();
      await user.keyboard("{Escape}");
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  
    it("has no axe violations when open", async () => {
      const { container } = renderWithProviders(
        <OverrideDrawer open={true} onOpenChange={() => {}} codes={_codes} onSubmit={() => {}} />,
      );
      expect(await axe(container)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/components/OverrideDrawer.tsx`.**

  ```tsx
  import * as Dialog from "@radix-ui/react-dialog";
  import { X } from "lucide-react";
  import * as React from "react";
  import { cn } from "../lib/cn";
  import { ReasonCodePicker, type ReasonCodeEntry } from "./ReasonCodePicker";
  
  export interface OverrideSubmitPayload {
    reasonCode: string;
    justification: string;
  }
  
  export interface OverrideDrawerProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    codes: ReasonCodeEntry[];
    onSubmit: (payload: OverrideSubmitPayload) => void;
    className?: string;
  }
  
  export function OverrideDrawer({
    open,
    onOpenChange,
    codes,
    onSubmit,
    className,
  }: OverrideDrawerProps): React.JSX.Element {
    const [selectedCode, setSelectedCode] = React.useState<string | null>(null);
    const [justification, setJustification] = React.useState("");
  
    React.useEffect(() => {
      if (!open) {
        setSelectedCode(null);
        setJustification("");
      }
    }, [open]);
  
    React.useEffect(() => {
      if (!open) return;
      const handler = (e: KeyboardEvent) => {
        if (e.key === "Enter" && selectedCode) {
          e.preventDefault();
          onSubmit({ reasonCode: selectedCode, justification });
        }
      };
      document.addEventListener("keydown", handler);
      return () => document.removeEventListener("keydown", handler);
    }, [open, selectedCode, justification, onSubmit]);
  
    return (
      <Dialog.Root open={open} onOpenChange={onOpenChange}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-40 bg-black/50" />
          <Dialog.Content
            aria-describedby="override-help"
            className={cn(
              "fixed right-0 top-0 z-50 flex h-full w-[min(560px,90vw)] flex-col gap-4 bg-background p-6 shadow-lg",
              className,
            )}
          >
            <header className="flex items-center justify-between">
              <Dialog.Title className="text-lg font-semibold">Override disposition</Dialog.Title>
              <Dialog.Close aria-label="Close" className="rounded-md p-1 hover:bg-muted">
                <X aria-hidden className="h-5 w-5" />
              </Dialog.Close>
            </header>
            <p id="override-help" className="text-sm text-muted-foreground">
              Type a reason-code prefix. The picker resolves on the first keystroke
              when the prefix is unique. Press <kbd>Enter</kbd> to submit.
            </p>
            <ReasonCodePicker codes={codes} onSelect={setSelectedCode} />
            {selectedCode && (
              <p className="rounded-md border border-border bg-muted p-2 text-sm">
                Selected: <span className="font-mono">{selectedCode}</span>
              </p>
            )}
            <label className="text-sm">
              Justification (optional)
              <textarea
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-md border border-border bg-background p-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"
              />
            </label>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="rounded-md border border-border px-3 py-1 text-sm hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!selectedCode}
                onClick={() => selectedCode && onSubmit({ reasonCode: selectedCode, justification })}
                className="rounded-md bg-primary px-3 py-1 text-sm text-primary-foreground disabled:opacity-50"
              >
                Submit override
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    );
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/components/OverrideDrawer
  git -C /home/context/projects/takehome-e7 add frontend/src/components/OverrideDrawer.tsx frontend/src/components/OverrideDrawer.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): OverrideDrawer — 3-keystroke override (FR-504/803)"
  ```

---

### Task T26 — useBatchStream (SSE consumer)

**Wave:** 6a
**Depends on:** T1, T5
**Owns (creates):** `frontend/src/sse/useBatchStream.ts` + `.test.ts`.

A React hook subscribing to `/batches/{batch_id}/stream` via the browser `EventSource` API. Pushes per-label events into a `useReducer`-backed store keyed by `label_ref`. Auto-reconnect is the browser default; on reconnect the server resumes from `current_index` (E6 contract). Disposes on unmount.

The test mocks `EventSource` globally and exercises connect / event push / close / unmount.

- [ ] **Step 1: Test.**

  ```ts
  import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
  import { renderHook, act } from "@testing-library/react";
  import { useBatchStream } from "./useBatchStream";
  import type { BatchSSEEvent } from "../types/sse";
  
  class FakeEventSource {
    static last: FakeEventSource | null = null;
    public onmessage: ((e: MessageEvent) => void) | null = null;
    public onerror: ((e: Event) => void) | null = null;
    public closed = false;
    public url: string;
    constructor(url: string) {
      this.url = url;
      FakeEventSource.last = this;
    }
    close(): void { this.closed = true; }
    fire(data: unknown): void {
      this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(data) }));
    }
  }
  
  const _stub = (i: number): BatchSSEEvent => ({
    batch_id: "B",
    queue_position: i,
    evaluation_id: `e${i}`,
    label_ref: `lbl-${i}`,
    disposition: "pass",
    disposition_confidence: { band: "high", numeric: 0.9 },
    fields: [],
    audit_trail: {
      evaluation_id: `e${i}`,
      rule_set_version: "0.1.0",
      model_version: null,
      prompt_version: null,
      input_hash: "h",
      output_hash: "h",
      started_at: "2026-04-01T00:00:00Z",
      completed_at: "2026-04-01T00:00:01Z",
      per_rule_trace: [],
      overrides: [],
    },
    metrics: {
      total_duration_ms: 100,
      per_rule_durations_ms: [],
      vision_duration_ms: 50,
      orchestrator_duration_ms: 0,
    },
  });
  
  describe("useBatchStream", () => {
    beforeEach(() => {
      (globalThis as unknown as { EventSource: typeof FakeEventSource }).EventSource = FakeEventSource;
      FakeEventSource.last = null;
    });
    afterEach(() => { delete (globalThis as { EventSource?: unknown }).EventSource; });
  
    it("opens an EventSource for the given batch_id", () => {
      renderHook(() => useBatchStream("B"));
      expect(FakeEventSource.last?.url).toContain("/batches/B/stream");
    });
  
    it("pushes events into the store keyed by label_ref", () => {
      const { result } = renderHook(() => useBatchStream("B"));
      act(() => FakeEventSource.last!.fire(_stub(1)));
      act(() => FakeEventSource.last!.fire(_stub(2)));
      expect(result.current.events).toHaveLength(2);
      expect(result.current.events[0]!.label_ref).toBe("lbl-1");
      expect(result.current.events[1]!.queue_position).toBe(2);
    });
  
    it("dedupes events that arrive twice for the same label_ref (SSE replay safety)", () => {
      const { result } = renderHook(() => useBatchStream("B"));
      act(() => FakeEventSource.last!.fire(_stub(1)));
      act(() => FakeEventSource.last!.fire(_stub(1)));
      expect(result.current.events).toHaveLength(1);
    });
  
    it("closes the EventSource on unmount", () => {
      const { unmount } = renderHook(() => useBatchStream("B"));
      const es = FakeEventSource.last!;
      unmount();
      expect(es.closed).toBe(true);
    });
  
    it("survives StrictMode double-mount cleanup (closes the old, opens new)", () => {
      // StrictMode behavior: mount → cleanup → mount. After both, latest EventSource is open.
      const { rerender, unmount } = renderHook(() => useBatchStream("B"));
      const first = FakeEventSource.last!;
      rerender();
      const second = FakeEventSource.last!;
      // first or second may be the same instance; we only require that after final unmount, .closed=true.
      unmount();
      expect(second.closed).toBe(true);
      void first;
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/sse/useBatchStream.ts`.**

  ```ts
  import * as React from "react";
  import type { BatchSSEEvent } from "../types/sse";
  
  export interface BatchStreamState {
    events: BatchSSEEvent[];
    error: string | null;
  }
  
  type _Action =
    | { type: "push"; event: BatchSSEEvent }
    | { type: "error"; message: string }
    | { type: "reset" };
  
  function _reducer(state: BatchStreamState, action: _Action): BatchStreamState {
    switch (action.type) {
      case "push":
        if (state.events.some((e) => e.label_ref === action.event.label_ref)) {
          return state;
        }
        return { ...state, events: [...state.events, action.event] };
      case "error":
        return { ...state, error: action.message };
      case "reset":
        return { events: [], error: null };
    }
  }
  
  export function useBatchStream(batchId: string): BatchStreamState {
    const [state, dispatch] = React.useReducer(_reducer, { events: [], error: null });
  
    // FRAMING ASSUMPTION (PRD §6.3): each `MessageEvent` carries one whole
    // BatchSSEEvent envelope as JSON in `msg.data`. If E6 instead emits
    // `event:` / `id:` / `retry:` framed multi-line records, attach
    // `addEventListener('label-update', …)` and friends per `event:` name and
    // re-parse here. Test corpus today is single-line `data:` only.
    React.useEffect(() => {
      if (!batchId) return;
      const url = `/batches/${encodeURIComponent(batchId)}/stream`;
      const es = new EventSource(url);
      es.onmessage = (msg) => {
        try {
          const parsed = JSON.parse(msg.data) as BatchSSEEvent;
          dispatch({ type: "push", event: parsed });
        } catch {
          dispatch({ type: "error", message: "Malformed SSE payload" });
        }
      };
      es.onerror = () => {
        dispatch({ type: "error", message: "SSE connection error" });
      };
      return () => {
        es.close();
      };
    }, [batchId]);
  
    return state;
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/sse/useBatchStream
  git -C /home/context/projects/takehome-e7 add frontend/src/sse/useBatchStream.ts frontend/src/sse/useBatchStream.test.ts
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): useBatchStream — SSE consumer with dedupe"
  ```

---

### Task T27 — Single-label island entry point

**Wave:** 6b
**Depends on:** T5, T8–T19, T20, T24, T25 (envelope types + all single-mode components + hooks)
**Owns (creates):** `frontend/src/single.tsx`, `frontend/src/single.test.tsx`.

The entry point that mounts on `<div id="root" data-mode="single">`. Reads the canned envelope from `<script id="envelope" type="application/json">` (when present). Renders `LiveRegion`, the field-card grid (looping `FieldCard` with `RuleVerdict` + `AISuggestionBlock`), the disposition-level `DispositionPill` + `ConfidenceIndicator`, the override drawer (gated by `useKeyboardShortcuts({ onOverride })`), and `RawJSONDrawer` (gated by `data-dev-mode`).

When the envelope is absent (production-runtime case), shows a minimal "No data — submit a label" placeholder.

- [ ] **Step 1: Write the smoke test (`frontend/src/single.test.tsx`).**

  ```tsx
  /** @vitest-environment jsdom */
  import { describe, it, expect, beforeEach } from "vitest";
  import { axe } from "vitest-axe";
  
  // Set up the DOM as Jinja would render it: <div id="root" data-mode="single">
  // plus a <script id="envelope" type="application/json"> tag.
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="root" data-mode="single"></div>
      <script id="envelope" type="application/json">${JSON.stringify({
        evaluation_id: "00000000-0000-4000-8000-000000000001",
        label_ref: "lbl",
        disposition: "pass",
        disposition_confidence: { band: "high", numeric: 0.9 },
        fields: [],
        audit_trail: {
          evaluation_id: "00000000-0000-4000-8000-000000000001",
          rule_set_version: "0.1.0",
          model_version: null,
          prompt_version: null,
          input_hash: "x",
          output_hash: "y",
          started_at: "2026-04-01T00:00:00Z",
          completed_at: "2026-04-01T00:00:01Z",
          per_rule_trace: [],
          overrides: [],
        },
        metrics: { total_duration_ms: 100, per_rule_durations_ms: [], vision_duration_ms: 50, orchestrator_duration_ms: 0 },
      })}</script>
    `;
  });
  
  describe("single.tsx entry point", () => {
    it("mounts on #root and sets data-mounted='true'", async () => {
      const { mount } = await import("./single");
      mount();
      await new Promise((r) => setTimeout(r, 0));
      const root = document.getElementById("root");
      expect(root).not.toBeNull();
      expect(root!.getAttribute("data-mounted")).toBe("true");
    });
  
    it("has no axe violations on the rendered tree", async () => {
      const { mount } = await import("./single");
      mount();
      await new Promise((r) => setTimeout(r, 50));
      expect(await axe(document.body)).toHaveNoViolations();
    });
  });
  // NOTE: `mount()` is exported (see single.tsx) so each `it` block can
  // explicitly re-mount on its own freshly-rebuilt DOM. Don't rely on the
  // module's auto-mount side effect for tests — Vitest caches modules across
  // tests and the second `it` would otherwise see an empty <div id="root">
  // (because beforeEach wipes innerHTML but the cached module doesn't re-run).
  ```

- [ ] **Step 2: Create `frontend/src/single.tsx`.**

  ```tsx
  import * as React from "react";
  import { createRoot } from "react-dom/client";
  import "./tokens/globals.css";
  import { AISuggestionBlock } from "./components/AISuggestionBlock";
  import { ConfidenceIndicator } from "./components/ConfidenceIndicator";
  import { DispositionPill } from "./components/DispositionPill";
  import { EvidencePanel } from "./components/EvidencePanel";
  import { FieldCard } from "./components/FieldCard";
  import { LiveRegion } from "./components/LiveRegion";
  import { NeedsBetterPhotoCard } from "./components/NeedsBetterPhotoCard";
  import { OverrideDrawer } from "./components/OverrideDrawer";
  import { RawJSONDrawer } from "./components/RawJSONDrawer";
  import { RuleVerdict } from "./components/RuleVerdict";
  import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
  import type { DispositionEnvelope } from "./types/envelopes";
  
  // A minimal hard-coded reason-code catalog mirrors rules/reason_codes.yaml.
  // E7 ships a small subset; E8 (or a build step) can generate the full set.
  //
  // ORDER INVARIANT (FR-803 — 3-keystroke override path):
  // For each fixture's canonical reason code, this array's FIRST entry that
  // shares the same starting letter MUST be that canonical code. The picker
  // (T20) auto-selects only when filter narrows to length === 1; otherwise
  // ENTER picks `filtered[highlight]` and `highlight` resets to 0 on filter
  // change. Combined, that means `O → <letter> → ENTER` lands on the first
  // code with that prefix in this array.
  //
  // Canonical paths verified:
  //  - fixture-03 (WARNING.STYLE.HEADING_NOT_BOLD_CAPS): 'w' → highlight 0
  //    among 3 W-prefixed codes ↑ — this entry must stay at position 0
  //    among W-prefixed entries.
  //
  // Reorder this array only after re-verifying T30's keyboard test still
  // passes. T20 does not assert this invariant; future readers, see also
  // the `tests/manual/a11y-smoke.md` step 7 narration.
  const _REASON_CODES = [
    { code: "BRAND.NAME.MISMATCH", description: "Brand mismatch" },
    { code: "BRAND.NAME.NEEDS_REVIEW", description: "Brand needs review" },
    { code: "WARNING.STYLE.HEADING_NOT_BOLD_CAPS", description: "Heading not bold caps" },
    { code: "WARNING.LEGIBILITY.LOW_RESOLUTION", description: "Low resolution" },
    { code: "WARNING.LEGIBILITY.GLARE", description: "Glare" },
    { code: "ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND", description: "ABV out of band" },
    { code: "CLASS_TYPE.SOI.NO_MATCH", description: "Class/Type SOI mismatch" },
  ];
  
  function SingleApp({ envelope }: { envelope: DispositionEnvelope | null }): React.JSX.Element {
    const [overrideOpen, setOverrideOpen] = React.useState(false);
    const [announcement, setAnnouncement] = React.useState("");
    useKeyboardShortcuts({
      onOverride: () => setOverrideOpen(true),
      onEscape: () => setOverrideOpen(false),
    });
  
    if (!envelope) {
      return (
        <div className="p-4">
          <p>No envelope. Submit a label via <code>POST /labels</code>.</p>
        </div>
      );
    }
  
    const isNeedsBetterPhoto = envelope.fields.some((f) =>
      f.rule_findings.some((rf) => rf.reason_code.startsWith("WARNING.LEGIBILITY.")),
    );
  
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">{envelope.label_ref}</h2>
            <p className="font-mono text-xs text-muted-foreground">{envelope.evaluation_id}</p>
          </div>
          <div className="flex items-center gap-3">
            <DispositionPill disposition={envelope.disposition} />
            <ConfidenceIndicator
              band={envelope.disposition_confidence.band}
              numeric={envelope.disposition_confidence.numeric}
            />
            <RawJSONDrawer enabled={document.body.dataset.devMode === "1"} payload={envelope} />
          </div>
        </header>
  
        {isNeedsBetterPhoto && (
          <NeedsBetterPhotoCard
            reasonCode={envelope.fields[0]!.rule_findings[0]!.reason_code}
            applicantMessage="Please re-submit a higher-resolution photo (≥300 DPI) of the front label."
          />
        )}
  
        <div className="grid grid-cols-1 gap-4">
          {envelope.fields.map((field) => (
            <FieldCard
              key={field.field_name}
              field={field}
              verdict={field.rule_findings[0] ? <RuleVerdict finding={field.rule_findings[0]} /> : null}
              aiSuggestion={<AISuggestionBlock suggestion={field.ai_suggestion} />}
            />
          ))}
        </div>
  
        <OverrideDrawer
          open={overrideOpen}
          onOpenChange={setOverrideOpen}
          codes={_REASON_CODES}
          onSubmit={(p) => {
            setAnnouncement(`Override saved: ${p.reasonCode}`);
            setOverrideOpen(false);
          }}
        />
        <LiveRegion message={announcement} />
        <EvidencePanelStub />
      </div>
    );
  }
  
  // Small inline placeholder so the module pulls EvidencePanel into the bundle
  // for the production runtime; a future task wires citation chip → evidence panel.
  function EvidencePanelStub(): React.JSX.Element {
    const [open, setOpen] = React.useState(false);
    void open;
    return (
      <EvidencePanel
        open={false}
        onOpenChange={setOpen}
        citation=""
        regulationText=""
        evidenceText=""
      />
    );
  }
  
  function _readEnvelope(): DispositionEnvelope | null {
    const tag = document.getElementById("envelope");
    if (!tag) return null;
    try {
      return JSON.parse(tag.textContent ?? "null") as DispositionEnvelope | null;
    } catch {
      return null;
    }
  }
  
  // Exported so the unit test can call it explicitly per-test (Vitest caches
  // modules — relying on the auto-mount side effect would render only on the
  // first `it` block). Production code path uses the auto-mount below.
  export function mount(): void {
    const root = document.getElementById("root");
    if (!root) return;
    const envelope = _readEnvelope();
    createRoot(root).render(
      <React.StrictMode>
        <SingleApp envelope={envelope} />
      </React.StrictMode>,
    );
    root.setAttribute("data-mounted", "true");
  }
  
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mount);
    } else {
      mount();
    }
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/single
  git -C /home/context/projects/takehome-e7 add frontend/src/single.tsx frontend/src/single.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): single.tsx — single-label island entry point"
  ```

---

### Task T28 — Batch island entry point

**Wave:** 6b
**Depends on:** T23 (BatchTable), T22 (QueuePosition), T26 (useBatchStream)
**Owns (creates):** `frontend/src/batch.tsx` + `frontend/src/batch.test.tsx`.

Mounts on `<div id="root" data-mode="batch" data-batch-id="…">`; subscribes via `useBatchStream(batchId)`; renders `BatchTable` with the live event store; renders `QueuePosition` keyed off the most-recent event.

- [ ] **Step 1: Test.**

  ```tsx
  /** @vitest-environment jsdom */
  import { describe, it, expect, beforeEach } from "vitest";
  import { axe } from "vitest-axe";
  
  // Stub EventSource as a no-op for the entry-point smoke; full SSE behavior is
  // covered by useBatchStream.test.ts.
  class _NoopEventSource {
    onmessage: unknown = null;
    onerror: unknown = null;
    close(): void {}
  }
  
  beforeEach(() => {
    (globalThis as unknown as { EventSource: unknown }).EventSource = _NoopEventSource;
    document.body.innerHTML = `<div id="root" data-mode="batch" data-batch-id="abc-123"></div>`;
  });
  
  // NOTE: `mount()` is exported from batch.tsx so each `it` block can re-mount
  // explicitly. Vitest caches modules, so relying on the auto-mount side
  // effect would render only on the first `it` block (subsequent ones would
  // see the empty <div id="root"> that beforeEach restored).
  describe("batch.tsx entry point", () => {
    it("mounts and reads data-batch-id", async () => {
      const { mount } = await import("./batch");
      mount();
      await new Promise((r) => setTimeout(r, 0));
      const root = document.getElementById("root");
      expect(root!.getAttribute("data-mounted")).toBe("true");
      expect(document.body.textContent).toContain("abc-123");
    });
  
    it("has no axe violations on the empty-state render", async () => {
      const { mount } = await import("./batch");
      mount();
      await new Promise((r) => setTimeout(r, 50));
      expect(await axe(document.body)).toHaveNoViolations();
    });
  });
  ```

- [ ] **Step 2: Create `frontend/src/batch.tsx`.**

  ```tsx
  import * as React from "react";
  import { createRoot } from "react-dom/client";
  import "./tokens/globals.css";
  import { BatchTable } from "./components/BatchTable";
  import { LiveRegion } from "./components/LiveRegion";
  import { QueuePosition } from "./components/QueuePosition";
  import { useBatchStream } from "./sse/useBatchStream";
  
  function BatchApp({ batchId }: { batchId: string }): React.JSX.Element {
    const { events, error } = useBatchStream(batchId);
    const total = Math.max(events.length, 1);
    const latest = events[events.length - 1];
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold">Batch {batchId}</h2>
            <p className="text-sm text-muted-foreground">
              Streaming results — {events.length} of {total}
            </p>
          </div>
          {latest && <QueuePosition current={latest.queue_position} total={total} />}
        </header>
        {error && (
          <p role="alert" className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </p>
        )}
        <BatchTable rows={events} onSelect={() => {}} />
        <LiveRegion message={latest ? `Label ${latest.label_ref}: ${latest.disposition}` : ""} />
      </div>
    );
  }
  
  // Exported so tests can call it explicitly per-test (Vitest caches modules
  // — see corresponding NOTE in batch.test.tsx). Production uses the
  // auto-mount block below.
  export function mount(): void {
    const root = document.getElementById("root");
    if (!root) return;
    const batchId = root.getAttribute("data-batch-id") ?? "";
    createRoot(root).render(
      <React.StrictMode>
        <BatchApp batchId={batchId} />
      </React.StrictMode>,
    );
    root.setAttribute("data-mounted", "true");
  }
  
  if (typeof document !== "undefined") {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", mount);
    } else {
      mount();
    }
  }
  ```

- [ ] **Step 3: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test src/batch
  git -C /home/context/projects/takehome-e7 add frontend/src/batch.tsx frontend/src/batch.test.tsx
  git -C /home/context/projects/takehome-e7 commit -m "feat(e7): batch.tsx — batch island entry point"
  ```

---

## Wave 7 — Playwright a11y / keyboard / reflow / WCAG / build-clean (5 parallel)

All Wave 7 tests use the `live_server` + `page` + `pnpm_built_island` fixtures from T7. They render real Jinja shells against the LIVE built island bundle in `app/ui/static/island/`. Since the committed bundle lands only in Wave 8 (T34), the `pnpm_built_island` session fixture (defined in T7's conftest) runs `pnpm install --frozen-lockfile && pnpm build` once at session start to populate `app/ui/static/island/` for the W7 tests. The test bodies use Playwright `route.fulfill()` to stub server data calls (which would otherwise reach E5/E6 routes that don't exist).

**Pre-test build hook.** The session-scoped `pnpm_built_island` fixture in `tests/conftest.py` runs `pnpm build` once before the Playwright session. **It is owned by T7 (W2)** — the Wave 7 tasks (T29–T32) consume it as a read-only session fixture. This avoids a same-wave race on `tests/conftest.py` that would otherwise occur if multiple W7 tasks all tried to add fixtures to it.

### Task T29 — Playwright + axe-core full-page a11y test

**Wave:** 7
**Depends on:** T7 (live_server + pnpm_built_island), all components, T27/T28 (entry points)
**Owns (creates):** `tests/test_a11y_axe.py`.

The test:
1. The `pnpm_built_island` fixture runs `pnpm build` once at session start.
2. For each canned envelope under `tests/fixtures/envelopes/single/`, the test:
   - Stubs `POST /labels` via `page.route()` to return that fixture (not strictly required since the page reads from the embedded `<script id="envelope">`, but keeps the door open for future runtime fetch).
   - Embeds the envelope into the Jinja-rendered `single.html` via a server-side override (we add a `?envelope=<fixture-name>` query string the route honors in test mode).

Because we can't modify `app/api/ui.py` to read query strings AFTER E7 ships (later epochs would risk reverting), we instead use `page.evaluate()` to inject the envelope script tag into the DOM **before** the island module imports its envelope reader.

The test asserts `axe.run({ runOnly: ['wcag2a', 'wcag2aa'] })` returns `violations.length === 0` for every envelope.

> **Note (v0.2):** the `pnpm_built_island` fixture is defined by T7 (W2). T29 only consumes it. No `tests/conftest.py` edit happens in this task.

- [ ] **Step 1: Write `tests/test_a11y_axe.py`.**

  ```python
  """T29: Playwright + axe-core — zero WCAG 2.0 AA violations on every fixture.
  
  Loads the Jinja shell against the live uvicorn fixture, injects the canned
  envelope into the DOM before the React island reads it, then runs axe-core
  inside the page and asserts no AA violations.
  """
  from __future__ import annotations
  
  import json
  from pathlib import Path
  
  import pytest
  from playwright.sync_api import Page
  
  ROOT = Path(__file__).resolve().parent.parent
  FIXTURES = ROOT / "tests" / "fixtures" / "envelopes" / "single"
  AXE_PATH = ROOT / "frontend" / "node_modules" / "axe-core" / "axe.min.js"
  
  
  _SINGLE_FIXTURES = sorted(p.name for p in FIXTURES.glob("*.json"))
  
  
  @pytest.mark.usefixtures("live_server", "pnpm_built_island")
  @pytest.mark.parametrize("fixture_name", _SINGLE_FIXTURES)
  def test_axe_zero_aa_violations_single(
      fixture_name: str, page: Page, live_server_url: str
  ) -> None:
      envelope = json.loads((FIXTURES / fixture_name).read_text())
      # Inject the envelope BEFORE the island imports.
      page.add_init_script(
          script=f"""
            (() => {{
              const tag = document.createElement('script');
              tag.id = 'envelope';
              tag.type = 'application/json';
              tag.textContent = {json.dumps(json.dumps(envelope))};
              const insert = () => {{
                if (document.body) {{
                  document.body.appendChild(tag);
                }} else {{
                  setTimeout(insert, 0);
                }}
              }};
              if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', insert);
              }} else {{
                insert();
              }}
            }})();
          """
      )
      page.goto(f"{live_server_url}/")
      # Wait for the island to mount.
      page.wait_for_selector('[data-mounted="true"]', timeout=5000)
      page.add_script_tag(path=str(AXE_PATH))
      result = page.evaluate(
          """async () => {
            const r = await window.axe.run(document, {
              runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
            });
            return r.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length }));
          }"""
      )
      assert result == [], f"axe violations on {fixture_name}: {result}"
  
  
  @pytest.mark.usefixtures("live_server", "pnpm_built_island")
  def test_axe_zero_aa_violations_batch(page: Page, live_server_url: str) -> None:
      page.goto(f"{live_server_url}/batch/abc-123")
      page.wait_for_selector('[data-mounted="true"]', timeout=5000)
      page.add_script_tag(path=str(AXE_PATH))
      result = page.evaluate(
          """async () => {
            const r = await window.axe.run(document, {
              runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
            });
            return r.violations.map(v => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length }));
          }"""
      )
      assert result == [], f"axe violations on /batch: {result}"
  ```

- [ ] **Step 2: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_a11y_axe.py -v
  git -C /home/context/projects/takehome-e7 add tests/test_a11y_axe.py
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): axe-core CI — zero WCAG 2.0 AA violations"
  ```

---

### Task T30 — Keyboard model (3-keystroke override + J/K)

**Wave:** 7
**Depends on:** T7 (live_server + pnpm_built_island)
**Owns (creates):** `tests/test_keyboard_model.py`.

Loads the single-label shell with fixture-03 (a fail). Asserts: pressing `O → w → ENTER` (3 keystrokes total) opens the override drawer, types into the picker, and submits — verified by listening for the `LiveRegion` announcement "Override saved: WARNING.STYLE.HEADING_NOT_BOLD_CAPS".

- [ ] **Step 1: Test code.**

  ```python
  """T30: AC-FR-803 — three-keystroke override completes the canonical case."""
  from __future__ import annotations
  
  import json
  from pathlib import Path
  
  import pytest
  from playwright.sync_api import Page
  
  ROOT = Path(__file__).resolve().parent.parent
  FIXTURE = (
      ROOT / "tests" / "fixtures" / "envelopes" / "single" / "03-warning-title-case.json"
  )
  
  
  @pytest.mark.usefixtures("live_server", "pnpm_built_island")
  def test_three_keystroke_override(page: Page, live_server_url: str) -> None:
      envelope = json.loads(FIXTURE.read_text())
      page.add_init_script(
          script=f"""
            window.addEventListener('DOMContentLoaded', () => {{
              const tag = document.createElement('script');
              tag.id = 'envelope';
              tag.type = 'application/json';
              tag.textContent = {json.dumps(json.dumps(envelope))};
              document.body.appendChild(tag);
            }});
          """
      )
      page.goto(f"{live_server_url}/")
      page.wait_for_selector('[data-mounted="true"]', timeout=5000)
  
      # Keystroke 1: 'O' → drawer opens, picker auto-focuses.
      page.keyboard.press("o")
      page.wait_for_selector('[role="dialog"]', timeout=2000)
      assert page.locator('[role="combobox"]').count() == 1
  
      # Keystroke 2: 'W' → unique prefix → ReasonCodePicker auto-selects WARNING.*.
      page.keyboard.type("w")
  
      # Keystroke 3: ENTER → submit.
      page.keyboard.press("Enter")
  
      # The LiveRegion announces the saved override; wait for the message.
      page.wait_for_selector(
          'text=/Override saved: WARNING\\.STYLE\\.HEADING_NOT_BOLD_CAPS/',
          timeout=2000,
      )
  
  
  @pytest.mark.usefixtures("live_server", "pnpm_built_island")
  def test_jk_navigation_does_not_steal_typing(page: Page, live_server_url: str) -> None:
      """J/K are reserved for batch navigation but must not fire while typing."""
      envelope = json.loads(FIXTURE.read_text())
      page.add_init_script(
          script=f"""
            window.addEventListener('DOMContentLoaded', () => {{
              const tag = document.createElement('script');
              tag.id = 'envelope';
              tag.type = 'application/json';
              tag.textContent = {json.dumps(json.dumps(envelope))};
              document.body.appendChild(tag);
            }});
          """
      )
      page.goto(f"{live_server_url}/")
      page.wait_for_selector('[data-mounted="true"]', timeout=5000)
      page.keyboard.press("o")
      page.wait_for_selector('[role="dialog"]', timeout=2000)
      page.keyboard.type("j")  # 'j' should land in the picker as text, not navigate.
      assert page.locator('[role="combobox"]').input_value().lower() == "j"
  ```

- [ ] **Step 2: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_keyboard_model.py -v
  git -C /home/context/projects/takehome-e7 add tests/test_keyboard_model.py
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): keyboard model — 3-keystroke override (FR-803)"
  ```

---

### Task T31 — Reflow at 320 CSS px

**Wave:** 7
**Depends on:** T7 (live_server + pnpm_built_island)
**Owns (creates):** `tests/test_reflow_320px.py`.

Sets viewport to 320×640; loads the single shell; asserts `document.documentElement.scrollWidth <= 320` (no horizontal 2-D scroll) per WCAG 1.4.10 / NFR-A11Y-005.

- [ ] **Step 1: Test code.**

  ```python
  """T31: NFR-A11Y-005 — layout reflows at 320 CSS px (WCAG 1.4.10)."""
  from __future__ import annotations
  
  import json
  from pathlib import Path
  
  import pytest
  from playwright.sync_api import Page
  
  ROOT = Path(__file__).resolve().parent.parent
  FIXTURE = (
      ROOT / "tests" / "fixtures" / "envelopes" / "single" / "01-spirits-clean.json"
  )
  
  
  @pytest.mark.usefixtures("live_server", "pnpm_built_island")
  def test_no_horizontal_scroll_at_320px(page: Page, live_server_url: str) -> None:
      envelope = json.loads(FIXTURE.read_text())
      page.set_viewport_size({"width": 320, "height": 640})
      page.add_init_script(
          script=f"""
            window.addEventListener('DOMContentLoaded', () => {{
              const tag = document.createElement('script');
              tag.id = 'envelope';
              tag.type = 'application/json';
              tag.textContent = {json.dumps(json.dumps(envelope))};
              document.body.appendChild(tag);
            }});
          """
      )
      page.goto(f"{live_server_url}/")
      page.wait_for_selector('[data-mounted="true"]', timeout=5000)
      scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
      client_width = page.evaluate("() => document.documentElement.clientWidth")
      # Tolerance of 1 px for sub-pixel rounding.
      assert scroll_width <= client_width + 1, (
          f"320 px viewport shows horizontal scroll: scrollWidth={scroll_width}, clientWidth={client_width}"
      )
  ```

- [ ] **Step 2: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_reflow_320px.py -v
  git -C /home/context/projects/takehome-e7 add tests/test_reflow_320px.py
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): reflow at 320 CSS px (NFR-A11Y-005)"
  ```

---

### Task T32 — DispositionPill WCAG 1.4.1 (color + shape + text)

**Wave:** 7
**Depends on:** T7 (live_server + pnpm_built_island)
**Owns (creates):** `tests/test_disposition_pill_wcag_141.py`.

Loads each fixture; finds the disposition pill at the disposition level; asserts the pill node has:
1. **Text channel** — readable inner text (`Pass`, `Fail`, `Needs review`).
2. **Shape channel** — a child element with `data-shape="check|x|question"`.
3. **Color channel** — non-default background color (computed style is not `transparent` and not the body background).

- [ ] **Step 1: Test code.**

  ```python
  """T32: FR-511 / WCAG 1.4.1 — disposition pill encodes color + shape + text."""
  from __future__ import annotations
  
  import json
  from pathlib import Path
  
  import pytest
  from playwright.sync_api import Page
  
  ROOT = Path(__file__).resolve().parent.parent
  FIXTURES = ROOT / "tests" / "fixtures" / "envelopes" / "single"
  
  
  @pytest.mark.usefixtures("live_server", "pnpm_built_island")
  @pytest.mark.parametrize(
      "fixture_name,expected_disposition,expected_shape,expected_text",
      [
          ("01-spirits-clean.json", "pass", "check", "Pass"),
          ("03-warning-title-case.json", "fail", "x", "Fail"),
          ("04-low-res-blurry.json", "needs_review", "question", "Needs review"),
          ("06-abv-out-of-tolerance.json", "fail", "x", "Fail"),
          ("07-borderline-confidence.json", "needs_review", "question", "Needs review"),
      ],
  )
  def test_disposition_pill_three_channels(
      fixture_name: str,
      expected_disposition: str,
      expected_shape: str,
      expected_text: str,
      page: Page,
      live_server_url: str,
  ) -> None:
      envelope = json.loads((FIXTURES / fixture_name).read_text())
      assert envelope["disposition"] == expected_disposition
      page.add_init_script(
          script=f"""
            window.addEventListener('DOMContentLoaded', () => {{
              const tag = document.createElement('script');
              tag.id = 'envelope';
              tag.type = 'application/json';
              tag.textContent = {json.dumps(json.dumps(envelope))};
              document.body.appendChild(tag);
            }});
          """
      )
      page.goto(f"{live_server_url}/")
      page.wait_for_selector('[data-mounted="true"]', timeout=5000)
  
      # Disposition-level pill is in the header next to the label_ref.
      pill = page.locator(f'[role="status"][aria-label="Disposition: {expected_text}"]').first
      assert pill.count() == 1
      # Text channel.
      assert expected_text in (pill.inner_text() or "")
      # Shape channel.
      assert pill.locator(f'[data-shape="{expected_shape}"]').count() == 1
      # Color channel — computed background-color is not the document body bg.
      pill_bg = pill.evaluate("(el) => getComputedStyle(el).backgroundColor")
      body_bg = page.evaluate("() => getComputedStyle(document.body).backgroundColor")
      assert pill_bg not in {"rgba(0, 0, 0, 0)", "transparent", body_bg}, (
          f"Pill background ({pill_bg}) is not visually distinct from body ({body_bg})"
      )
  ```

- [ ] **Step 2: Run + Commit.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_disposition_pill_wcag_141.py -v
  git -C /home/context/projects/takehome-e7 add tests/test_disposition_pill_wcag_141.py
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): disposition pill — color + shape + text (FR-511)"
  ```

---

### Task T33 — Built-island clean diff CI gate + manual a11y checklist

**Wave:** 7
**Depends on:** T1, T7 (consumes `pnpm_built_island` fixture)
**Owns (creates):** `tests/test_island_build_clean.py`, `tests/manual/a11y-smoke.md`.

The R-5 mitigation: every PR runs `pnpm build` and asserts the diff against `app/ui/static/island/` is empty (so the committed bundle never drifts from sources). The manual a11y smoke checklist is committed for release-time NVDA + VoiceOver review.

- [ ] **Step 1: Test code.**

  ```python
  """T33: R-5 mitigation — committed island bundle matches frontend sources."""
  from __future__ import annotations
  
  import subprocess
  from pathlib import Path
  
  ROOT = Path(__file__).resolve().parent.parent
  
  
  def test_pnpm_build_produces_clean_diff(pnpm_built_island: Path) -> None:
      """The session-scoped `pnpm_built_island` fixture (defined in T7's
      conftest.py) runs `pnpm install --frozen-lockfile && pnpm build` once
      per session; this test just verifies that `git diff` against the
      committed bundle is empty after that build. Reusing the fixture avoids
      a second `pnpm install + pnpm build` invocation per session.
      """
      result = subprocess.run(
          ["git", "diff", "--exit-code", str(pnpm_built_island)],
          cwd=ROOT, capture_output=True, text=True,
      )
      assert result.returncode == 0, (
          f"app/ui/static/island/ diverges from frontend sources after pnpm build:\n{result.stdout}"
      )
  ```

- [ ] **Step 2: Create `tests/manual/a11y-smoke.md`.**

  ```markdown
  # E7 Manual A11y Smoke — NVDA + VoiceOver
  
  Run before each release / before merging E7 to main.
  
  ## NVDA (Windows, Firefox)
  
  1. Load `https://<deployed-url>/` with a canned envelope (single-label demo).
  2. Verify NVDA announces the page title, then the H1 ("TTB Label Verification").
  3. Tab through the focusable elements; the first should be "Skip to main content".
  4. Activate the skip link; focus lands on `#main`.
  5. Tab to a citation chip; activate it (Enter); the evidence dialog opens with focus on the close button.
  6. Press `O`; the override drawer opens; the reason-code picker is announced.
  7. Type `W`; NVDA announces the picker filter narrowing to the WARNING.* codes; the first highlighted option is `WARNING.STYLE.HEADING_NOT_BOLD_CAPS`.
  8. Press `Enter`; NVDA announces the LiveRegion message "Override saved: WARNING.STYLE.HEADING_NOT_BOLD_CAPS".
  9. Press `Esc`; the drawer closes; focus returns to the trigger.
  10. With `prefers-reduced-motion: reduce` set in OS settings, verify no fade/slide animations on dialogs or toasts.
  
  ## VoiceOver (macOS, Safari)
  
  1. Load the page; VO+A reads the page from the top.
  2. VO+→ steps through the navigation; the rotor (VO+U) shows landmarks (banner, main, contentinfo).
  3. The disposition pill is announced as "Disposition: Pass / Fail / Needs review" (not just the icon).
  4. Open the override drawer via `O`; VO announces the modal.
  5. Tab order inside the drawer: combobox → submit → cancel → close.
  6. After submit, VO reads the LiveRegion message.
  
  ## Failure handling
  
  Any item failing a step is a **release blocker** unless an exception is filed under
  `docs/exceptions/` and reviewed by the project owner. The axe-core CI gate should
  catch most issues; this checklist catches what axe cannot (announcement quality,
  VoiceOver-specific behaviors).
  ```

- [ ] **Step 3: Commit.**

  ```bash
  git -C /home/context/projects/takehome-e7 add tests/test_island_build_clean.py tests/manual/a11y-smoke.md
  git -C /home/context/projects/takehome-e7 commit -m "test(e7): island-bundle clean-diff CI gate + manual a11y checklist"
  ```

---

## Wave 8 — Final island build + commit (sequential)

### Task T34 — Build the island bundle and commit the artifacts

**Wave:** 8
**Depends on:** every prior task — every component, hook, entry point, and test must be on the branch first.
**Owns (creates):** `app/ui/static/island/single.js`, `single.css`, `single.js.map`, `batch.js`, `batch.css`, `batch.js.map` (and any `chunks/*.js` Vite produces).

Run `pnpm build`, stage the produced files, commit. After this task, T33 must be green on the new branch tip.

- [ ] **Step 1: Verify worktree is clean.**

  ```bash
  cd /home/context/projects/takehome-e7 && git status --short
  ```

  Expected: empty.

- [ ] **Step 2: Build the island.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm install --frozen-lockfile && pnpm build
  ```

  Expected: Vite outputs `single.js`, `single.css`, `batch.js`, `batch.css`, plus source maps to `app/ui/static/island/`.

- [ ] **Step 3: Inspect the diff.**

  ```bash
  cd /home/context/projects/takehome-e7 && git status --short app/ui/static/island/
  ```

  Expected: a list of new files (the `.gitkeep` is unchanged).

- [ ] **Step 4: Stage + commit.**

  ```bash
  cd /home/context/projects/takehome-e7 && git add app/ui/static/island/
  git -C /home/context/projects/takehome-e7 commit -m "chore(e7): build React island — single + batch bundles"
  ```

- [ ] **Step 5: Verify the clean-diff CI gate passes.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest tests/test_island_build_clean.py -v
  ```

  Expected: 1 passed.

- [ ] **Step 6: Run the full Python test suite as the final sanity gate.**

  ```bash
  cd /home/context/projects/takehome-e7 && uv run --python 3.12 pytest -x -q
  ```

  Expected: full suite green. The original 375 + T3 (8) + T4 (5) + T5 (2) + T7 (2) + T29 (~7 parametrized + 1) + T30 (2) + T31 (1) + T32 (5) + T33 (1) = ~409 tests.

- [ ] **Step 7: Run the frontend test suite as the final sanity gate.**

  ```bash
  cd /home/context/projects/takehome-e7/frontend && pnpm test
  ```

  Expected: every component + hook + entry-point test green.

---

## 8. Self-review (writing-plans skill §"Self-Review")

**Spec coverage** — every L1 §4 exit gate is mapped:

| L1 exit-gate AC | Implemented by |
|---|---|
| 1. `pnpm install && pnpm build` produces island bundle | T1 + T34 |
| 2. `uv run task demo` mounts island; `data-mounted="true"` | T27 + T28 (entry-point smoke); T29 wait-for-selector |
| 3. AC-NFR-A11Y-001 zero AA violations | T29 |
| 4. AC-FR-803 three-keystroke override | T30 |
| 5. AC-FR-503 visibly separated rule verdict + AI suggestion | T17 + T18 (component tests assert `<aside aria-label="AI suggestion">` is NOT a `role="status"`) |
| 6. AC-FR-511 disposition pill color + shape + text | T8 unit test + T32 Playwright structural test |
| 7. AC-NFR-A11Y-004 prefers-reduced-motion | T2 globals.css gate; covered by axe via tag `wcag2aa` (not enforced by axe per se but the global `@media` rule is the enforcement) |
| 8. AC-NFR-A11Y-005 reflow at 320 CSS px | T31 |
| 9. AC-FR-510 confidence numeric + tri-state | T9 |
| 10. AC-FR-507 LiveRegion announces | T13 + T30 (waits for the live-region announcement) |
| 11. 17 components have Vitest tests | T8–T19, T20–T23 (tally: 17 component tests; T24/T26 are hooks; T25 is OverrideDrawer; T27/T28 are entry points). |
| 12. Built island bundle clean diff | T33 + T34 |
| 13. BboxOverlay keyboard navigable | T15 |
| 14. RawJSONDrawer DEV_MODE-gated | T21 + the parent decision in T27 to read `data-dev-mode` |

**Placeholder scan** — every code block embedded in tasks is full code; no "TBD" / "implement later" / "fill in" remain.

**Type consistency** — all component props match the TS types declared in T5 (`DispositionEnvelope`, `BatchSSEEvent`, `Band`, `FieldFindingWire`, etc.). Reason codes appear in fixtures (T3) and in `_REASON_CODES` constant (T27); they are aligned.

**Forbidden-file invariant** — confirmed: no task modifies `app/services/`, `app/api/labels.py`, `app/api/batches.py`, `app/api/overrides.py`, `app/api/healthz.py`, `app/batch/`. The only `app/api/` file touched is `ui.py` (new).

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-04 | Project team (parallel E7 session) | Initial draft. 34 tasks across 8 waves; canned-envelope-fixture-driven; all WCAG / keyboard / reflow gates wired. |
| 0.2 | 2026-05-04 | Project team (parallel E7 session) | Parallel-planning audit. Split W6 into W6a (T25, T26) + W6b (T27, T28) — T27/T28 import symbols T25/T26 produce, so co-running them in a single wave was a same-wave race. Moved `pnpm_built_island` Playwright session fixture from T29 (W7) to T7 (W2) — having T29 own the conftest edit while T30/T31/T32 depended on it created a same-wave conftest race. Updated T29 (no longer modifies `tests/conftest.py`; Step 1 fixture-add removed; remaining steps renumbered) and T30/T31/T32 deps to point at T7 only. Appended §10 Dependency Graph (Task / Depends On / Blocks / Files Owned). |
| 0.4 | 2026-05-04 | Project team (parallel E7 session) | Plan-review iter-2 — §10 reciprocity warnings: added T7 to T33 deps (and T33 to T7 blocks) since T33 now consumes the `pnpm_built_island` fixture; added T3 to T31 deps since `tests/test_reflow_320px.py` reads `tests/fixtures/envelopes/single/01-spirits-clean.json`. Architectural reviewer pass APPROVED with no remaining blockers (C1 mitigation deemed sufficient because T30 is itself the runtime invariant; C2/R1/R5 implementations clean; R2/R6 acceptably deferred for MVP). Plan is ready for parallel-plan-executor. |
| 0.3 | 2026-05-04 | Project team (parallel E7 session) | Plan-review iter-1 — apply 7 structural warnings + 2 architectural critical + 2 recommendations. Structural: bumped per-task **Wave:** headers from `6` → `6a`/`6b` (T25–T28); added `frontend/src/single.test.tsx` to T27 Owns; corrected §4 conftest fixture list (`live_server`, `live_server_url`, `pnpm_built_island`); rewrote Wave 7 prologue first sentence to reflect once-per-session build via the T7 fixture (was: per-test); fixed T3 §10 row to list `batch/05-batch-of-50-envelope.json` + `batch/05-batch-of-50-events.jsonl`; added T3 dep to §10 rows for T29/T30/T32; added T5 dep to §10 row for T27; added `frontend/src/single.test.tsx` to T27 §10 Files Owned. Architectural critical: (C1) added ORDER INVARIANT comment to T27's `_REASON_CODES` array documenting the FR-803 3-keystroke path's dependence on insertion order — the picker (T20) auto-resolves only on a unique prefix, but ENTER lands on `filtered[highlight=0]`; the array order ensures that `O → w → ENTER` resolves to `WARNING.STYLE.HEADING_NOT_BOLD_CAPS`. Updated step 7 of `tests/manual/a11y-smoke.md` narration to match. (C2) Refactored T27's `single.tsx` and T28's `batch.tsx` to **export** `mount()` (renamed from internal `_mount`); test files now call `mount()` explicitly per `it` block to avoid Vitest's module cache silently skipping the second `it` block's render. Recommendations: (R1) T33 now consumes the `pnpm_built_island` fixture instead of running a second `pnpm install + pnpm build` per session — added T7 to T33's deps. (R5) Added FRAMING ASSUMPTION comment to T26's `useBatchStream` hook documenting the single-line `data:` JSON-envelope assumption per PRD §6.3. |

## 10. Dependency Graph

Per `parallel-planning` skill §Step 6. "Blocks" lists direct downstream tasks only (transitive blocks omitted to keep the table readable).

| Task | Depends On | Blocks | Files Owned |
|---|---|---|---|
| T1  | — | T5, T6, T7, T8, T9, T10, T11, T12, T13, T15, T16, T18, T19, T20, T21, T22, T24, T26, T33 | `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/postcss.config.js`, `frontend/index.html`, `frontend/vitest.config.ts`, `frontend/src/lib/cn.ts`, `frontend/src/test/setup.ts`, `frontend/src/test/render.tsx`, `frontend/src/test/smoke.test.tsx` |
| T2  | — | T8, T9, T10, T11, T12, T13, T15, T16, T18, T19, T20, T21, T22 | `frontend/src/tokens/uswds-tokens.css`, `frontend/src/tokens/globals.css`, `frontend/src/tokens/uswds-tokens.test.ts` |
| T3  | — | T29, T30, T31, T32 (consumers via fixture files) | `tests/fixtures/envelopes/single/{01,02,03,04,06,07}-*.json` (6 single fixtures), `tests/fixtures/envelopes/batch/05-batch-of-50-envelope.json`, `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl` (SSE event sequence), `tests/test_canned_envelopes_round_trip.py` |
| T4  | — | T7 | `app/ui/templates/base.html`, `app/ui/templates/single.html`, `app/ui/templates/batch.html`, `app/api/ui.py` (new), `tests/test_ui_routes.py`; modifies `app/main.py` (additive) |
| T5  | T1 | T26, T27, T28 (envelope types) | `frontend/src/types/envelopes.ts`, `frontend/src/types/sse.ts`, `tests/test_typescript_envelope_drift.py` |
| T6  | T1 | — | `frontend/src/test/jest-dom.test.tsx` |
| T7  | T1, T4 | T29, T30, T31, T32, T33 (live_server + pnpm_built_island) | `tests/test_playwright_harness_smoke.py`; modifies `pyproject.toml`, `tests/conftest.py` |
| T8  | T1, T2 | T14, T17, T23, T27, T32 | `frontend/src/components/DispositionPill.tsx`, `frontend/src/components/DispositionPill.test.tsx` |
| T9  | T1, T2 | T14, T27 | `frontend/src/components/ConfidenceIndicator.tsx`, `frontend/src/components/ConfidenceIndicator.test.tsx` |
| T10 | T1, T2 | T14, T27 | `frontend/src/components/CitationChip.tsx`, `frontend/src/components/CitationChip.test.tsx` |
| T11 | T1, T2 | T27 | `frontend/src/components/Alert.tsx`, `frontend/src/components/Alert.test.tsx` |
| T12 | T1, T2 | T27 | `frontend/src/components/Toast.tsx`, `frontend/src/components/Toast.test.tsx` |
| T13 | T1, T2 | T27 | `frontend/src/components/LiveRegion.tsx`, `frontend/src/components/LiveRegion.test.tsx` |
| T14 | T8, T9, T10 | T27 | `frontend/src/components/FieldCard.tsx`, `frontend/src/components/FieldCard.test.tsx` |
| T15 | T1, T2 | T27 | `frontend/src/components/BboxOverlay.tsx`, `frontend/src/components/BboxOverlay.test.tsx` |
| T16 | T1, T2 | T27 | `frontend/src/components/EvidencePanel.tsx`, `frontend/src/components/EvidencePanel.test.tsx` |
| T17 | T8 | T27 | `frontend/src/components/RuleVerdict.tsx`, `frontend/src/components/RuleVerdict.test.tsx` |
| T18 | T1, T2 | T27 | `frontend/src/components/AISuggestionBlock.tsx`, `frontend/src/components/AISuggestionBlock.test.tsx` |
| T19 | T1, T2 | T27 | `frontend/src/components/NeedsBetterPhotoCard.tsx`, `frontend/src/components/NeedsBetterPhotoCard.test.tsx` |
| T20 | T1, T2 | T25, T27 | `frontend/src/components/ReasonCodePicker.tsx`, `frontend/src/components/ReasonCodePicker.test.tsx` |
| T21 | T1, T2 | T27 | `frontend/src/components/RawJSONDrawer.tsx`, `frontend/src/components/RawJSONDrawer.test.tsx` |
| T22 | T1, T2 | T28 | `frontend/src/components/QueuePosition.tsx`, `frontend/src/components/QueuePosition.test.tsx` |
| T23 | T8 | T28 | `frontend/src/components/BatchTable.tsx`, `frontend/src/components/BatchTable.test.tsx` |
| T24 | T1 | T25, T27 | `frontend/src/hooks/useKeyboardShortcuts.ts`, `frontend/src/hooks/useKeyboardShortcuts.test.ts` |
| T25 | T20, T24 | T27 | `frontend/src/components/OverrideDrawer.tsx`, `frontend/src/components/OverrideDrawer.test.tsx` |
| T26 | T1, T5 | T28 | `frontend/src/sse/useBatchStream.ts`, `frontend/src/sse/useBatchStream.test.ts` |
| T27 | T5, T8–T19, T20, T24, T25 | T29, T34 | `frontend/src/single.tsx`, `frontend/src/single.test.tsx` |
| T28 | T22, T23, T26 | T29, T34 | `frontend/src/batch.tsx`, `frontend/src/batch.test.tsx` |
| T29 | T3, T7, T27, T28 (and all components transitively) | T34 | `tests/test_a11y_axe.py` |
| T30 | T3, T7 | T34 | `tests/test_keyboard_model.py` |
| T31 | T3, T7 | T34 | `tests/test_reflow_320px.py` |
| T32 | T3, T7 | T34 | `tests/test_disposition_pill_wcag_141.py` |
| T33 | T1, T7 | T34 | `tests/test_island_build_clean.py`, `tests/manual/a11y-smoke.md` |
| T34 | every prior task | — | `app/ui/static/island/single.js`, `single.css`, `single.js.map`, `batch.js`, `batch.css`, `batch.js.map`, `app/ui/static/island/chunks/*.js` (Vite output) |

**Wave assignment (Task → Wave):**
- W1: T1, T2, T3, T4
- W2: T5, T6, T7
- W3: T8, T9, T10, T11, T12, T13
- W4: T14, T15, T16, T17, T18, T19
- W5: T20, T21, T22, T23, T24
- W6a: T25, T26
- W6b: T27, T28
- W7: T29, T30, T31, T32, T33
- W8: T34
