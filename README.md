# TTB AI-Powered Alcohol Label Verification Prototype

Standalone, web-deployable proof-of-concept for AI-orchestrated, deterministic-rule-core
COLA label verification with a human-in-the-loop disposition. See `docs/BRD.md` for
business context, `docs/PRD.md` for behavior, `docs/ARCHITECTURE.md` for design.

## Repository layout

```
app/                 FastAPI single-process application (Web, Application Service,
                     Vision Extractor seam, Rule Engine, AI Orchestrator seam,
                     Batch Processor, Audit Recorder, schemas, UI shell)
frontend/            React + Vite island sources (built bundle committed to
                     app/ui/static/island/)
rules/               Canonical YAML rule pack + reason-codes registry + tables
assets/              Hash-pinned regulatory assets (e.g. §16.21 verbatim warning)
fixtures/            6 demo fixtures
demo/cached/         Pre-warmed LLM responses for the demo fixtures
eval/                Eval-harness manifest, datasheet, and DEV_MODE-only history
configs/             Per-mode TOML defaults (vision.local, vision.cloud, orchestrator)
scripts/             Operational scripts (e.g. regenerate_fixtures.py)
docs/                Living documents — BRD, PRD, ARCHITECTURE, decisions log,
                     PRD-deferred-content, planning history, research outputs
tests/               Pytest suite
```

## Documentation

| Doc | Purpose |
|---|---|
| `docs/BRD.md` | Business case, stakeholders, value, scope envelope |
| `docs/PRD.md` | User journeys, FRs/NFRs, wire contracts, acceptance criteria |
| `docs/ARCHITECTURE.md` | Components, interfaces, internal models, deployment, ADRs |
| `docs/03-decisions.md` | Decision log (D-001 onward) |
| `docs/PRD-deferred-content.md` | PRD trimmings, absorbed by ARCHITECTURE.md |
| `docs/planning/` | Pre-research planning + per-topic research plans (T1–T12, R0) |
| `docs/research/` | Research outputs (T1–T12) and synthesis briefs (S1–S8) |

## Status

Pre-implementation. Repository scaffold only — code lands per ARCHITECTURE.md §14.1.
