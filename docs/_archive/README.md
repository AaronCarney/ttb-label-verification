# docs/_archive/ — Research Scaffolding (Historical)

Files here are research **briefs** and pre-spec **synthesis briefs** that have been superseded by the canonical specs (`BRD.md`, `PRD.md`, `ARCHITECTURE.md`, `03-decisions.md`) and the substantive research outputs (`docs/research/T*-output.md`, `docs/research/S1-S5-output.md`).

Moved here for clarity, not deletion — the content is historically valuable as paper-trail for how the active spec was derived.

## What's here

### Research-topic briefs (the prompts that defined what to research)

The corresponding substantive **outputs** live in `docs/research/T*-output.md` (T1 brief → T1 output, etc.).

- `T1-regulatory-framework.md`
- `T2-cola-operational-context.md`
- `T3-validation-engine.md`
- `T4-ocr-vision.md`
- `T5-ai-orchestration.md`
- `T6-batch-processing.md`
- `T7-federal-deployment.md`
- `T8-ux-design.md`
- `T9-test-data-evaluation.md`
- `T10-stakeholder-frameworks.md`
- `T11-economic-analysis.md`
- `T12-decision-communication.md`
- `T13-labeled-fail-data.md`

### Spec-derivation briefs (consumed into the canonical spec docs)

- `S6-BRD-brief.md` — consumed into `docs/BRD.md`
- `S7-PRD-brief.md` — consumed into `docs/PRD.md`
- `S8-architecture-brief.md` — consumed into `docs/ARCHITECTURE.md`

## What's intentionally NOT here

The following live in `docs/planning/` because they're cited by bare-name from the active specs and are still load-bearing reference material:

- `00-research-plan.md` — listed in BRD §12.2 source documents
- `01-requirements.md` — cited heavily across BRD / PRD for FR/BR tier classification (Hard / Strong / Medium / Stretch)
- `02-architecture.md` — cited from PRD §15 glossary
- `04-research-topics.md` — cited from BRD §10.2 / PRD §12.1 as the source of inherited open questions
- `05-gaps-and-limitations.md` — cited from BRD / PRD as the honest-disclosure source for accepted prototype gaps
- `R0-federal-cost-conventions.md` — reference doc cited from `03-decisions.md` (D-009) and consumed by T7 / T11 / T12 outputs

## Why split this way

The active spec hierarchy reads:

```
BRD ──► PRD ──► ARCHITECTURE ──► L1 epoch plans (docs/plans/)
        │                       │
        ├──► research/T*-output  (substantive research, still authoritative)
        ├──► research/S1-S5      (synthesis sessions, still authoritative)
        └──► planning/{0X, R0}   (still cited by bare name from active specs)
```

The archived T-briefs and S6/S7/S8 spec-briefs are scaffolding **above** the active layer — once the outputs they produced were absorbed into the active specs and into `docs/research/`, the briefs themselves became historical.
