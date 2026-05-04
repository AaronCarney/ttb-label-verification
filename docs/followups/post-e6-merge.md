# Post-E6-Merge Followups (E7 deferred review items)

Two Important code-review findings on `feat/e7-ui` were deliberately **not fixed in E7** because they wire against contracts that E6 owns. E6 is implemented in a parallel session and has not yet landed on `main` (as of 2026-05-04). When E6 merges, work the items below.

Both have inline `TODO(post-E6):` breadcrumbs at the call sites — grep `TODO(post-E6)` to find them.

---

## 1. Wire override submission to E6's `POST /overrides` endpoint

**Severity:** Important
**Source:** code review of `feat/e7-ui`, item #4
**Call site:** `frontend/src/single.tsx` — `OverrideDrawer.onSubmit` handler (currently only fires LiveRegion + closes drawer)

### What's missing
The override drawer's submit flow today resolves the override **locally**:
```tsx
onSubmit={(p) => {
  setAnnouncement(`Override saved: ${p.reasonCode}`);
  setOverrideOpen(false);
  // TODO(post-E6): POST { reasonCode, justification } to E6's /overrides
}}
```
AC-FR-507 (LiveRegion announces) is satisfied. **AC-FR-801 (audit trail records the override) is not** — the override is not persisted server-side, so `audit_trail.overrides` will not contain it on subsequent fetches.

### What to do once E6 lands
1. Confirm E6's endpoint shape from `app/api/overrides.py` (path, method, request body, response). The PRD §6.2 / FR-803 contract is the authority; E6's implementation should match.
2. Add an `async` POST in the `onSubmit` handler — likely `fetch('/overrides', { method: 'POST', body: JSON.stringify({...}) })` with `evaluation_id`, `field_name` (or whichever scope E6 chose), `reason_code`, `justification_text`, and `reviewer_id` (if E6 requires one — the prototype may stub `reviewer_id="prototype"`).
3. On success: keep the existing LiveRegion announcement.
4. On failure: surface via `Toast` (already shipped, FR-506). Do **not** silently swallow.
5. Consider re-fetching the envelope after submit so `audit_trail.overrides` reflects the new entry — or have E6's response include the updated audit record and patch local state.
6. Add a Playwright test that asserts the POST is made (route stub via `page.route()`) and the LiveRegion + Toast paths fire correctly.

---

## 2. Defensively support named-event SSE framing in `useBatchStream`

**Severity:** Important
**Source:** code review of `feat/e7-ui`, item #9
**Call site:** `frontend/src/sse/useBatchStream.ts` — see FRAMING ASSUMPTION comment

### What's missing
`useBatchStream` only listens for unnamed `message` events:
```ts
es.onmessage = (msg) => { ... };
```
If E6's `/batches/{id}/stream` emits **named** events (e.g. `event: label-update\ndata: {...}`), `EventSource.onmessage` does **not** fire — those are dispatched only via `addEventListener('label-update', ...)`. Result: the batch view would silently hang on "Connecting…" with zero events.

The current PRD §6.3 wire schema does not nail down whether E6 uses named or unnamed framing. Test corpus today is single-line `data:` only.

### What to do once E6 lands
1. Read E6's actual SSE emit code (`app/batch/**`, `app/api/batches.py`). Identify whether it sends `event:` lines or just `data:` lines.
2. If **unnamed only** — current code is correct, just add a comment noting the verification.
3. If **named events** — switch to `es.addEventListener('<event-name>', handler)` for each name E6 emits. Keep `onmessage` as a fallback for backwards-compat or remove it entirely if E6 only uses named events.
4. Update `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl` (and any test that consumes it) to match E6's actual frame format. Currently the JSONL is a sequence of bare-JSON lines; if E6 uses named events, prepend the `event:` line to each test record.
5. `useBatchStream.test.ts` — add a test for the named-event path.

---

## How to discover this file later

- `git log --grep="post-e6"` finds commits referencing this followup
- `grep -rn "TODO(post-E6)" frontend/ docs/` finds inline breadcrumbs
- This file lives in `docs/followups/` — checked in as the canonical landing pad for "thing we knew about but couldn't fix yet"
