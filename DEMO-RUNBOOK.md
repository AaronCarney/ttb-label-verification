# Demo Runbook

Operator timeline for the 5-minute recorded walkthrough (PRD §10.2).

> **Status note.** This runbook assumes E5 (Application Service), E6 (batch + override), and E7 (UI) are all on `main`. The HF Space provisioning section and recording protocol live below.

---

## T-30 minutes — environment check

```bash
# 1. Deployment reachable with valid TLS
curl -I https://context31415-ttb-label.hf.space/healthz
# Expect: HTTP/2 200 with valid HF-issued cert (no --insecure flag)

# 2. UI shell renders
curl -fsSL https://context31415-ttb-label.hf.space/ | head -20
# Expect: HTML, includes the island bundle script tag

# 3. API credentials valid
curl https://context31415-ttb-label.hf.space/healthz | jq '.mode.orchestrator'
# Expect: "openai"

# 4. Repo clean
gh release list && git status
# Expect: working tree clean, latest release tagged

# 5. Envelope snapshots fresh (regression baseline)
uv run --python 3.12 python scripts/snapshot_demo_envelopes.py --canonicalize-only
git diff --quiet demo/cached/
# Expect: no diff
```

## T-5 minutes — pre-warm

```bash
# Sentinel pipeline against fixture-01
curl https://context31415-ttb-label.hf.space/healthz
# Expect: 200 within 2 s (vision model + LLM client warm)
```

## T-1 minute — dry run

Open https://context31415-ttb-label.hf.space in a fresh browser tab. Drop fixture-01 onto the upload area. Confirm a `pass` disposition appears within 5 s.

## T-0 — begin recording

Six-stage path per PRD §10.2:

1. **Stage 1 — Upload fixture-01** (clean spirits). Disposition: `pass`. Show the citation chips backing each rule.
2. **Stage 2 — Upload fixture-02** (STONE'S THROW Bourbon). Disposition: `pass`. Narrate the apostrophe-aware brand normalization (PRD-deferred §3.3) — orchestrator's brand_disambig task fires.
3. **Stage 3 — Upload fixture-03** (title-case warning). Disposition: `fail` on the case-sensitivity rule. Show the reason code surfaced in `audit_trail.per_rule_trace`.
4. **Stage 4 — Upload fixture-04** (low-res / glare). Disposition: `needs_review`. Show the legibility short-circuit prompting re-upload.
5. **Stage 5 — Upload fixture-05** (50-label batch, post-merge T15). Show the SSE stream, queue position, and lookahead progress. Trigger the M-of-N anomaly advisory by submitting same-reason fails.
6. **Stage 6 — Override on fixture-06** (ABV out-of-tolerance). Three-keystroke override demo (AC-FR-803). Show the audit-trail entry with reason code + reviewer ID + timestamp.

Bonus (deployed but cut from recording for time): fixture-07 borderline-band `needs_review` with the medium-confidence band surfaced in `disposition_confidence`.

## Failure recovery

| Scenario | Recovery |
|---|---|
| Network drops mid-batch | SSE auto-reconnect from `current_index`; reviewer continues |
| LLM timeout | The Evaluator's whole-eval timeout (5 s) routes to `needs_review` with `ENGINE.SLA.TIMEOUT` reason code. Cached envelope baselines under `demo/cached/` document expected dispositions if the live demo needs a fallback narrative. |
| OCR low-confidence on a demo image | Switch to fixture-01 as fallback; document image quality is a separate FR-700 demo |
| HF Space cold-start exceeds 5 s | T-5 pre-warm absorbs this; if it recurs mid-demo, point at the `/healthz` curl in T-30 as evidence the deploy is healthy |
| Cache stale relative to active LLM_MODEL_SNAPSHOT | `uv run --python 3.12 python scripts/snapshot_demo_envelopes.py` (requires OPENAI_API_KEY); commit the diff |

---

## Initial deployment setup (one-time, executed 2026-05-04)

1. **HF Space create** — `hf repos create Context31415/ttb-label --type space --space-sdk docker --public`
2. **Push** — `git remote add hf https://huggingface.co/spaces/Context31415/ttb-label && git push hf main`
3. **Variables** (set via API at provisioning time; verify in HF Space → Settings → Variables and secrets):
   - `ORCHESTRATOR_BACKEND` = `openai`
   - `LLM_MODEL_SNAPSHOT` = `gpt-4o-2024-08-06`
   - `LOOKAHEAD_K` = `3`
   - `PROMPT_VERSION` = `v1`
   - `VISION_MODE` = `cloud` (cpu-basic has no GPU; `auto` would degrade)
   - `DEMO_CACHE` = `1`
   - `DEV_MODE` — leave unset for the public URL
4. **Secrets** (UI-only — Space → Settings → Variables and secrets → New secret):
   - `OPENAI_API_KEY`
5. **Custom domain** — **NOT USED.** HF custom domains require Pro ($9/mo). Per **D-DEPLOY-001** (decisions log), the demo uses the default `https://context31415-ttb-label.hf.space` URL; vanity `ttb.aaroncarney.me` is deferred to pilot phase. Cloudflare CNAME stays dangling — harmless.
6. **Verify** — three smoke calls:
   - `curl -I https://context31415-ttb-label.hf.space/healthz` → 200 with valid HF-issued cert
   - `curl -I https://context31415-ttb-label.hf.space/` → 200 (UI shell)
   - `curl -I https://context31415-ttb-label.hf.space/static/island/single.js` → 200 (asset serving)
