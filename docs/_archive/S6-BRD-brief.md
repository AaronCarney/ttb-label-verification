# S6 — Business Requirements Document (BRD)

**Phase:** Synthesis (post-research)
**Status:** READY TO AUTHOR
**Prerequisites:** All Tn-output (especially T1, T2, T7, T10, T11, T12) and Sn-output (S2 for scope-cuts) files; R0; D-001, D-008, D-009.
**Blocks:** PRD (S7) and Architecture Doc (S8) reference back to this for the "why."

---

## Synopsis

This session produces `BRD.md` — the business case for the TTB AI-Powered Alcohol Label Verification prototype. The BRD answers **why** this work exists: business problem, stakeholders, value at scale, policy posture, constraints. It does **not** define what we're building (PRD) or how it's built (Arch Doc).

The take-home brief is the ground truth. Everything else (T1–T12, S1–S5, decision log) is research that *interprets* the take-home — it does not replace it. When the take-home conflicts with downstream research, the take-home wins, and the conflict gets logged as a risk or open question.

A second framing point: the BRD has a dual audience. The **stated** audience is the take-home reviewer (Sarah's team), who should read it as evidence the candidate understood the business context. The **simulated** audience is a TTB sponsor / OMB reviewer, who would read it as a real business case. Write for the simulated audience; the stated audience will recognize the rigor.

## Required reading

- **Primary (treat as ground truth):**
  - `Take-Home_Project__AI-Powered_Alcohol_Label_Verification_App.docx` — interview notes (Sarah, Marcus, Dave, Jenny), technical requirements, deliverables, evaluation criteria
- **Core artifacts:**
  - `01-requirements.md`, `02-architecture.md`, `03-decisions.md` (esp. D-001, D-008, D-009), `04-research-topics.md`, `05-gaps-and-limitations.md`
- **Research outputs (business-case material):**
  - `T1-output.md` — regulatory framework anchor
  - `T2-output.md` — operational context (volume, review time, COLA system)
  - `T7-output.md` — federal deployment / policy gradation
  - `T10-output.md` — stakeholder analysis (salience, empathy maps, JTBD, pre-mortem)
  - `T11-output.md` — economic analysis (TCO, labor savings, sensitivity)
  - `T12-output.md` — decision communication and visualization
  - `R0-federal-cost-conventions.md` — A-94 / GAO-20-195G conventions
- **Excluded from this session** (those are PRD / Arch Doc material): T3, T4, T5, T6, T8, T9, S1, S3, S4, S5.

## Output expected

A single `BRD.md` document, ~8–15 pages, with these sections in order:

1. Executive summary
2. Background and current state
3. Business objectives
4. Stakeholders
5. Business requirements (high-level — *not* functional requirements)
6. Project scope
7. Cost-benefit analysis
8. Compliance and regulatory posture
9. Constraints, assumptions, dependencies
10. Risks and mitigations
11. Glossary
12. Appendices (cross-references to PRD, ADRs, source research)

## In-topic questions

### Section 1 — Executive summary

#### Q1.1 — One-paragraph problem statement
What is the business problem in one paragraph, framed in TTB terms (not engineering terms)? Source: take-home (Sarah's interview, esp. "drowning in routine stuff"); T2 volume figures; T1 regulatory context.

#### Q1.2 — One-paragraph proposed approach
What is the proposed approach at the level a sponsor would care about? Mention "AI-orchestrated, deterministic-rule-core," human-in-the-loop, prototype scope, and the ~5s latency commitment. Do **not** describe the architecture. Source: D-002, D-007; take-home tech requirements.

#### Q1.3 — Headline value proposition
What's the headline number or framing? E.g., "saves N agent-minutes per application at expected accuracy X across ~150K applications/year." Pull the actual range from T11 §Stage 2 / Q11.7. Source: T11 outputs only — do not invent figures.

*Write this section last, after Sections 2–10 are written.*

### Section 2 — Background and current state

#### Q2.1 — Current TTB label review process
Describe the current state in 3–5 paragraphs: ~150K applications/year, 47 agents, COLA system (.NET, 2003-era), 5–10 min per simple application, manual eyeball matching. Source: take-home Sarah interview; T2 §operational context.

#### Q2.2 — What's broken about it (from the inside view)
What do agents actually experience? Lift specifics from interview notes — Sarah's "data entry verification," Dave's nuance examples, Jenny's printed checklist, the failed scanning vendor pilot. Source: take-home interviews verbatim where possible.

#### Q2.3 — Prior modernization attempts and why they failed
The scanning vendor pilot is the canonical case. What lessons does it teach about latency (5s killed it), firewall constraints (Marcus), and adoption (Dave's skepticism)? Source: take-home Marcus + Sarah; T2 §prior pilots if applicable.

#### Q2.4 — Why now
What changed that makes this tractable now? GPU-affordable vision models, structured-output LLMs, federal-context viable on-prem inference. Keep this short — 2–3 bullet equivalents in prose. Source: S1 high-level findings (don't go into stack details).

### Section 3 — Business objectives

#### Q3.1 — SMART objective hierarchy
Translate "help agents do label review faster and better" into SMART (specific, measurable, achievable, relevant, time-bound) objectives. Suggested objectives:
- **Throughput:** reduce average per-application review time from current baseline by N% (cite T11 Stage 1 ranges).
- **Accuracy:** maintain or improve agent disposition accuracy vs. current human-only baseline (cite T9/S4 evaluation targets).
- **Adoption:** achieve usage by ≥X% of agents within Y days post-rollout (cite T10 pre-mortem data).
- **Compliance:** every disposition produces a rule-cited rejection reason (cite D-007).

For each, state the metric, the target range, the time horizon, and the source of the figure. **Use ranges, not point estimates** (D-009).

#### Q3.2 — Strategic alignment
How does this connect to higher-level TTB / Treasury / federal IT-modernization priorities? Source: T7 policy framing; OMB IT modernization guidance referenced in R0.

#### Q3.3 — Non-objectives
What is this explicitly **not** trying to do? E.g., not replacing agents, not integrating with COLA, not automating allowable-revisions review (S2 D-010 out-of-scope), not handling beverages outside Parts 4/5/7. Source: take-home Marcus ("standalone proof-of-concept"); D-003; S2 D-010.

### Section 4 — Stakeholders

#### Q4.1 — Stakeholder roster with roles, interests, and influence
Produce a stakeholder table from T10 §Q10.1–Q10.2 (salience model). Columns: name, role, prototype-stage influence, production-stage influence, primary interest, success criterion they care about. Include **at minimum**: Sarah, Dave, Jenny, Marcus, plus the production-stage emergent stakeholders T10 surfaced (CIO, FedRAMP authorizing official, OMB, applicants, etc.).

#### Q4.2 — RACI for the prototype phase
Lift T10 §Q10.3 RACI directly; cite the source.

#### Q4.3 — Phase-dependent priority
Restate D-001 in business-case language (not engineering decision-log language). Why does the order flip between prototype and production stages?

#### Q4.4 — Stakeholder concerns and mitigations
For each top-tier stakeholder, what's their #1 concern and how does this project address it? Source: T10 empathy maps (Q10.4–Q10.6) and pre-mortem (Q10.7).

### Section 5 — Business requirements (high-level)

*Note:* These are **business** requirements, not functional ones. The PRD will translate these into functional requirements. Keep each at the "what the business needs" level. Format as numbered BR-001, BR-002, etc., with a one-line statement plus rationale and source.

#### Q5.1 — Core verification requirements
What does the business need the system to verify? Brand match, ABV, net contents, government warning, bottler info, country of origin (imports). Cite take-home tech requirements + T1 §1.1 field manifest.

#### Q5.2 — Reasoning and audit trail requirements
The business needs every disposition to carry a human-readable, regulation-cited explanation. Source: D-007 elevated to Hard tier in `01-requirements.md`.

#### Q5.3 — Throughput and latency requirements
~5s per single label; batch handling for peak-season importer drops of 200–300 labels. Source: take-home Sarah verbatim; D-010.

#### Q5.4 — Usability requirements
"73-year-old benchmark" senior-friendly UI; manual review path always available. Source: take-home Sarah + Dave; `01-requirements.md` Strong tier.

#### Q5.5 — Production-parity design requirements
Wrap cloud dependencies behind interfaces; design for on-prem inference path; respect federal firewall posture. Source: D-004; take-home Marcus.

#### Q5.6 — Regulatory coverage requirements
Wine, spirits, malt at common-fields level; class-specific rules deferred. Source: D-003; D-010; T1 scope.

### Section 6 — Project scope

#### Q6.1 — In-scope (MVP)
Lift S2 D-010 MVP scope verbatim, summarized in business language (not engineering language).

#### Q6.2 — Stretch
Lift S2 D-010 stretch list in business language.

#### Q6.3 — Out of scope
Lift S2 D-010 out-of-scope list. Add explicitly: COLA integration, allowable-revisions review, post-approval change auditing, conditional fields (sulfite, organic, allergen, cochineal). Source: D-003; D-010; take-home Marcus on COLA.

#### Q6.4 — Future phases (informative, not committed)
What plausibly happens after the prototype? Production pilot, FedRAMP path, COLA integration. Frame as informational, not as a commitment. Source: T7 staging.

### Section 7 — Cost-benefit analysis

*This section is the synthesis output of T11 and T12. Do not regenerate the analysis; cite it.*

#### Q7.1 — Methodology statement
State that the analysis follows OMB Circular A-94 (Nov 2023) and GAO-20-195G conventions, framed as cost-effectiveness analysis (CEA) per D-009. One paragraph. Source: D-009; R0.

#### Q7.2 — Labor savings model summary
Summarize T11 Stage 1–2 outputs: per-application time saved range × annual volume range × loaded labor rate range = aggregate annual labor savings range. Show the headline range with explicit drivers. Source: T11 Q11.4, Q11.7, Q11.8.

#### Q7.3 — Per-option cost summary
Summarize T11 Stage 3 outputs in a single comparison table: option, one-time costs, recurring costs, variable costs, 3yr/5yr horizon. Source: T11 Q11.10–Q11.15.

#### Q7.4 — Net-value comparison
Summarize T11 Stage 4 — net value range per option, break-even points. Source: T11 Q11.16; T12 visualization recommendations.

#### Q7.5 — Sensitivity findings
What inputs drive the answer? Where does the recommendation flip? Source: T11 Q11.18–Q11.19.

#### Q7.6 — Realization-rate caveat
The single most consequential and most uncertain number is the realization rate (theoretical labor savings → budget savings). Surface it explicitly per T11 Q11.8. Source: T11 Q11.8.

#### Q7.7 — Non-monetizable factors
Risk reduction, agent experience, public trust, optionality. Source: T11 Q11.17.

#### Q7.8 — Headline framing
What's the honest one-sentence framing of the cost-benefit story? Source: T11 Q11.20.

### Section 8 — Compliance and regulatory posture

#### Q8.1 — Authority basis
What CFR provisions does the system check against, and where does that authority come from? Source: T1 §0 regulatory anchor (Parts 4, 5, 7, 16); cite specific TDs (TTB-176, TTB-199, TTB-158).

#### Q8.2 — Federal IT compliance posture (prototype)
Marcus's "for a prototype, just don't do anything crazy." No PII storage, no production-grade ATO required, no FedRAMP for the prototype. Source: take-home Marcus; T7 prototype-tier framing.

#### Q8.3 — Federal IT compliance posture (production, informational)
What would production require? FedRAMP Moderate or High, ATO, PIV/SAML, document retention policy, on-prem or Azure Government inference. Source: T7 staging map.

#### Q8.4 — Data handling posture
No persistent storage of submitted artwork beyond session. Source: `01-requirements.md` Strong tier; D-007.

#### Q8.5 — Audit and traceability
Every disposition includes rule citation, evidence, and reasoning suitable for downstream regulatory audit. Source: D-007.

### Section 9 — Constraints, assumptions, dependencies

#### Q9.1 — Constraints
- Time-boxed take-home prototype (not production).
- Federal firewall constrains outbound API calls in production (Marcus).
- ~5s latency ceiling is non-negotiable (Sarah's vendor-pilot lesson).
- 73-year-old benchmark UX (Sarah).
- Standalone — no COLA integration (Marcus).

Cite each.

#### Q9.2 — Assumptions
- Application data input format is mockable for the prototype (open clarification per `01-requirements.md`).
- Public COLA Registry is a usable test corpus (S4).
- Reviewer environment can run a deployed URL (take-home deliverable).
- Volume figures (~150K/yr) are stable for the next 3-yr horizon (T11 Q11.5).

#### Q9.3 — Dependencies
- Vision/OCR component (cloud or local — see Arch Doc).
- LLM component for orchestration (cloud or local).
- Public CFR text (eCFR) for regulation-citation strings.
- TTB Public COLA Registry for evaluation data.

Note that this list does not commit specific vendors — that's an Arch Doc concern.

### Section 10 — Risks and mitigations

#### Q10.1 — Risk register
Lift T10 §Q10.7 pre-mortem risks. Format as risk-id, description, likelihood, impact, mitigation, owner. Top items typically include:
- Cold-start latency past 5s on demo day (#1 from T10).
- Realization-rate gap between theoretical and budget savings (T11 Q11.8).
- Vendor-API price escalation / lock-in (T11 Q11.14).
- Regulatory changes during build (T1 §12.2 wine modernization risk).
- Adoption friction (Dave skepticism vector).
- Federal authorization timeline risk for production path (T7).

#### Q10.2 — Open questions and decisions deferred
What hasn't been decided and needs to be? Source: `01-requirements.md` Still-open clarifications; `04-research-topics.md`; `05-gaps-and-limitations.md`. Examples: application input format, deployed-URL auth posture, structured reason codes.

### Section 11 — Glossary

#### Q11.1 — Acronym and term list
ABV, ALC/VOL, ATO, BRD, CFR, COLA, CPI (characters per inch — TTB sense, not Consumer Price Index), FedRAMP, GS-grade, OCR, PIV, PRD, SAML, SoI (Standard of Identity), SoC (Statement of Composition), TD (Treasury Decision), TTB. Each gets a one-line definition. Source: T1 + T7 + R0 as needed.

### Section 12 — Appendices

#### Q12.1 — Cross-reference map
Pointers to:
- PRD (`PRD.md` — what we're building, in detail)
- Architecture Doc (`ARCHITECTURE.md` — how it's built)
- Decision log (`03-decisions.md`)
- Research outputs (`T1-output.md` … `T12-output.md`, `S1-output.md` … `S5-output.md`)
- Original take-home brief

## Cross-topic synthesis questions consumed by this session

- **X-7** (cost × policy × technical fit): the BRD is the natural home for this. Section 7 + Section 8 together resolve it.

## Notes for the author

- **The take-home brief wins ties.** When a research output disagrees with the take-home, follow the take-home and log the conflict as an open question.
- **Business language, not engineering language.** "The system must wrap cloud OCR behind a substitutable interface" is engineering. "The system must be deployable in environments that block outbound cloud calls" is business. The first belongs in the Arch Doc; the second in the BRD.
- **Cite, don't regenerate.** T11 already has the cost analysis. Pull the figures and cite the source. If you find yourself re-deriving numbers, stop — it belongs upstream in the research, not in this synthesis.
- **Ranges, not points** (per D-009). Every figure that came from T11 should preserve its range.
- **Don't bleed scope.** This is the BRD. Functional requirements (R-001 etc.) belong in the PRD. Component design belongs in the Arch Doc. If a section starts to feel detailed, ask whether it's still answering "why" — if it's drifting to "what" or "how," cut it.
- **Length target: 8–15 pages.** If it's growing past 15, content is leaking from PRD or Arch Doc.
- **New decisions surfaced during writing → ADRs.** Append D-013+ to `03-decisions.md` rather than burying decisions in the BRD prose.
