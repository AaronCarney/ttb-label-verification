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

AI-powered alcohol label verification against TTB regulations. Returns a draft
disposition (`pass` / `fail` / `needs_review`) for a COLA label in ≤5 s with
citation-grounded reasoning.

> **Live demo:** https://context31415-ttb-label.hf.space — interact with the seven demo fixtures (single-label) directly. A spoken-narration walkthrough is in `docs/demo-narration.md`.

## One-command setup (reviewer profiles)

The React island bundle is pre-built and committed under `app/ui/static/island/`, so reviewer profiles B/C do **not** need a frontend toolchain.

### Profile A — WSL2 + GPU (full local-mode path, includes frontend rebuild)
```bash
git clone https://github.com/aaroncarney/ttb-label-verification && cd ttb-label-verification
uv sync --extra gpu
# Optional — only needed if you want to rebuild the UI bundle:
# (cd frontend && pnpm install && pnpm build)
uv run task demo
# Open http://localhost:8000
```

### Profile B — macOS, no GPU (cloud-mode only)
```bash
git clone https://github.com/aaroncarney/ttb-label-verification && cd ttb-label-verification
uv sync
export OPENAI_API_KEY=sk-...
uv run task demo
# Open http://localhost:8000
```

### Profile C — Linux, no GPU (cloud-mode only)
Same as Profile B.

## Headline trade-off

This prototype optimizes for **citation-grounded transparency** over **end-to-end automation**. The deterministic rule core (`rules/`) makes pass/fail decisions; the AI surface (Vision + Orchestrator) extracts evidence and proposes explanations but never decides.

The economic case (`docs/research/T11-output.md`) and policy case (`docs/research/T7-output.md`) settle the trade-off range.

## Documentation

- [Business requirements](docs/BRD.md)
- [Product requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decisions log](docs/03-decisions.md)
- [Demo runbook](DEMO-RUNBOOK.md) — for the recorded walkthrough

## Eval

```bash
uv run task eval-smoke   # ~20 labels, < 60 s
uv run task eval-full    # ~50 labels, several minutes (merge-to-main gate)
```

The `/eval` route is `DEV_MODE`-gated.

## License

Prototype; not for production use.
