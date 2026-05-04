# E7 Post-E6 Followups — L2 (v0.2 — post plan-review)

> **Parent:** [`ttb-label-verification-epoch-7-l2.md`](./ttb-label-verification-epoch-7-l2.md) §"Deferred items" + [`docs/followups/post-e6-merge.md`](../followups/post-e6-merge.md)
> **Tier:** L2 (tactical).
> **Branch:** `feat/e7-ui`.
> **Dependencies:** E6 surface available on `main` — `app/api/batches.py` (named-event SSE) + `app/api/overrides.py` (POST `/labels/{evaluation_id}/overrides`).

---

## 1. Goal

Close the two `TODO(post-E6)` breadcrumbs in `frontend/` against E6's actual contracts. Narrow scope to what E7's UI surface actually consumes.

After this plan: `feat/e7-ui` is self-consistent against E6 on `main`, the island bundle is rebuilt, and the branch is mergeable.

## 2. Scope decisions (locked, post plan-review)

- **D-PE6-01** — `applied_disposition` derived from reason_code prefix: `WARNING.*` → `needs_review`; `FAIL.*` → `fail`; `PASS.*` → `pass`. Required server-side; UI does not capture it explicitly.
- **D-PE6-02** — T1 test uses `page.route()` to stub the POST. Single-label demo flow cannot end-to-end persist (E6 endpoint requires the label to be in an in-flight batch's `results` map; single-label `/labels` POST doesn't add to any batch). Test verifies wire shape + LiveRegion + Toast paths, not server persistence. Documented inline at the call site.
- **D-PE6-03** — T2 wires only `label-result` + `stream-end`. **Skip** `anomaly-advisory` and `override-applied` — E7 UI doesn't render advisories or consume cross-subscriber audit updates. Inline note documents the deferral.
- **D-PE6-04** — Anomaly dismiss endpoint (`POST /batches/{batch_id}/anomalies/{advisory_id}/dismiss`) deferred. E7 UI doesn't surface advisory display or dismiss affordance. Lands as a post-E8 followup if/when the UI surfaces advisories.

## 3. Locked surface

**Owned (this plan can write to):**
- `frontend/src/single.tsx`
- `frontend/src/sse/useBatchStream.ts`
- `frontend/src/sse/useBatchStream.test.ts` (NEW or extended)
- `tests/test_keyboard_model.py` (extend with override-POST shape assertion)
- `app/ui/static/island/{single,batch}.{js,css,map}` (regenerated bundle in T3)
- `docs/followups/post-e6-merge.md` (closeout edits)

**Forbidden (read-only):**
- `app/services/**`, `app/api/**`, `app/batch/**` (E5/E6 territory)
- `frontend/src/components/**` not in the owned list

## 4. Task graph

```
Wave 1 (2 ‖):  T1 (override-POST wiring)   T2 (SSE named-event listeners)
Wave 2 (1):    T3 (final validation: bundle rebuild + full pytest + frontend tests + followup closeout)
```

Wave 1 tasks own disjoint files.

---

## 5. Tasks

### T1 — Wire OverrideDrawer.onSubmit to POST `/labels/{evaluation_id}/overrides`

**Label:** TDD
**Owner files:** `frontend/src/single.tsx`, `tests/test_keyboard_model.py`

**Authoritative E6 schema** (from `app/api/overrides.py:55-61`):
```python
class OverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field_name: str | None = None
    applied_disposition: Literal["pass", "fail", "needs_review"]
    reason_code: str
    justification_text: str | None = None
```
- Path: `POST /labels/{evaluation_id}/overrides`
- `evaluation_id` is path-only; do **not** include in body (`extra="forbid"` rejects).
- `reviewer_id` is server-generated; do **not** include in body.
- `applied_disposition` REQUIRED — derive from reason_code prefix per D-PE6-01.

**Recipe.**

1. **RED.** Extend `tests/test_keyboard_model.py`:

   ```python
   def test_three_keystroke_override_posts_to_endpoint(page: Page, live_server_url: str) -> None:
       envelope = json.loads(FIXTURE.read_text())
       captured: dict = {}
       def _route(route, request):
           captured["url"] = request.url
           captured["method"] = request.method
           captured["body"] = request.post_data_json
           route.fulfill(status=200, content_type="application/json", body=json.dumps({
               "field_name": None,
               "original_disposition": "pass",
               "applied_disposition": "needs_review",
               "reason_code": captured["body"]["reason_code"],
               "justification_text": captured["body"].get("justification_text"),
               "reviewer_id": "session-test",
               "timestamp": "2026-05-04T00:00:00Z",
           }))
       page.route(f"**/labels/*/overrides", _route)

       page.add_init_script(script=f"""
         window.addEventListener('DOMContentLoaded', () => {{
           const tag = document.createElement('script');
           tag.id = 'envelope';
           tag.type = 'application/json';
           tag.textContent = {json.dumps(json.dumps(envelope))};
           document.body.appendChild(tag);
         }});
       """)
       page.goto(f"{live_server_url}/")
       page.wait_for_selector('[data-mounted="true"]', timeout=5000)

       page.keyboard.press("o")
       page.wait_for_selector('[role="dialog"]', timeout=2000)
       page.keyboard.type("w")
       page.keyboard.press("Enter")
       page.wait_for_selector(
           'text=/Override saved: WARNING\\.STYLE\\.HEADING_NOT_BOLD_CAPS/',
           timeout=2000,
       )
       assert captured["method"] == "POST"
       assert f"/labels/{envelope['evaluation_id']}/overrides" in captured["url"]
       body = captured["body"]
       assert body["reason_code"] == "WARNING.STYLE.HEADING_NOT_BOLD_CAPS"
       assert body["applied_disposition"] == "needs_review"
       assert body["field_name"] is None
       assert "evaluation_id" not in body  # path-only
       assert "reviewer_id" not in body    # server-generated
   ```

   And a failure-path test:
   ```python
   def test_override_failure_path_surfaces_toast(page: Page, live_server_url: str) -> None:
       # ... same envelope load + init script ...
       def _route_422(route):
           route.fulfill(status=422, content_type="application/json",
                         body=json.dumps({"detail": "reason_code 'WARNING.STYLE.HEADING_NOT_BOLD_CAPS' is not in the loaded registry"}))
       page.route(f"**/labels/*/overrides", _route_422)
       # ... goto, keystrokes O w ENTER ...
       page.wait_for_selector('[role="status"]', timeout=2000)  # Toast role=status
       assert page.locator('[role="dialog"]').is_visible()  # drawer stays open
       assert "not in the loaded registry" in page.locator('[role="status"]').inner_text()
   ```

   The existing `test_three_keystroke_override` (no-stub LiveRegion-only test) stays — it asserts the UX still works when no route is intercepted (browser fetch fails silently → catch branch fires Toast with network error). Update its assertion accordingly OR keep it as the "happy LiveRegion path" by also stubbing 200. Pick the simpler: **keep the existing test as-is, add the two new tests above.** The existing test will start failing once we add the fetch — fix it by adding a 200-stub `page.route()` to it.

2. **GREEN.** In `frontend/src/single.tsx`, replace the `onSubmit` block at the `TODO(post-E6)` marker:

   ```tsx
   // Add at top of file (after existing imports):
   import { Toast } from "./components/Toast";

   // Inside the component, with other state:
   const [toast, setToast] = React.useState<{kind: "error" | "success", message: string} | null>(null);

   // Helper (file-local):
   function _disposition_for(code: string): "pass" | "fail" | "needs_review" {
     if (code.startsWith("FAIL.")) return "fail";
     if (code.startsWith("PASS.")) return "pass";
     return "needs_review";  // WARNING.* and any unprefixed code default to needs_review
   }

   // Replace the onSubmit handler:
   onSubmit={async (p) => {
     const body = {
       field_name: null,
       applied_disposition: _disposition_for(p.reasonCode),
       reason_code: p.reasonCode,
       justification_text: p.justification || null,
     };
     try {
       const res = await fetch(
         `/labels/${encodeURIComponent(envelope.evaluation_id)}/overrides`,
         { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body) },
       );
       if (!res.ok) {
         const errBody = await res.json().catch(() => ({detail: "Override request failed"}));
         const detail = Array.isArray(errBody.detail)
           ? errBody.detail.map((d: {msg?: string}) => d.msg).filter(Boolean).join("; ")
           : (errBody.detail ?? "Override request failed");
         setToast({kind: "error", message: detail});
         return;
       }
       setAnnouncement(`Override saved: ${p.reasonCode}`);
       setOverrideOpen(false);
     } catch {
       setToast({kind: "error", message: "Network error — override not saved"});
     }
   }}
   ```

   Render `Toast` conditionally near `LiveRegion`:
   ```tsx
   {toast && (
     <Toast
       message={toast.message}
       onDismiss={() => setToast(null)}
     />
   )}
   ```

   Drop the entire `TODO(post-E6):` comment block. Add a one-line note immediately above the handler:
   ```tsx
   // Single-label demo flow: this POST 404s against the real E6 endpoint
   // because the label is not in any in-flight batch's results map.
   // Tests intercept via page.route(). See docs/followups/post-e6-merge.md.
   ```

3. **REFACTOR.** If the handler exceeds ~25 lines, extract `submitOverride(payload, evaluationId): Promise<{ok: boolean, error?: string}>` to a sibling helper.

4. **Commit cadence.** Two commits expected:
   - `test(e7): override POST wiring + 422 failure path (post-E6 #1)`
   - `feat(e7): wire OverrideDrawer.onSubmit to POST /overrides (FR-803)`

5. **Validation grep.** `grep -n "TODO(post-E6)" frontend/src/single.tsx` returns nothing.

---

### T2 — Switch `useBatchStream` to named-event listener (label-result only)

**Label:** TDD
**Owner files:** `frontend/src/sse/useBatchStream.ts`, `frontend/src/sse/useBatchStream.test.ts`

**Authoritative E6 wire** (from `app/batch/worker.py` and `app/api/batches.py:117-118`):
- Worker emits these events: `label-result` (per-label disposition), `anomaly-advisory` (M-of-N detector trip), `stream-end` (terminal).
- Override endpoint emits: `override-applied` (audit trail mutation).
- `label-result` data shape: `{batch_id: str, queue_position: int, envelope: DispositionEnvelope}` — wrapped envelope, NOT bare `BatchSSEEvent`.
- Other events have different shapes.

**D-PE6-03 consequence:** This task wires only `label-result` + `stream-end`. The other two are out of scope for E7's UI.

**Recipe.**

1. **RED.** Create `frontend/src/sse/useBatchStream.test.ts`. Use a fake `EventSource` (the existing convention; check sibling tests). Tests:
   - **label-result event drives push** — fire one named `label-result` event with `{batch_id, queue_position, envelope: <DispositionEnvelope>}`; assert `state.events[0].label_ref === envelope.label_ref`, `state.events[0].batch_id === <batch_id>`, `state.events[0].queue_position === <pos>`.
   - **stream-end closes the connection** — fire one `label-result`, then `stream-end`; assert subsequent `label-result` events are ignored (EventSource closed).
   - **dedupe still works** — fire two `label-result` events with same `envelope.label_ref`; assert `state.events.length === 1`.
   - **malformed payload sets error** — fire `label-result` with non-JSON `data`; assert `state.error === "Malformed SSE payload"`.

2. **GREEN.** Rewrite the `useEffect` body:

   ```ts
   import * as React from "react";
   import type { DispositionEnvelope } from "../types/envelopes";
   import type { BatchSSEEvent } from "../types/sse";

   // ... existing reducer, state types unchanged ...

   // E6 emits named SSE events per ARCH §5.2: label-result, anomaly-advisory,
   // stream-end (worker), and override-applied (override endpoint).
   // E7 consumes only label-result + stream-end; the others are not surfaced
   // in the current UI (see docs/followups/post-e6-merge.md, D-PE6-03).
   React.useEffect(() => {
     if (!batchId) return;
     const url = `/batches/${encodeURIComponent(batchId)}/stream`;
     const es = new EventSource(url);

     const _onLabelResult = (msg: MessageEvent) => {
       try {
         const wrapped = JSON.parse(msg.data as string) as {
           batch_id: string;
           queue_position: number;
           envelope: DispositionEnvelope;
         };
         const flat: BatchSSEEvent = {
           ...wrapped.envelope,
           batch_id: wrapped.batch_id,
           queue_position: wrapped.queue_position,
         };
         dispatch({type: "push", event: flat});
       } catch {
         dispatch({type: "error", message: "Malformed SSE payload"});
       }
     };
     const _onStreamEnd = () => es.close();

     es.addEventListener("label-result", _onLabelResult);
     es.addEventListener("stream-end", _onStreamEnd);
     es.onerror = () => dispatch({type: "error", message: "SSE connection error"});

     return () => {
       es.removeEventListener("label-result", _onLabelResult);
       es.removeEventListener("stream-end", _onStreamEnd);
       es.close();
     };
   }, [batchId]);
   ```

   Drop the `FRAMING ASSUMPTION` and `TODO(post-E6)` comment blocks entirely. The new comment block above the `useEffect` documents the contract.

3. **REFACTOR.** Optional — extract `_unwrapLabelResult(data: string): BatchSSEEvent | null` if it improves test coverage clarity.

4. **No fixture edit.** `tests/fixtures/envelopes/batch/05-batch-of-50-events.jsonl` stays bare-JSON; tests synthesize the named-event wrapper in JS via the fake EventSource. Lock this decision.

5. **Commit cadence.** Two commits:
   - `test(e7): named-event SSE listeners — label-result + stream-end (post-E6 #2)`
   - `fix(e7): subscribe useBatchStream to named SSE events (label-result framing)`

6. **Validation grep.** `grep -n "TODO(post-E6)" frontend/src/sse/useBatchStream.ts` returns nothing. `grep -n "FRAMING ASSUMPTION" frontend/src/sse/useBatchStream.ts` returns nothing.

---

### T3 — Final validation + bundle rebuild + followup closeout

**Label:** skip-tdd (mechanical)
**Owner files:** `app/ui/static/island/{single,batch}.{js,css,map}`, `docs/followups/post-e6-merge.md`

**Recipe.**

1. `cd /home/context/olorin/projects/takehome/frontend && pnpm install --frozen-lockfile && pnpm build`. If `tsc -b` fails, fix typing inline (Rule 1-3).
2. `cd /home/context/olorin/projects/takehome && git add app/ui/static/island/`. Verify diff is `single.{js,css,map}` + `batch.{js,css,map}`.
3. `uv run --python 3.12 pytest -x -q tests/test_island_build_clean.py` — clean-diff gate must pass.
4. `cd frontend && pnpm test` — all hook + component tests green, including new T2 tests.
5. `cd .. && uv run --python 3.12 pytest -x -q` — full Python suite green, including new T1 tests.
6. Update `docs/followups/post-e6-merge.md`:
   - Mark items 1 & 2 as **Resolved** with commit hashes.
   - Add a new **Item 3 (deferred to post-E8)** documenting:
     - Anomaly-advisory display in batch UI
     - `POST /batches/{batch_id}/anomalies/{advisory_id}/dismiss` endpoint (E6 omitted; in-process `dismiss()` exists)
     - `override-applied` SSE consumer for cross-subscriber timeline updates
     - `applied_disposition` UX — currently derived from reason_code prefix (D-PE6-01); a real disposition picker may be needed if reviewers want override semantics independent of the code chosen
7. Commit: `chore(e7): rebuild island bundle + close post-E6 followups`.

## 6. Exit gate

- `grep -rn "TODO(post-E6)" frontend/` → zero hits.
- `grep -rn "FRAMING ASSUMPTION" frontend/` → zero hits.
- Full Python suite passes.
- `pnpm test` passes.
- `pnpm build && git diff --exit-code app/ui/static/island/` returns 0.
- `feat/e7-ui` is mergeable into `main` (no conflicts on E6 surface — verified by `git rebase --dry-run main`).

## 7. Total commits expected

- T1: 2
- T2: 2
- T3: 1
- **Total: 5 commits on `feat/e7-ui`**.
