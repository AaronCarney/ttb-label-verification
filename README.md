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

> **Live demo:** https://context31415-ttb-label.hf.space — interact with the seven demo fixtures (single-label) directly. A spoken-narration walkthrough is in `docs/demo-narration.md`.

## How to think about this prototype

This is a take-home prototype, not a production system. It does not connect to COLAs Online, write back, or replace a reviewer's signature. The point is to show how an AI-assisted review tool can speed up the routine field-matching work without putting the regulatory verdict in the AI's hands.

## The four decisions that shape everything else

1. **The AI never decides — it just helps explain.** All `pass` / `fail` / `needs_review` verdicts come from deterministic code reading a YAML rule pack. The language model only paraphrases template reasoning and reconciles ambiguous OCR reads. If the model goes down or returns garbage, the system emits `needs_review` with a structured reason — it never silently flips to `pass`.

2. **Rules live in YAML, not Python.** Each regulation is a row in a YAML file (`rules/`) with the CFR citation, the rule logic name, and the parameters. Updating a tolerance or adding a class-of-product rule is a config change, not a code change. Python only contains the validators these rules call by name.

3. **The two AI dependencies are swappable.** OCR (vision) and the language model both sit behind a small project-owned interface. The cloud path uses GPT-4o with structured outputs; the on-prem path uses PaddleOCR plus the same model. A second LLM backend (Anthropic) is wired as a skeleton to prove the seam works — it is not run live. Switching is an environment-variable flip, not a refactor.

4. **No persistence, no auth, no integration.** Everything is in-memory and session-scoped. This was a deliberate scope cut for the prototype: it keeps the surface area small enough to be reviewed in a few hours and lets the demo run on a free tier. A real deployment would replace the in-memory state with a durable store at the seams already marked for it.

## What's deliberately not in the box

- **No COLAs Online integration.** The application input is a JSON envelope plus a label image; the output is a JSON disposition envelope. Whoever calls it owns the integration.
- **No persistent storage.** Audit trail and batch state live in process memory and disappear when the container restarts.
- **No reviewer identity or auth.** The override leg records a stub reviewer ID; real identity is a pilot-tier concern.
- **One rule pack depth.** The spirits rules are the deep cut (per the take-home brief); wine and malt are wired to the rule engine but the rule pack itself is intentionally shallow on those classes.

## Honest gaps

The full eval (`uv run task eval-full`) does run end-to-end against the live pipeline, but the macro-F1 number on first run lands well below the 0.70 target. Two reasons, both mechanical: (a) the synthetic 200×200 fixture PNGs are too low-resolution and too plain for GPT-4o to OCR consistently, so several fixtures route to `needs_review` for the wrong reason; (b) the eval manifest schema uses `FR-XXX` rule IDs while the live engine emits the YAML registry IDs, so per-rule recall is computed on an empty intersection. The harness, adapter, scoring, and history serialization are all real and complete; the gap is in the fixture and manifest data quality. Full write-up is in `docs/plans/ttb-label-verification-epoch-8-demo-eval-deploy.md` §10.

## Setup (reviewer profiles)

The React UI bundle is pre-built and committed under `app/ui/static/island/`, so Profiles B and C do not need a Node toolchain.

### Profile A — WSL2 + GPU (full local-mode path, includes UI rebuild)
```bash
git clone https://github.com/AaronCarney/ttb-label-verification && cd ttb-label-verification
uv sync --extra gpu
uv run task demo
# Open http://localhost:8000
```

### Profile B — macOS, no GPU (cloud-mode only)
```bash
git clone https://github.com/AaronCarney/ttb-label-verification && cd ttb-label-verification
cp .env.example .env  # then fill OPENAI_API_KEY
uv sync
uv run task demo
# Open http://localhost:8000
```

### Profile C — Linux, no GPU (cloud-mode only)
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
- [`DEMO-RUNBOOK.md`](DEMO-RUNBOOK.md) — five-minute reviewer walkthrough
- [`docs/demo-narration.md`](docs/demo-narration.md) — the spoken script for that walkthrough

## License

Prototype; not for production use.
