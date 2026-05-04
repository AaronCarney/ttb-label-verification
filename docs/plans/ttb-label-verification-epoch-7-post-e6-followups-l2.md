# E7 Post-E6 Followups — L2

> **Parent:** [`ttb-label-verification-epoch-7-l2.md`](./ttb-label-verification-epoch-7-l2.md) §"Deferred items" + [`docs/followups/post-e6-merge.md`](../followups/post-e6-merge.md)
> **Tier:** L2 (tactical).
> **Branch:** `feat/e7-ui`.
> **Dependencies:** E6 surface on `main` — `app/api/batches.py` (named-event SSE) + `app/api/overrides.py` (POST `/labels/{id}/overrides`). Confirmed landed at `main` HEAD `d27a8c2`.

---

## 1. Goal

Close the two `TODO(post-E6)` breadcrumbs in `frontend/`. Both wire E7's island against E6's actual contracts (formerly stubbed because E6 ran in a parallel session and hadn't landed when E7 froze).

After this plan: `feat/e7-ui` is fully self-consistent against the E6 surface on `main`, the island bundle is rebuilt, and the branch is mergeable.

---

## 2. Locked surface

**Owned (this plan can write to):**
- `frontend/src/single.tsx`
- `frontend/src/sse/useBatchStream.ts`
- `frontend/src/sse/useBatchStream.test.ts` (NEW or extended)
- `tests/test_keyboard_model.py` (extend with override-POST assertion)
- `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl` (reformat to named-event records, only if currently bare-JSON)
- `app/ui/static/island/{single,batch}.{js,css,map}` (regenerated bundle in Wave 2)
- `docs/followups/post-e6-merge.md` (close-out edits — mark items resolved)

**Forbidden (read-only):**
- `app/services/**`, `app/api/**`, `app/batch/**` (E5/E6 territory — already on `main`)
- Any other `frontend/src/components/**` not in the owned list

---

## 3. Task graph

```
Wave 1 (2 ‖):  T1 (override-POST wiring)   T2 (SSE named-event listeners)
Wave 2 (1):    T3 (final validation: bundle rebuild + full pytest + frontend tests)
```

Wave 1 tasks are mutually independent — disjoint file ownership, no shared imports.

---

## 4. Tasks

### T1 — Wire OverrideDrawer.onSubmit to POST `/labels/{id}/overrides`

**Label:** TDD
**Owner files:** `frontend/src/single.tsx`, `tests/test_keyboard_model.py`

**Context.** E6's endpoint is `POST /labels/{evaluation_id}/overrides` (commit `04fba48`, file `app/api/overrides.py`). Request body is `OverrideEntry`-shaped: `{evaluation_id, field_name|null, reason_code, justification_text, reviewer_id}`. Response on 2xx returns the updated audit envelope. On 4xx (registry validation failure) the body is `{detail: "<message>"}`; on 409 (collision) similarly. AC-FR-801 requires the override is durably recorded server-side; AC-FR-507 requires LiveRegion announces locally.

**Recipe.**

1. **RED.** Extend `tests/test_keyboard_model.py` with an `O → w → ENTER` flow that:
   - Stubs the route via `page.route('/labels/*/overrides', ...)` to capture the POST.
   - Asserts (a) one POST landed, (b) request body has `reason_code`, `justification_text`, `evaluation_id`, (c) LiveRegion text contains "Override saved", (d) drawer closes after submit.
   - Add a parallel test for failure path: stub returns 422; assert Toast appears with the error and drawer stays open.

2. **GREEN.** Replace the body of `OverrideDrawer.onSubmit` in `frontend/src/single.tsx:104-110` with an async handler:
   ```tsx
   onSubmit={async (p) => {
     try {
       const res = await fetch(`/labels/${encodeURIComponent(envelope.evaluation_id)}/overrides`, {
         method: "POST",
         headers: {"Content-Type": "application/json"},
         body: JSON.stringify({
           evaluation_id: envelope.evaluation_id,
           field_name: null,
           reason_code: p.reasonCode,
           justification_text: p.justification,
           reviewer_id: "prototype",
         }),
       });
       if (!res.ok) {
         const body = await res.json().catch(() => ({detail: "Override request failed"}));
         setToast({kind: "error", message: body.detail ?? "Override request failed"});
         return;
       }
       setAnnouncement(`Override saved: ${p.reasonCode}`);
       setOverrideOpen(false);
     } catch {
       setToast({kind: "error", message: "Network error — override not saved"});
     }
   }}
   ```
   Remove the `TODO(post-E6)` comment. If `setToast` is not yet wired in this file, add a minimal Toast slot bound to existing `Toast` component (already imported at T12). Keep `setAnnouncement` + `setOverrideOpen` exactly as they were.

3. **REFACTOR.** If the handler is now >25 lines, extract `submitOverride(payload, evaluationId): Promise<{ok: boolean, error?: string}>` to a sibling helper. Keep the handler dumb — it only branches on the helper's result.

4. **Commit per cycle.** Two commits expected:
   - `test(e7): override POST wiring + failure path (post-E6 #1)`
   - `feat(e7): wire OverrideDrawer.onSubmit to POST /overrides (FR-803)`

5. **Validation grep.** No new `TODO(post-E6)` markers remain in `frontend/src/single.tsx`. The `// TODO(post-E6): POST` line at L106 is gone.

---

### T2 — Switch `useBatchStream` to named-event listeners

**Label:** TDD
**Owner files:** `frontend/src/sse/useBatchStream.ts`, `frontend/src/sse/useBatchStream.test.ts`, `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl`

**Context.** E6 emits named SSE events: `app/api/batches.py:118` does `yield {"event": evt["event"], "data": evt["data"]}`. `EventSource.onmessage` does NOT fire on named events — only `addEventListener('<name>', ...)` does. Worker emits three event types per ARCH §5.2: `label-update`, `anomaly`, `stream-end`. The hook must subscribe to each.

**Recipe.**

1. **RED.** Add `frontend/src/sse/useBatchStream.test.ts` (or extend if it exists) with three tests using a fake `EventSource`:
   - Named `label-update` event triggers `push` action.
   - Named `anomaly` event surfaces in state.
   - Named `stream-end` event closes the connection (no more events accepted).
   - Bonus: dedupe still works on duplicate `label_ref` across events.

2. **GREEN.** Rewrite the `useEffect` body to register listeners per event name:
   ```ts
   const es = new EventSource(url);
   const _onPayload = (msg: MessageEvent) => {
     try {
       const parsed = JSON.parse(msg.data as string) as BatchSSEEvent;
       dispatch({type: "push", event: parsed});
     } catch {
       dispatch({type: "error", message: "Malformed SSE payload"});
     }
   };
   es.addEventListener("label-update", _onPayload);
   es.addEventListener("anomaly", _onPayload);
   es.addEventListener("stream-end", () => es.close());
   es.onerror = () => dispatch({type: "error", message: "SSE connection error"});
   return () => {
     es.removeEventListener("label-update", _onPayload);
     es.removeEventListener("anomaly", _onPayload);
     es.close();
   };
   ```
   Drop `es.onmessage` entirely (verified E6 emits named-only). Remove the `TODO(post-E6)` block + the `FRAMING ASSUMPTION` comment, replacing with one short note: `// E6 emits named events per ARCH §5.2: label-update, anomaly, stream-end.`

3. **REFACTOR.** If event names ever expand, prefer a constant `_BATCH_EVENT_NAMES = ["label-update", "anomaly"] as const` and iterate. Optional — only if it doesn't bloat.

4. **Fixture audit.** Read `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl`. If each line is bare JSON (current state), prepend `event: label-update` framing OR document inline that the JSONL is a payload-only fixture and the test harness wraps it. The simpler path: keep JSONL bare-JSON and have the test fake `EventSource` synthesize the named-event wrapper. Pick whichever keeps the diff smaller.

5. **Commit per cycle.** Expected commits:
   - `test(e7): named-event SSE listeners — label-update, anomaly, stream-end (post-E6 #2)`
   - `fix(e7): subscribe useBatchStream to named SSE events`
   - (Optional) `chore(e7): batch fixture — clarify framing convention`

6. **Validation grep.** No `TODO(post-E6)` remains in `frontend/src/sse/useBatchStream.ts`.

---

### T3 — Final validation: bundle rebuild + full suite

**Label:** skip-tdd (mechanical)
**Owner files:** `app/ui/static/island/{single,batch}.{js,css,map}`, `docs/followups/post-e6-merge.md`

**Recipe.**

1. `cd /home/context/olorin/projects/takehome/frontend && pnpm install --frozen-lockfile && pnpm build`. Bundle MUST succeed; if `tsc -b` fails, fix typing inline (Rule 1-3 auto-fix).
2. `cd /home/context/olorin/projects/takehome && git add app/ui/static/island/`. Verify `git diff --cached --stat` shows expected `single.{js,css,map}` + `batch.{js,css,map}` changes.
3. `cd /home/context/olorin/projects/takehome && uv run --python 3.12 pytest -x -q tests/test_island_build_clean.py`. Must pass — clean-diff gate.
4. Run `cd /home/context/olorin/projects/takehome/frontend && pnpm test`. Every component / hook test green, including new T2 hook tests.
5. Run `cd /home/context/olorin/projects/takehome && uv run --python 3.12 pytest -x -q`. Full Python suite green.
6. Mark `docs/followups/post-e6-merge.md` items 1+2 as resolved (add a `**Status:** Resolved YYYY-MM-DD on commit <hash>` line under each item header). One closeout commit.
7. Commit: `chore(e7): rebuild island bundle + close post-E6 followups`.

---

## 5. Exit gate

- `grep -rn "TODO(post-E6)" frontend/ docs/` → zero hits in `frontend/src/**`. (One historical mention in `docs/followups/post-e6-merge.md` is acceptable as it documents the closed item.)
- Full Python suite passes.
- `pnpm test` passes.
- `pnpm build && git diff --exit-code app/ui/static/island/` returns 0.
- Branch `feat/e7-ui` is mergeable into `main` (no conflicts on E6 surface — verified by attempting a dry-run rebase).

---

## 6. Total commits expected

- T1: 2
- T2: 2–3
- T3: 1
- **Total: 5–6 commits on `feat/e7-ui`**.
