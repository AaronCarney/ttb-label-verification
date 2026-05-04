# Post-E6-Merge Followups (E7 deferred review items)

Two Important code-review findings on `feat/e7-ui` were deliberately **not fixed in E7** because they wired against contracts that E6 owned. **Both are now resolved on `feat/e7-ui` as of 2026-05-04.** Inline `TODO(post-E6):` breadcrumbs have been removed from the call sites.

A third section below lists items that were **deferred to post-E8** — they were considered while closing items 1 and 2 but require either UI affordances or backend routes not yet on the table.

---

## 1. Wire override submission to E6's `POST /overrides` endpoint

**Status:** RESOLVED 2026-05-04
**Severity:** Important
**Source:** code review of `feat/e7-ui`, item #4
**Call site:** `frontend/src/single.tsx` — `OverrideDrawer.onSubmit` handler

### What was missing
The override drawer's submit flow resolved the override **locally**:
```tsx
onSubmit={(p) => {
  setAnnouncement(`Override saved: ${p.reasonCode}`);
  setOverrideOpen(false);
  // TODO(post-E6): POST { reasonCode, justification } to E6's /overrides
}}
```
AC-FR-507 (LiveRegion announces) was satisfied. **AC-FR-801 (audit trail records the override) was not** — the override was not persisted server-side.

### Resolution

- Test commit `638f1b8` — RED test for POST shape (`test_three_keystroke_override_posts_to_endpoint`).
- Implementation commit `eef5e78` — `OverrideDrawer.onSubmit` wired to `POST /labels/{evaluation_id}/overrides`. `applied_disposition` is derived from the reason-code prefix (per **D-PE6-01**: `WARNING.*` → `needs_review`, `FAIL.*` → `fail`, `PASS.*` → `pass`). LiveRegion announcement preserved on success; Toast surface on failure.
- Failure-path commit `c096e0f` — RED test for the 422 toast surface (`test_override_failure_path_surfaces_toast`).
- Test selector fix `9d6b203` — switched the 422 test to a text-based locator. The original `[role="status"]` selector collided with disposition badges (which also use `role="status"` for screen-reader announcement) under Playwright strict mode.

### Locked decisions
- **D-PE6-01** — `applied_disposition` is derived from the reason-code prefix in E7. An explicit picker UX is deferred (see DEFER-4 below).

---

## 2. Defensively support named-event SSE framing in `useBatchStream`

**Status:** RESOLVED 2026-05-04
**Severity:** Important
**Source:** code review of `feat/e7-ui`, item #9
**Call site:** `frontend/src/sse/useBatchStream.ts`

### What was missing
`useBatchStream` only listened for unnamed `message` events:
```ts
es.onmessage = (msg) => { ... };
```
E6 emits **named** events (`event: label-result\ndata: {...}`), which `EventSource.onmessage` does **not** receive. Result: the batch view would silently hang on "Connecting…" with zero events.

### Resolution

- Test commit `db26c3e` — RED test for named SSE framing covering `label-result` + `stream-end` dispatch, dedupe-by-label-id, and malformed-payload tolerance.
- Implementation commit `b3d3c1c` — `useBatchStream` switched from `es.onmessage` to `addEventListener('label-result', ...)` and `addEventListener('stream-end', ...)`. Payload is unwrapped from the E6 envelope shape `{batch_id, queue_position, envelope}`.
- Test stub fix `8ed6f13` — added `addEventListener` / `removeEventListener` no-ops to the `batch.test.tsx` smoke stub (Rule 1-3 inline fix dispatched by the T2 subagent).

### Scope note
- Only `label-result` and `stream-end` are wired in E7. `anomaly-advisory` and `override-applied` are **not** subscribed because no UI affordance renders them — see DEFER-1 and DEFER-3 below.

---

## 3. Deferred to post-E8

The following items were considered while closing #1 and #2 but require either UI affordances or backend routes not in scope for E7. They are tracked here as the canonical "knew about it, deferred it" landing pad.

### DEFER-1: Anomaly-advisory display in batch UI

`useBatchStream` does **not** subscribe to the `anomaly-advisory` SSE event because there is no UI surface for it in E7's batch page. When E8 (or post-E8 polish) adds an advisory banner / row, wire `addEventListener('anomaly-advisory', ...)` and surface the payload in `batch.tsx`.

### DEFER-2: `POST /batches/{batch_id}/anomalies/{advisory_id}/dismiss` endpoint

E6 ships an in-process `AnomalyDetector.dismiss()` method but **omitted the HTTP route** that the batch UI would need to call. Add the route + a minimal contract test before any UI dismiss button can be wired up. Pair with DEFER-1.

### DEFER-3: `override-applied` SSE consumer for cross-subscriber timeline updates

When one reviewer overrides a label, other open subscribers do not see the change — their batch view is stale. Wire `addEventListener('override-applied', ...)` in `useBatchStream` and patch the local envelope state when the event arrives. Out of E7 scope because the "multi-reviewer" UX is not yet exercised.

### DEFER-4: Explicit `applied_disposition` picker UX

Per **D-PE6-01**, `applied_disposition` is currently derived from the reason-code prefix. If reviewers ever need to choose a disposition independently of the reason code (e.g. flagging a `WARNING.*` finding as `fail` due to context not encoded in the rule), add an explicit dropdown to the `OverrideDrawer` and have the API consume the picked value rather than a derived one.

---

## How to discover this file later

- `git log --grep="post-e6"` finds commits referencing this followup
- `grep -rn "TODO(post-E6)" frontend/ docs/` finds inline breadcrumbs (now empty — both items closed)
- This file lives in `docs/followups/` — checked in as the canonical landing pad for "thing we knew about but couldn't fix yet"
