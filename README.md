---
title: TTB Label Verification
emoji: 🍷
colorFrom: indigo
colorTo: red
sdk: docker
app_port: 8000
hardware: cpu-basic
pinned: false
---

# TTB Label Verification (prototype)

A reviewer drops an alcohol-label image into the page; in about five seconds the system extracts the regulated fields, checks them against the federal rule pack, and returns a single verdict — `pass`, `fail`, or `needs_review` — with a citation for every check. A second screen handles batch uploads of up to a few hundred labels with a streaming progress feed and a three-keystroke override.

> **Live demo:** https://context31415-ttb-label.hf.space — the seven demo fixtures are loaded; drop them onto the upload area or paste their paths.

## The problem in one screen

TTB reviews ~150,000 COLA applications a year with ~47 specialists. Sarah (Deputy Director) describes her team as "drowning in routine stuff" — eyeball-matching brand, ABV, net contents, and the government warning between the application and the artwork before any judgment-laden review begins. A previous vendor pilot died because it took 30–40 seconds per label; in her words, *"if we can't get results back in about 5 seconds, nobody's going to use it."*

The brief is to demonstrate, in a standalone web prototype, that AI-assisted review can take the routine field-matching off Sarah's queue without putting the regulatory verdict in the model's hands. No COLAs Online integration, no production claims, no persistent storage.

## Core requirements — what's actually built

The seven required fields are all extracted, checked, and cited: brand name, class/type, ABV, net contents, bottler/importer name and address, country of origin (imports), and the Part 16 government health warning. The warning check enforces the verbatim §16.21 text, the all-caps-and-bold heading per §16.22(a)(2), the contrasting background, and the type-size and CPI minimums. ABV uses the regulatory tolerance (±0.3 pp for spirits; ±1.0/1.5 pp for wine; ±0.3 pp with 0.5% floor for malt), not strict equality. Brand match goes through normalized exact (Stage A) and Jaro-Winkler fuzzy (Stage B). Batch upload is wired through `POST /batches` with SSE streaming. Override is one screen, three keystrokes, audited.

## The four architectural choices

**1. The AI never decides — it just helps explain.** Every `pass` / `fail` / `needs_review` verdict comes from deterministic Python reading a YAML rule pack. The language model only paraphrases template reasoning and reconciles ambiguous OCR reads. If the model goes down or returns garbage, the system emits `needs_review` with a structured reason — it never silently flips to `pass`. This is a posture choice: a regulator can defend a verdict that traces to a rule and a CFR citation. They cannot defend "the model said so."

**2. Rules live in YAML, not Python.** Each regulation is a row in a YAML file with the CFR citation, the validator name, and the parameters. Updating the spirits ABV tolerance or adding a class-of-product rule is a config change and a test, not a code change. Python only contains the validators these rules call by name. This is what makes the rule pack auditable by a non-programmer reviewer and what keeps "rules as data" from being marketing copy.

**3. The two AI dependencies are swappable.** OCR (vision) and the language model both sit behind a small project-owned interface. The cloud path is GPT-4o with structured outputs; the on-prem path is PaddleOCR plus the same model. A second LLM backend (Anthropic) is wired as a working skeleton to prove the seam — it is not run live for cost reasons. Switching is an environment-variable flip, not a refactor. This was an explicit response to Marcus's "our network blocks a lot of outbound traffic" — the architecture cannot be cloud-only.

**4. Batch reuses the single-label engine, on the same five-second budget.** I refused to split into "fast single, slow batch" — that produces two code paths, two SLAs, and two sets of bugs. The batch worker runs the same per-label evaluator, with a small lookahead (default 3) that pre-fetches the next labels while the reviewer is reading the current one. The first label of a batch is processed individually so the reviewer feels the same latency they would feel from `POST /labels`. The brief asked for batch *and* the 5s SLA; I treated them as the same requirement.

## Stakeholder asks, point by point

- **Sarah's 5 seconds.** Single-label P50 is ~2.7s, P99 is ≤5s. The whole-evaluation timeout is enforced (`ENGINE.SLA.TIMEOUT`); the per-rule timeout is 250ms. Demo runs hit `/healthz` at T-5 minutes to pre-warm the model client.
- **Sarah's "my 73yo mother".** The UI is a Jinja2 shell with a single React island, USWDS color tokens, semantic HTML, axe-core in CI, no ARIA acrobatics. Reflows at 320 CSS px. Honors `prefers-reduced-motion`. Disposition pill uses color *and* shape *and* text — no color-only signals.
- **Sarah's batch from Janet in Seattle.** `POST /batches` accepts up to a few hundred labels, streams per-label results over SSE, surfaces an M-of-N anomaly advisory when ≥3 same-reason failures cluster, and lets a mid-batch override land without stopping the queue.
- **Dave's STONE'S THROW.** Brand match has Stage A normalization (uppercase, strip apostrophes/punctuation) before any fuzzy comparison. `STONE'S THROW` matches `Stone's Throw` as a `pass`, not a `needs_review`. Fixture-02 is exactly this case.
- **Jenny's warning-statement exactness.** The warning rule is the deepest one in the pack: verbatim §16.21 text match, all-caps + bold detection on the heading, contrasting background, type-size minima, CPI maximum, separate-and-apart placement. Title-case is a `fail`, not a soft warning. Fixture-03 is exactly this case.
- **Jenny's bad photos.** BRISQUE/NIQE quality gates emit `WARNING.LEGIBILITY.*` reason codes; the disposition is `needs_review` with a structured "needs better photo" hint, not a silent `fail`. Fixture-04 is exactly this case.
- **Marcus's network reality.** No persistent storage, no DB, no Redis. Audit/state is in-memory and session-scoped. Cloud and on-prem inference paths share an interface so the on-prem path can be swapped in for a firewalled deployment without touching anything else.

## Code organization

The substitutability boundaries are visible at the directory level: `app/vision/{base.py, cloud.py, local.py}`, `app/orchestrator/{base.py, openai_strict.py, anthropic_strict.py}`, `app/rules/{loader.py, engine.py, _validators/}`. The wire contracts are in `app/schemas/wire/` (PRD §6.x). The application service in `app/services/evaluator.py` is where the seams compose. Frontend is `frontend/src/` (TS + Vite); the built bundle is committed under `app/ui/static/island/` so reviewers without a Node toolchain can still run the demo.

## UX and error handling

Every negative disposition includes a structured `reason_code` from a single taxonomy (`BIN.SUB.SPECIFIC[.QUALIFIER]`). Engine failures emit `needs_review` with one of `ENGINE.EXTRACTION.UNAVAILABLE`, `ENGINE.MODEL.UNAVAILABLE`, `ENGINE.SLA.TIMEOUT`, or `ENGINE.VALIDATOR.{TIMEOUT,EXCEPTION}`; the reviewer never sees a stack trace. Override is `O → reason → ENTER` from anywhere in the disposition view. Live region announcements are scoped so screen-reader users hear "passed" or "failed" without having to navigate to the pill.

## Trade-offs and known gaps

- **Spirits rule pack is deep, wine and malt are shallow.** I chose one class to do thoroughly (Standard of Identity recognition, age-statement floor) rather than three classes half-finished. The cross-cutting rules (warning, ABV, net contents) cover all three.
- **No reviewer identity, no auth.** The override leg records a stub reviewer ID. Real identity is a pilot-tier concern; the brief explicitly carved auth out.
- **No persistence.** Restart the container and audit/state is gone. The seams (audit ring buffer, batch state) are designed so a durable store can be dropped in without code changes elsewhere.
- **The full eval AC gate (macro-F1 ≥ 0.70) is not met end-to-end.** End-to-end on the live stack: macro-F1 = 0.19. The harness, adapter, and scoring are real and complete; the gap is two-layered — synthetic 200×200 fixtures aren't reliably OCR-able by `gpt-4o-2024-08-06` (4/6 fixtures route to `ENGINE.EXTRACTION.UNAVAILABLE` and force `needs_review`), and the manifest's `expected_per_rule` uses PRD-style `FR-XXX` rule IDs while the live engine emits YAML-registry IDs (zero overlap, so per-rule recall is vacuous). To isolate rule-engine quality from OCR robustness, the harness also runs in `--mode replay`: vision is replaced with a synthesizer that maps each fixture's `expected.json` to the rule-side observations validators consume. **Replay macro-F1 = 0.82** (5/6 fixtures correctly disposition; FIX-07's borderline-confidence signal lives downstream of validators and isn't replay-encodable). Replay is a diagnostic isolation tool, not a §4 gate substitute — six layout/verbatim rules are skipped because they need pixel-derived metadata (full disabled list with rationale in `eval/_vision_replay.py`). Cost-weighted score on the live stack is 0.83–0.94, which means most errors are false-rejects (asked for review) rather than false-accepts (silently passed). Full write-up in `docs/plans/ttb-label-verification-epoch-8-demo-eval-deploy.md` §10.

## Setup

If you just want to try it, the live demo above already has the key configured server-side — no local setup required. Local boot is for reading code and running the eval harness.

**You will need an OpenAI API key for any local profile.** The orchestrator (LLM) always runs against GPT-4o; only the vision model can run locally. Get a key at https://platform.openai.com/api-keys.

In every profile: `cp .env.example .env`, then put your key on the `OPENAI_API_KEY=` line. Every other variable in `.env.example` has a sensible default and can stay as-is.

The React UI bundle is pre-built and committed under `app/ui/static/island/`, so Profiles B and C do not need a Node toolchain.

### Profile A — WSL2 + GPU (local vision path, GPU-extras install)
```bash
git clone https://github.com/AaronCarney/ttb-label-verification && cd ttb-label-verification
cp .env.example .env  # fill OPENAI_API_KEY
uv sync --extra gpu
uv run task demo
# Open http://localhost:8000
```

### Profile B — macOS, no GPU (cloud vision path)
```bash
git clone https://github.com/AaronCarney/ttb-label-verification && cd ttb-label-verification
cp .env.example .env  # fill OPENAI_API_KEY
uv sync
uv run task demo
# Open http://localhost:8000
```

### Profile C — Linux, no GPU (cloud vision path)
Same as Profile B.

## Eval

```bash
uv run task eval-smoke   # ~20 labels, < 60 s, mocked harness mechanics
uv run task eval-full    # ~50 labels, several minutes, hits the live pipeline
```

The `/eval` dashboard route is gated by `DEV_MODE=1` so production builds never serve it.

## Where the rest of the story lives

- [`docs/BRD.md`](docs/BRD.md) — what we're solving and why
- [`docs/PRD.md`](docs/PRD.md) — what the system does, the FR/NFR list, acceptance criteria
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, data flow, deployment
- [`docs/03-decisions.md`](docs/03-decisions.md) — every architectural decision, dated, with rationale
- [`DEMO-RUNBOOK.md`](DEMO-RUNBOOK.md) — operational checks and HF Space provisioning

## License

Prototype; not for production use.
