# TTB Label Verification — Prototype

> Reviewer-facing README — **draft, owned by E8 T9 to polish**. Internal spec docs (BRD/PRD/ARCHITECTURE/decisions) live under `docs/`; this file stands alone for a take-home reviewer.

A working proof-of-concept for AI-assisted TTB COLA label review. A reviewer drops a label image into the page; within roughly five seconds the system extracts the regulated fields, runs the federal rule pack against them, and returns a single disposition (`pass` / `fail` / `needs_review`) with citations and a full audit trail. A second screen handles batch submissions of up to ~300 labels with a streaming progress feed and a three-keystroke override path.

**Live demo:** <https://context31415-ttb-label.hf.space>
**Demo walkthrough (5 min):** TODO — Loom URL goes here once recorded (T16).

---

## Quick start

The hosted demo is the easiest way in — no install, no API key, cached responses for the demo fixtures.

For a local boot:

```bash
git clone https://github.com/AaronCarney/ttb-label-verification.git
cd ttb-label-verification
cp .env.example .env            # then fill OPENAI_API_KEY
uv sync                         # CPU profile; ~90s on a fast connection
uv run task demo                # uvicorn app.main:app on :8000
curl http://localhost:8000/healthz
```

For local on-prem-style boot (PaddleOCR + on-host LLM, no outbound calls):

```bash
uv sync --extra gpu             # adds paddlepaddle-gpu + torch (CUDA 12.6)
VISION_MODE=local uv run task demo
```

The first `/healthz` after a GPU-mode start adds ~30–45 s of model load; warm calls return in ≤2 s. See `DEMO-RUNBOOK.md` for the operator timeline used during the recorded walkthrough.

---

## Approach

**Deterministic core, AI on the seam.** The rule layer is pure Python over Pydantic models — every field-level finding traces back to a YAML rule with a reason code and a CFR citation. The vision and language models live behind narrow interfaces (one for OCR / field extraction, one for ambiguous-string adjudication). They produce typed observations that the rule engine consumes; they never decide a disposition on their own. This was a direct response to reviewer skepticism captured in the discovery interviews — every reject must cite a rule, not a vibe.

**Single chokepoint.** All disposition logic flows through one `Evaluator.evaluate()` call. That call orchestrates: image-quality gate → vision extraction → per-field rule evaluation → optional AI tiebreak on a single borderline rule (currently brand fuzzy-match) → confidence aggregation → audit assembly. Per-rule timeouts and a whole-eval budget keep the 5-second SLA from compounding.

**Substitutable model seams.** Vision has a `cloud` mode (GPT-4o on a region crop, OpenAI Structured Outputs with `strict:true`) and a `local` mode (PaddleOCR for OCR + a small in-process VLM). The orchestrator has the same shape — OpenAI Structured Outputs in production, an Anthropic skeleton kept compiling as a substitutability proof. Either side can be swapped without touching the rule layer.

**Audit-first envelope.** Every evaluation emits a deterministic `DispositionEnvelope` with field-level findings, per-rule traces, an input hash, an output hash, and an override list. Same input bytes → same output bytes; reproducible across processes.

**Reviewer-grade UI.** Server-rendered Jinja shell + a small React + TypeScript island. Keyboard-operable end to end (the override path is three keystrokes), high-contrast, no hidden gestures, axe-core zero AA violations gated in CI. The "73-year-old reviewer" benchmark from the Sarah interview is the calibration point.

**Streaming batch path.** A bounded queue + lookahead worker streams per-label results over server-sent events. The first label completes individually under the single-label budget; subsequent labels stream as they finish. A soft anomaly advisory fires when M-of-N consecutive labels share a failure reason — the early signal a real reviewer wants when an upstream artwork file is broken.

---

## Tools used

- **Language / runtime:** Python 3.12, Node 20 (build-time only).
- **Backend:** FastAPI, Pydantic v2, Jinja2, sse-starlette, `uv` for dependency management.
- **Frontend:** React 18 + TypeScript, Vite, USWDS color tokens, Radix UI primitives, vitest, axe-core, Playwright (sync API for keyboard / a11y tests).
- **Vision (cloud mode):** GPT-4o via OpenAI Structured Outputs (`strict:true`), called on a region crop.
- **Vision (local mode):** PaddleOCR for text + a small in-process VLM for low-confidence regions.
- **Orchestrator:** OpenAI Structured Outputs for the brand-match tiebreak; Anthropic adapter kept compiling but never invoked live.
- **Rule engine:** YAML rule pack + Pydantic-validated `RuleSet` + a small validator registry (one validator per rule type — equality, ABV-band, format-check, fuzzy-brand, contrast-ratio, layout-isolation, CPI-lookup).
- **Storage:** none persistent. In-memory app state for batches; demo response cache on disk under `demo/cached/`.
- **Testing:** pytest, pytest-asyncio, Playwright (sync), vitest, axe-core, vitest-axe.
- **Eval:** harness module with manifest + datasheet (Gebru et al. format); macro-F1, per-rule precision/recall, ECE, latency. Gated behind `DEV_MODE`.
- **Deployment:** Hugging Face Spaces, Docker SDK, `cpu-basic` tier. No custom domain or front-end proxy.

---

## Assumptions

1. **Prototype tier, not production.** No FedRAMP package, no ATO claim, no PII handling beyond what's needed to reproduce a defect, no integration with COLAs Online.
2. **Common-fields manifest only.** Wine (Part 4), distilled spirits (Part 5), malt beverages (Part 7), plus the universal Part 16 government health warning. Class-specific rules (age statements, geographical indications, appellations, sulfite/organic disclosures) are explicitly deferred.
3. **No real reviewer identity.** `reviewer_id` is a stringified UUID stub; production would bind to PIV-card or SAML federation against Treasury identity infrastructure.
4. **No persistence beyond the current process.** Batches and overrides live in `app.state`; restart loses them. A real deployment would back the queue with Postgres or Redis.
5. **Cloud mode is the default for the deployed demo.** Local mode is wired and tested but the deployed Space runs `cpu-basic` with `VISION_MODE=cloud`. The on-prem path is a substitutability proof, not the demo path.
6. **Demo cache shipped with the repo.** The six demo fixtures have pre-recorded LLM responses at `demo/cached/` so reviewers don't burn API budget walking the runbook. Cache is regenerated explicitly on snapshot-pin drift.
7. **First-label-individual semantics.** The first label of a batch is processed under the single-label latency budget; subsequent labels are subject to lookahead-windowed throughput.
8. **No authentication on the deployed URL.** Public read; the Space holds no production data.

---

## Trade-offs and limitations

- **Cold-start.** `cpu-basic` HF Spaces sleep aggressively; first request after idle can take 10–20 s. The runbook's `T-5` step pre-warms before the demo begins.
- **AI orchestrator scope is intentionally small.** The orchestrator only fires on `BRAND.NAME.NEEDS_REVIEW` from the fuzzy-brand validator. It is not a generalized agent that revisits other rules. Broader orchestrator coverage was out of scope for the seven-day window.
- **Vision model is not fine-tuned.** Cloud mode relies on GPT-4o's general OCR capability; local mode relies on PaddleOCR. A production deployment would benefit from fine-tuning on TTB label imagery, particularly for the ABV-region crop and government-warning legibility check.
- **Single-process app.** No worker pool, no queue across processes, no horizontal scaling. Adequate for the prototype tier; not for the 150k-applications-a-year production load.
- **Eval corpus is small.** Six single-label fixtures plus one 50-label batch fixture. Right-sized for a take-home eval, not a production calibration set; this is an explicit decision (D-023) not an oversight.
- **Anthropic adapter is a skeleton.** Type-checked, imported, and exercised in unit tests against a mock — but never run against the live Anthropic API. Kept as a substitutability proof per D-024.
- **Latency budget assumes warm models.** P50 ≤ 2.7 s and P99 ≤ 5.0 s are measured under warm-cache demo conditions. A cold cache against a live LLM blows past P99.
- **Bounded queue uses asyncio primitives, not a real broker.** Reactive Streams `request(n)` semantics are honored within the process; cross-process backpressure is not.

---

## Project structure

```
app/
  api/              FastAPI route handlers (/healthz, /labels, /batches, /overrides, /eval)
  schemas/          Pydantic v2 internal + wire-format types
  rules/            Validator registry; one module per rule family
  services/         Evaluator, orchestrator, vision extractors, batch worker, anomaly detector
  ui/
    templates/      Jinja2 page shells (single, batch)
    static/island/  Built React + Vite bundle (committed)
  config.py         Pydantic Settings — single source of truth for env vars
  deps.py           DI container; selects vision and orchestrator implementations
  main.py           App factory
frontend/           React + TypeScript island sources (built into app/ui/static/island/)
rules/              YAML rule pack — one file per rule, parsed by services/rule_engine
fixtures/           Six demo fixtures + their expected.json sidecars
demo/cached/        Pre-recorded LLM responses for the demo fixtures
eval/               Manifest + datasheet + harness + dashboard renderer
tests/              pytest + Playwright + vitest suites
docs/               BRD, PRD, ARCHITECTURE, decisions, epoch plans, runbook
```

---

## Testing

```bash
uv run pytest -v                 # full Python suite
cd frontend && pnpm test --run   # vitest + vitest-axe
cd frontend && pnpm build        # produces app/ui/static/island/ bundle (committed)
```

Per-epoch exit-gate suites land at `tests/test_e<N>_exit_gate.py`. Playwright tests run a real uvicorn instance against the built island; they are alphabetically clustered and run last in the suite to avoid event-loop pollution of the asyncio-based unit tests.

---

## Where to read more

If a reviewer wants to go deeper, the canonical specs live under `docs/`:

- `docs/BRD.md` — business requirements, stakeholder synthesis from the discovery interviews.
- `docs/PRD.md` — full functional and non-functional requirement set, wire schemas, AC matrix.
- `docs/ARCHITECTURE.md` — module boundaries, seam ownership, latency budget, deployment shape.
- `docs/03-decisions.md` — ADR index linking to D-001 through D-DEPLOY-004.
- `docs/operations.md` — log triage cookbook for the deployed demo.

These are *background*; this README is the entry point.
