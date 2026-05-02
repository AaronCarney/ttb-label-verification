# Research Plan — Master Index

**Status:** LIVING DOCUMENT
**Last updated:** 2026-04-28 (v3: added R0 reference doc; T7 refocused on policy-gradation framing)

## Purpose

This document indexes the research topics that need answering before and during prototype build. Each topic has its own brief (T1.md through T12.md), intended to be passed as context to a separate Claude research conversation along with the relevant artifacts.

## Two kinds of supporting docs

- **Tn briefs (T1–T12)** — open research questions to be investigated.
- **Rn reference docs** — settled context, not open research. These exist because some material recurs across multiple Tn topics and shouldn't be re-researched independently each time. Treat as required reading for the Tn topics that cite them.

## How to use this plan

1. **Read the phasing.** Don't run topics out of order unless the dependency graph permits it.
2. **Pick a topic that has its prerequisites met.** Each topic brief states its prereqs at the top.
3. **Open a fresh Claude conversation.** Upload the original brief, all five core artifacts (01–05), the topic brief itself, and any Rn reference docs the topic cites.
4. **Run only the in-topic questions in that conversation.** Cross-topic synthesis questions (flagged in each brief) are held until the constituent topics are complete.
5. **Save the research output** as `Tn-output.md` (e.g., `T1-output.md`) and add it to project knowledge before running downstream topics.

## Required artifacts for every research conversation

These should be attached to every topic conversation as baseline context:

- The original take-home brief
- `01-requirements.md`
- `02-architecture.md`
- `03-decisions.md`
- `04-research-topics.md`
- `05-gaps-and-limitations.md`

Topic-specific additional reading is listed in each brief, including any Rn reference docs.

## Reference docs

| ID | Title | Required for |
|---|---|---|
| R0 | Federal Cost & Budget Analysis Conventions | T7 (lightly), T11 (heavily), T12 (heavily) |

## Phasing

```
                    ┌─────────────────────────┐
                    │ T10: Stakeholder        │  (independent; run anytime,
                    │      Frameworks         │   most useful early)
                    └─────────────────────────┘

PHASE 1 — FOUNDATION (must complete before Phase 2 questions can be fully formulated)

       ┌──────────────────────────┐    ┌──────────────────────────┐
       │ T1: TTB Regulatory       │    │ T2: COLA System &        │
       │     Framework            │    │     Operational Context  │
       └─────────────┬────────────┘    └─────────────┬────────────┘
                     │                                │
                     │  (T1 and T2 can run in parallel)
                     │                                │
                     ▼                                ▼

PHASE 2 — CORE ARCHITECTURE (parallel after Phase 1)

       ┌──────────────────────────┐    ┌──────────────────────────┐
       │ T3: Validation /         │    │ T4: OCR & Vision         │
       │     Rule Engine          │    │     Architecture         │
       │     (needs T1)           │    │     (needs T1, T2)       │
       └─────────────┬────────────┘    └─────────────┬────────────┘
                     │                                │
                     ▼                                ▼

PHASE 3 — COMPOSED ARCHITECTURE (parallel after Phase 2)

  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
  │ T5: AI / LLM     │ │ T6: Batch        │ │ T7: Federal      │ │ T11: Economic    │
  │     Orchestration│ │     Processing   │ │     Deployment   │ │      Analysis    │
  │  (needs T3, T4)  │ │ (needs T2,T3,T4) │ │ (needs R0; T3,T4,│ │ (needs R0; T2,T4,│
  │                  │ │                  │ │  T5 partial)     │ │  T5, T7 partial) │
  └─────────┬────────┘ └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
            │                   │                    │                    │
            └───────────────────┼────────────────────┼────────────────────┘
                                │                    │
                                ▼                    ▼

PHASE 4 — USER-FACING & EVALUATION (after Phase 3)

  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
  │ T8: UX Design        │  │ T9: Test Data &      │  │ T12: Decision        │
  │     (needs T2, T7)   │  │     Evaluation       │  │      Communication & │
  │                      │  │     (needs T1, T3)   │  │      Visualization   │
  │                      │  │                      │  │ (needs R0; T11 prim.;│
  │                      │  │                      │  │  T7,T8,T9,T10 sec.)  │
  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

## Topic summary

| ID | Topic | Phase | Prerequisites | Status |
|---|---|---|---|---|
| T1 | TTB Regulatory Framework | 1 | none | READY |
| T2 | COLA System & Operational Context | 1 | none | READY |
| T3 | Validation / Rule Engine Architecture | 2 | T1 | PARTIAL |
| T4 | OCR & Vision Architecture | 2 | T1, T2 | PARTIAL |
| T5 | AI / LLM Orchestration Architecture | 3 | T3, T4 | DEFERRED |
| T6 | Batch Processing Architecture | 3 | T2, T3, T4 | DEFERRED |
| T7 | Federal Deployment Architecture | 3 | R0; T3, T4, T5 partial | PARTIAL — refocused on policy-gradation framing |
| T8 | UX Design | 4 | T2, T7 | PARTIAL |
| T9 | Test Data & Evaluation Strategy | 4 | T1, T3 | PARTIAL |
| T10 | Stakeholder Frameworks Applied | independent | none | READY |
| T11 | Economic Analysis (TCO + labor savings) | 3 | R0; T2, T4, T5, T7 partial | PARTIAL |
| T12 | Decision Communication & Visualization | 4 | R0; T11 primary; T7,T8,T9,T10 secondary | PARTIAL |

**Status legend:**
- **READY**: All in-topic questions can be researched now.
- **PARTIAL**: Some questions can be researched now; deeper ones flagged as deferred within the brief.
- **DEFERRED**: Most questions cannot be meaningfully formulated until prereqs are answered. Brief contains question stubs and notes on what's needed.

## What "questions cannot be formulated" means

Three different cases:

1. **Question is fully answerable now.** Run it.
2. **Question depends on a prior topic's output but the dependency is light.** Question can be formulated; answer may be conditional on prior outputs. Run it with awareness.
3. **Question depends fundamentally on prior outputs and would be malformed without them.** Hold it until the prereq is done. Marked `DEFERRED` in the topic brief.

T5 and T6 are the clearest cases of (3). T11's costing questions and T12's specific-application questions are the next most dependent.

## Cross-topic synthesis registry

These questions cannot be answered in any single topic conversation. They require collation of outputs from multiple topics. They should be run as a final synthesis pass after their constituent topics are complete.

| ID | Question | Requires |
|---|---|---|
| X-1 | What does the end-to-end processing time budget look like, broken down by component, against the 5s SLA? | T3, T4, T5, T6 |
| X-2 | Where does the system fall back to "needs human review" vs "automatic reject"? Map the decision tree across all components. | T3, T4, T5 |
| X-3 | What are the production-readiness gaps between the prototype architecture and what would clear FedRAMP / ATO? | T3, T4, T5, T7 |
| X-4 | Which TTB regulatory rules require code logic vs. which can be expressed as pure data? | T1, T3 |
| X-5 | What is the test corpus design that exercises every rule across every beverage class with realistic failure modes? | T1, T2, T9 |
| X-6 | What does the demo path look like that hits Sarah, Dave, and Jenny's strongest signals, with appropriate visualization throughout? | T8, T9, T10, T12 |
| X-7 | Map cost × policy × technical fit per architectural option, producing the headline trade-off chart that goes in the README. | T7, T11, T12 |

When running synthesis, open a new conversation, attach all required topic outputs, and ask the synthesis question directly.

## Iteration and updates

- New questions identified during research go back into the relevant topic brief, not into the conversation in flight.
- If a topic surfaces a previously-unknown dependency, update this master plan and the affected topic brief before continuing.
- Resolved topics produce a `Tn-output.md` that becomes required reading for downstream topics.

## Revision history

- **2026-04-28 (v1)** — Created with T1–T10.
- **2026-04-28 (v2)** — Added T11 (Economic Analysis) and T12 (Decision Communication & Visualization). Added X-7 to synthesis registry.
- **2026-04-28 (v3)** — Added R0 (Federal Cost & Budget Analysis Conventions) as reference doc. Refocused T7 on policy-gradation framing rather than compliance-checklist framing. Updated phasing diagram and prereqs to reference R0 where relevant.
