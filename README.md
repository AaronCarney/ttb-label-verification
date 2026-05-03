# TTB Label Verification — Prototype

A standalone, web-deployable proof-of-concept for AI-orchestrated, deterministic-rule-core
TTB COLA label verification. **Prototype tier** per BRD §8.2 — not a production ATO claim,
no COLAs Online integration, no persistence beyond the current process.

See `docs/PRD.md` (v0.6) and `docs/ARCHITECTURE.md` (v0.3) for the full spec; see
`docs/plans/ttb-label-verification-epochs.md` for the L1 epoch plan.

## Reviewer profiles (ARCH §9.1)

Three one-command setup profiles target the deployed-URL and on-prem trajectories.

### Profile A — Hosted demo (preferred)

The deployed URL serves the cloud-mode default (GPT-4o on crop, Structured Outputs
`strict:true`). No local install; no API key needed for review against cached fixtures.

### Profile B — Local cloud-mode boot

```bash
git clone <repo>
cd ttb-label-verification
cp .env.example .env  # then fill OPENAI_API_KEY
uv sync               # CPU profile; ≤90s on a 5 Mbps connection
uv run task demo      # uvicorn app.main:app on :8000
curl http://localhost:8000/healthz
```

### Profile C — Local GPU mode (on-prem-trajectory)

```bash
uv sync --extra gpu   # adds paddlepaddle-gpu (CUDA 12.6) + torch
VISION_MODE=local uv run task demo
```

GPU profile boot adds ~30–45 s for first-`/healthz` (model load); subsequent
`/healthz` warm calls are ≤2 s. See `DEMO-RUNBOOK.md` for the demo timeline.

## Project structure

```
app/                    FastAPI single-process app
  schemas/              Pydantic v2 internal + wire (PRD §6.x) types
  logging/              JSON-line stdout, OTel GenAI attribute names
  api/                  Route handlers (E1: /healthz; E5–E8 add the rest)
  config.py             Pydantic Settings (single source of truth for env vars)
  deps.py               DI container; selects VisionExtractor / Orchestrator
  main.py               App factory
tests/                  pytest suite
docs/                   PRD, ARCHITECTURE, decisions, epoch plans
```

## Testing

```bash
uv run pytest -v
```

The exit-gate integration suite is `tests/test_e1_exit_gate.py` (E1) and the
analogous `test_e<N>_exit_gate.py` for later epochs.
