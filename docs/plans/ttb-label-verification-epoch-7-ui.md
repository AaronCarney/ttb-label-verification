# Epoch 7 — UI: Jinja2 Shell + React Island

> **Parent:** [`ttb-label-verification-epochs.md`](./ttb-label-verification-epochs.md)
> **Tier:** L1 (epoch-level).
> **Substitutability seam owned:** none — the UI is intentionally not behind an abstraction (per ARCH §8.4: D-013 settles the framework; substituting it would mean rewriting every route and template).
> **Depends on:** **E5** (single-label disposition envelope; `/healthz` warm-up; `POST /labels` endpoint), **E6** (batch envelope; SSE stream; override endpoint).

---

## 1. Goal

Ship the reviewer-facing UI surface — Jinja2 server-rendered page shells plus the React + TypeScript island in `frontend/` (built bundle committed to `app/ui/static/island/`). The 17-component inventory from PRD §5.6 / T8 is implemented; the UI conforms to **WCAG 2.0 Level AA** per Section 508 (NFR-A11Y-001) with axe-core CI gating; the senior-friendly "73-year-old benchmark" is honored (NFR-UX-001); the canonical override flow completes in three keystrokes (FR-803); the bbox overlay is keyboard-navigable and screen-reader-accessible.

After E7, reviewers running the deployed prototype see exactly the surface PRD §5.6 specifies — field cards, citation chips, evidence panels, override drawer, batch table, queue position, anomaly toasts, raw-JSON drawer (DEV_MODE) — and the experience clears WCAG AA without manual intervention on every PR.

---

## 2. Components delivered

### 2.1 Jinja2 shell (`app/ui/templates/`)

Server-rendered page shells per ARCH §4.2.1. Single Python process, no Node runtime in the deployed container; the React island mounts inside a `<div id="root">`.

- `app/ui/templates/base.html` — global page shell: header, USWDS color tokens, skip-link, footer, `<noscript>` fallback that points reviewers to the JSON `POST /labels` endpoint.
- `app/ui/templates/single.html` — single-label review page (mounts the island).
- `app/ui/templates/batch.html` — batch review page (mounts the island in batch mode).
- `app/ui/templates/partials/` — SSE-target partials for any progressive-enhancement fallback (the L2 plan settles whether these are needed; recommend no — the React island is the rendering layer per D-013).

### 2.2 React island (`frontend/`)

Per ARCH §14.1 / D-013. Built with **Vite + React 18 + TypeScript + shadcn/ui + Tailwind CSS** + USWDS color tokens. The 17 components from PRD §5.6 / T8:

| # | Component | File | PRD FR |
|---|---|---|---|
| 1 | `DispositionPill` | `frontend/src/components/DispositionPill.tsx` | FR-511 |
| 2 | `BboxOverlay` | `frontend/src/components/BboxOverlay.tsx` | FR-501 |
| 3 | `EvidencePanel` | `frontend/src/components/EvidencePanel.tsx` | FR-502 |
| 4 | `FieldCard` | `frontend/src/components/FieldCard.tsx` | FR-500 |
| 5 | `RuleVerdict` | `frontend/src/components/RuleVerdict.tsx` | FR-500, FR-503 |
| 6 | `AISuggestionBlock` | `frontend/src/components/AISuggestionBlock.tsx` | FR-503 |
| 7 | `ConfidenceIndicator` | `frontend/src/components/ConfidenceIndicator.tsx` | FR-510 |
| 8 | `CitationChip` | `frontend/src/components/CitationChip.tsx` | FR-502 |
| 9 | `OverrideDrawer` | `frontend/src/components/OverrideDrawer.tsx` | FR-504, FR-803 |
| 10 | `ReasonCodePicker` | `frontend/src/components/ReasonCodePicker.tsx` | FR-504 |
| 11 | `NeedsBetterPhotoCard` | `frontend/src/components/NeedsBetterPhotoCard.tsx` | FR-505 |
| 12 | `RawJSONDrawer` | `frontend/src/components/RawJSONDrawer.tsx` | FR-508 |
| 13 | `BatchTable` | `frontend/src/components/BatchTable.tsx` | FR-509 |
| 14 | `QueuePosition` | `frontend/src/components/QueuePosition.tsx` | FR-406 |
| 15 | `Alert` | `frontend/src/components/Alert.tsx` | FR-506 |
| 16 | `Toast` | `frontend/src/components/Toast.tsx` | FR-506 |
| 17 | `LiveRegion` | `frontend/src/components/LiveRegion.tsx` | FR-507 |

Each component file includes a Vitest sibling test (`<Component>.test.tsx`) covering at least: positive render, negative render, keyboard interaction (where applicable), and ARIA semantics.

### 2.3 USWDS tokens (`frontend/src/tokens/uswds-tokens.css`)

USWDS v3 color tokens applied as CSS custom properties; mapped to shadcn/ui CSS vars per ARCH §7. The L2 plan ships the CSS files; documentation references the USWDS token versions used.

### 2.4 SSE consumer (`frontend/src/sse/useBatchStream.ts`)

A small React hook backed by the browser `EventSource` API:

- Subscribes to `/batches/{batch_id}/stream`.
- Pushes per-label events into a `useReducer` store; the `BatchTable` reads from this store.
- Handles auto-reconnect (browser default with `retry:` SSE comment); on reconnect, the server resumes from `current_index` per E6's contract.
- Disposes on component unmount.

### 2.5 Keyboard model (`frontend/src/hooks/useKeyboardShortcuts.ts`)

Per PRD §2.5 / T8 keyboard model:

- `O` → opens `OverrideDrawer` with focus on `ReasonCodePicker`.
- `J / K` → next / previous label in batch.
- `ENTER` (in `OverrideDrawer`) → submits the override.
- `ESC` (anywhere) → closes drawers / dialogs.
- The "three-keystroke override" target (FR-803) is `O → reason → ENTER` where the reason picker resolves on a single keystroke if the typed character is a unique prefix of a reason code (per E2's reason-code prefix uniqueness invariant).

### 2.6 Accessibility infrastructure

- `LiveRegion` component (per FR-507) — an ARIA `aria-live="polite"` region announcing disposition changes and override confirmations to screen readers.
- `prefers-reduced-motion` honored: every animation is gated behind `@media (prefers-reduced-motion: no-preference)` (NFR-A11Y-004).
- Reflow at 320 CSS px (NFR-A11Y-005): the layout uses CSS grid and flex with `min-content` widths; tested at 320 px viewport.
- `BboxOverlay` is `<svg>` over `<img>` with `<g role="button" tabindex="0" aria-pressed>` per box per ARCH §7 — Canvas was rejected.
- Disposition pill uses **color + shape + text** (FR-511 / WCAG 1.4.1) — the pill is a `<span>` with a unique geometric shape per disposition state plus the text label.

### 2.7 Vite build

- `frontend/vite.config.ts` — output goes to `app/ui/static/island/` so FastAPI's `StaticFiles` mount serves it.
- `frontend/package.json` — `react`, `react-dom`, `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`, `lucide-react`, `tailwindcss`, devDeps `vite`, `typescript`, `@vitejs/plugin-react`.
- `frontend/pnpm-lock.yaml` committed.
- The **built bundle** (`app/ui/static/island/`) is committed (per D-013 consequences) so reviewers running `uv run task demo` do not need Node.

### 2.8 Test surface

- `frontend/src/components/*.test.tsx` — Vitest unit tests for every component (≥ 17 files; ≥ 60 cases total covering positive/negative/keyboard/ARIA per component).
- `frontend/src/sse/useBatchStream.test.ts` — SSE hook covers connect / disconnect / reconnect / event push.
- `frontend/src/hooks/useKeyboardShortcuts.test.ts` — covers each shortcut + focus behavior.
- `tests/test_a11y_axe.py` — Playwright + axe-core CI test that loads each demo fixture and asserts **zero WCAG 2.0 Level AA violations**.
- `tests/test_keyboard_model.py` — Playwright tests for `O → reason → ENTER` (3-keystroke target) and `J/K` navigation.
- `tests/test_reflow_320px.py` — Playwright tests that the layout reflows at 320 CSS px without 2-D scrolling.
- `tests/test_disposition_pill_wcag_141.py` — confirms the disposition pill uses color + shape + text (the shape is asserted via DOM class assertion; the text via inner text).
- `tests/manual/a11y-smoke.md` — checklist for NVDA + VoiceOver smoke (manual); referenced from the L2 plan.
- `tests/test_island_build_clean.py` — `pnpm build && git diff --exit-code app/ui/static/island/` — the built bundle is up-to-date relative to sources (R-5 mitigation, parent §6).

---

## 3. Wire / data contracts owned by this epoch

E7 owns no wire contract — it consumes E5 / E6 endpoints and SSE events. The TypeScript types in `frontend/src/types/` are generated from the Python Pydantic schemas (recommended) or hand-mirrored (acceptable for prototype). The L2 plan settles this; recommend `datamodel-code-generator` to keep them in sync.

E7 **does** own the `O / J / K / ENTER / ESC` keyboard contract — adding a new shortcut in any later epoch requires an L1 revision because reviewer training depends on shortcut stability.

---

## 4. Exit gate

The epoch lands when **all of these pass**:

1. `frontend/` builds with `cd frontend && pnpm install && pnpm build`; built bundle lands in `app/ui/static/island/`.
2. `uv run task demo` serves `single.html` and `batch.html`; both pages mount the React island successfully (the L2 plan ships a smoke test that asserts a `data-mounted="true"` attribute appears in the DOM after island boot).
3. **AC-NFR-A11Y-001**: `tests/test_a11y_axe.py` reports **zero** WCAG 2.0 Level AA violations on each of fixtures 01–07.
4. **AC-FR-803**: three-keystroke override completes (`O → reason-code-first-letter → ENTER`) in the canonical case; verified by `tests/test_keyboard_model.py`.
5. **AC-FR-503**: rule verdict and AI suggestion are visibly separated — distinct `<section>` containers with distinct `aria-label`s and visual styling; AI suggestion is **never** rendered in the disposition position.
6. **AC-FR-511**: disposition pill uses color + shape + text (verified structurally by the DOM-class test).
7. **AC-NFR-A11Y-004**: `prefers-reduced-motion: reduce` disables animations; verified by Playwright with the media-feature override.
8. **AC-NFR-A11Y-005**: layout reflows at 320 CSS px without 2-D scrolling.
9. **AC-FR-510**: confidence indicator shows numeric + tri-state band (high/medium/low).
10. **AC-FR-507**: live region announces disposition changes and override confirmations (Playwright assertion against `aria-live` content).
11. The 17 PRD §5.6 components all have Vitest tests with ≥ 1 positive, ≥ 1 negative case each.
12. Built island bundle is **clean** — `pnpm build && git diff --exit-code app/ui/static/island/` returns 0 (CI gate).
13. `BboxOverlay` is keyboard-navigable: each `<g role="button" tabindex="0">` is reachable via Tab; `Enter` toggles the `aria-pressed` state.
14. `RawJSONDrawer` is reachable only when `DEV_MODE=1` (per D-019); when `DEV_MODE` is unset, the drawer is not registered and the related `GET /batches/{id}/labels/{lid}/calls` route returns 404.

---

## 5. TDD strategy

**Mockable** —

- The server's `POST /labels`, SSE stream, and override endpoint — replaced by a Vitest mock or a Playwright `route.fulfill()` stub that returns canned PRD §6.2 envelopes.
- The browser's `EventSource` — replaced by a Vitest mock for `useBatchStream` unit tests.

**Real** —

- The actual DOM (`@testing-library/react`).
- The actual axe-core engine (real WCAG checking).
- The actual Vite build pipeline.

**Test layering.**

- *Unit* (Vitest, in `frontend/`) — every component, every hook.
- *A11y* (Playwright + axe-core, in `tests/`) — full-page checks against demo fixtures.
- *Keyboard* (Playwright) — three-keystroke override, J/K navigation, focus management.
- *Reflow* (Playwright) — viewport resize.
- *Manual* (NVDA + VoiceOver smoke, documented in `tests/manual/a11y-smoke.md`) — out of CI; documented as a release-time check.

**CI integration.** The built bundle is committed; CI verifies `pnpm build` produces a clean diff. Vitest runs in `frontend/`; Playwright runs against a transient `uvicorn` instance with a mocked `Evaluator` (so the rule engine and LLMs are not required at UI test time).

---

## 6. Out of scope for this epoch

- Live model integration in UI tests — the UI tests use canned envelopes; live-pipeline rendering is exercised by E5/E6/E8 tests.
- Internationalization — out of MVP per PRD §3.3.
- Advanced WCAG 2.1 / 2.2 success criteria beyond NFR-A11Y-003 design targets (the appendix list is the design target, not the regulatory minimum).
- Supervisor calibration view — **stretch** (parent §8); lands in E7 if the calendar permits, else E8.
- Templated applicant-message **send** — **stretch** (parent §8); MVP ships the *display* of the templated message and a Copy button.

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The committed island bundle drifts from frontend sources (R-5 in parent §6) | Medium | Medium | CI gate: `pnpm build && git diff --exit-code app/ui/static/island/` is 0 on every PR |
| WCAG AA axe-core violations on non-trivial demo fixtures | Medium | High | The L2 plan front-loads the a11y tests so violations surface early (write the failing axe test before implementing the component); shadcn/ui + Radix gives correct ARIA primitives by default |
| SSE consumer + React 18 strict mode double-invokes side effects | Medium | Medium | The `useBatchStream` hook uses `useEffect` cleanup correctly and the test suite explicitly exercises strict-mode double-invocation (`<React.StrictMode>` wrapper in test renderers) |
| Three-keystroke target depends on reason-code prefix uniqueness (R-9 in parent §6) | Medium | Low | E2 enforces the prefix uniqueness invariant at startup; if violated, the picker resolves on the second keystroke (graceful degradation, not a hard fail) |
| Reflow at 320 px breaks `BboxOverlay` because the SVG aspect ratio collapses | Medium | Medium | The overlay is wrapped in a `min-width:0` flex container with `object-fit: contain` on the `<img>`; tested at 320, 768, 1280 viewports |
| Color tokens drift between USWDS and shadcn — light/dark mismatch | Low | Medium | A single `tokens.css` file is the source for both; tested for token presence by a CI grep |
| The `<noscript>` fallback over-promises and under-delivers | Low | Low | The fallback explicitly says "JavaScript is required for the reviewer UI; for programmatic submissions, see the API at `POST /labels`" — no fallback rendering |
| Playwright + axe-core add 5+ minutes to CI | Medium | Low | A11y check runs only on `tests/test_a11y_axe.py` against 7 fixtures; ≤ 1 minute total |

---

## 8. L2 hand-off notes

When E7 lands:

1. Decompose into ~20 tasks: 17 components (parallelizable in waves of 5–6) → keyboard hook → SSE hook → reflow + a11y CI → island build verification.
2. **Wave structure:** primitives (`Alert`, `Toast`, `LiveRegion`, `CitationChip`, `ConfidenceIndicator`, `DispositionPill`) first (wave 1, parallel) → containers (`FieldCard`, `BboxOverlay`, `EvidencePanel`, `RuleVerdict`, `AISuggestionBlock`, `NeedsBetterPhotoCard`, `RawJSONDrawer`, `BatchTable`, `QueuePosition`) (wave 2, parallel after primitives) → drawers (`OverrideDrawer`, `ReasonCodePicker`) (wave 3, after containers) → hooks + a11y CI (wave 4) → integration smoke (wave 5).
3. The L2 plan **must** include a task that runs `pnpm build` and verifies the bundle diff is clean — this is the R-5 canary.
4. The L2 plan **must** include a task that exercises the manual NVDA + VoiceOver smoke checklist — even though the test is manual, the checklist is committed under `tests/manual/a11y-smoke.md`.
5. TypeScript types: recommend running `datamodel-code-generator --input-file-type pydantic --input app/schemas/wire/disposition.py --output frontend/src/types/disposition.ts` as a build step; if not, hand-mirror with a CI grep for shape drift.

---

## 9. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial epoch-7 L1 doc. |
