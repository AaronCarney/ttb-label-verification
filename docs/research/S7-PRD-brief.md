# S7 — Product Requirements Document (PRD)

**Phase:** Synthesis (post-research)
**Status:** READY TO AUTHOR
**Prerequisites:** `BRD.md` (S6 output) is complete and approved. All Tn-output and Sn-output files. `01-requirements.md`, `02-architecture.md`, `03-decisions.md` (esp. D-001 through D-015), `04-research-topics.md`, `05-gaps-and-limitations.md`. R0.
**Blocks:** Architecture Doc (S8) references the PRD's functional requirements as the "what" it must implement.

---

## Synopsis

This session produces `PRD.md` — the functional specification for the TTB AI-Powered Alcohol Label Verification prototype. The PRD answers **what** the system does. It does **not** explain why (BRD) or how (Arch Doc).

The seam:

- **BRD** owns business problem, stakeholders, value, scope, compliance posture, BR-### business requirements ("the system must be deployable in firewalled federal environments").
- **PRD** owns user roles, user journeys, functional requirements (FR-###), inputs, outputs, data contracts at the system-boundary level, acceptance criteria, evaluation targets, and a BR→FR traceability matrix.
- **Arch Doc** owns components, interfaces between components, data models inside the system, technology choices, deployment topology, ADRs.

**The take-home brief is ground truth.** When research outputs disagree with the take-home, follow the take-home and log the conflict. When the BRD disagrees with the take-home, that's a BRD bug — flag it back to S6, don't paper over it in the PRD.

**Dual audience.** Stated audience: take-home reviewer evaluating whether the candidate translated stakeholder constraints into a buildable spec. Simulated audience: a TTB product owner handing this to an implementation team. Write for the simulated audience.

**Critical scope discipline.** Functional requirements describe externally observable behavior, not implementation. "The system shall apply Jaro-Winkler with thresholds 0.85/0.92" is implementation (Arch Doc). "The system shall surface brand-name matches that differ only in case or punctuation as a pass disposition" is functional (PRD). Test: could two competing implementations both satisfy this requirement? If yes, it's functional. If only one specific implementation could satisfy it, it's leaking architecture.

## Required reading

- **Primary (treat as ground truth):**
  - `Take-Home_Project__AI-Powered_Alcohol_Label_Verification_App.docx` — interview notes (Sarah, Marcus, Dave, Jenny), technical requirements, deliverables, evaluation criteria
- **Synthesis upstream (this PRD must align with):**
  - `BRD.md` (S6 output) — every FR-### must trace to a BR-### in the BRD's Section 5
- **Core artifacts:**
  - `01-requirements.md` (Hard / Strong / Medium / Stretch tiering — direct input to FR prioritization)
  - `02-architecture.md` (component inventory and data-flow boundary — informs where FRs sit, not how they're built)
  - `03-decisions.md` — esp. D-002 (deterministic core, AI orchestrates), D-003 (class-specific rules deferred), D-005 (per-field match policies), D-006 (ABV tolerance), D-007 (rejection reasoning required), D-010 (MVP scope), D-011 (demo shape), D-012 (rule-pack depth = spirits), D-013–D-015 (stack-shape, rule data format, deployment mode)
  - `04-research-topics.md` — open questions
  - `05-gaps-and-limitations.md` — accepted prototype gaps; these constrain FRs honestly
- **Research outputs (functional-spec material — the in-scope T-outputs for this session):**
  - `T1-output.md` — regulatory field manifest, per-field rules, government-warning specification, reason-code taxonomy. **Primary source for FRs in §5.3.**
  - `T2-output.md` — Form 5100.31 schema, submission paths, COLA Registry capabilities, accepted artwork formats. **Primary source for the application-input contract in §6.1 and FR-100 series.**
  - `T3-output.md` — validator interface (`FieldObservation` + `ExpectedValue` → `ValidationResult`), rejection-reason data model, confidence-scoring methodology, engine failure-mode taxonomy. **Primary source for the data contracts in §6 and the "needs-review" semantics in §5.10.**
  - `T4-output.md` — extraction requirements per field (text, bbox, typography, layout, color), needs-better-photo disposition, accepted-formats posture (JPEG/PNG only). **Primary source for extraction FRs in §5.1 and image-handling FRs in §5.7.**
  - `T5-output.md` — orchestrator task list (brand-name borderline, reasoning enrichment, OCR multi-reading reconciliation), failure-mode handling, single-shot tool-call posture. **Primary source for AI-orchestration FRs in §5.4 — keep at the "what task" level, not the "which model" level.**
  - `T6-output.md` — batch processing semantics, lookahead behavior (k=2–3), pull-based reactive-streams pattern, mid-batch override under independence assumption, soft-anomaly detector, backpressure. **Primary source for batch FRs in §5.5.**
  - `T8-output.md` — UX components (17-component inventory), demo path, accessibility floor (Section 508 / WCAG 2.0 AA legal floor; WCAG 2.1/2.2 as design targets), keyboard model, error-message standards, reduced-motion, reflow. **Primary source for UX FRs in §5.6 and accessibility ACs.**
  - `T9-output.md` and `S4-output.md` — evaluation methodology, acceptance criteria, per-rule precision/recall targets, eval manifest, harness behavior. **Primary source for §8 acceptance criteria and §9 evaluation plan.**
  - `S2-output.md` — D-010 MVP/stretch/out-of-scope, D-011 demo shape, D-012 rule-pack depth = spirits. **Lift directly into §3 scope and §10 demo plan.**
  - `S3-output.md` — D-013 stack-shape boundary (FastAPI + Jinja2 + React island; SVG bbox overlay), D-014 rule data format (real YAML under `rules/`), D-015 dual deployment mode (`VISION_MODE={local,cloud,auto}`). **The PRD references these as boundary commitments at the contract level; technology specifics live in the Arch Doc.**
  - `S5-output.md` — final per-class MVP rule list with reason codes; ABV tolerance values (spirits ±0.3 pp; malt ±0.3 pp w/ 0.5% floor; wine ±1.0 / ±1.5 pp w/ class-boundary anti-overlap); validator interface confirmation; reason-code grammar `BIN.SUB.SPECIFIC[.QUALIFIER]`. **Primary source for the rule manifest in §5.3 and reason-code grammar in §6.2.**
- **Excluded as primary sources for this session** (those are BRD or Arch Doc material): T7, T10, T11, T12, S1, R0, S6 itself.
  - T7's compliance posture is *referenced* in §11 as a constraint, not redrawn.
  - T10's stakeholder analysis is *referenced* in §2 user-role definitions, not redrawn.
  - T11/T12 economic and visualization material belongs in the BRD, not here.
  - R0 cost conventions are BRD-only.
  - S1 stack survey is upstream of S3's stack commitments and is Arch Doc material.

## Output expected

A single `PRD.md` document, ~15–25 pages, with these sections in order:

1. Document control and purpose
2. User roles and primary journeys
3. Scope (MVP / stretch / out of scope)
4. Assumptions and dependencies on BRD
5. Functional requirements (FR-###)
6. Data contracts at the system boundary
7. Non-functional requirements
8. Acceptance criteria per FR
9. Evaluation plan
10. Demo plan
11. Operational and compliance constraints (referenced from BRD §8)
12. Open questions and decisions deferred
13. Traceability matrix (BR → FR)
14. Glossary delta (PRD-only terms not in BRD glossary)
15. Appendices (cross-references, change log)

## In-topic questions

### Section 1 — Document control and purpose

#### Q1.1 — One-paragraph purpose
What does this document do, who reads it, and how does it relate to the BRD and Arch Doc? Source: this brief; BRD §1.

#### Q1.2 — Out-of-scope statements
State explicitly what this PRD does *not* cover (component design, deployment topology, vendor selection, internal data models inside components). Source: scope-discipline rule above.

*Write Section 1 last after the rest is stable.*

### Section 2 — User roles and primary journeys

#### Q2.1 — Roles
Who interacts with the prototype? At minimum: **Reviewer (label specialist)**, **Supervisor (informational, observes but does not act in MVP)**, **System administrator (deployment-time only)**. Note: only personas who interact with the *system* are roles; sponsors (Sarah at the program level) are stakeholders, not user roles. Source: T8 user-role discussion; T10 stakeholder roster filtered to system users.

#### Q2.2 — Primary journey: single-label review
Walk through the journey from "reviewer opens the prototype" to "disposition reached." Use T8's stage 1–3 sequence as the anchor, plus T8 Q8.8 demo path. Source: T8 §Q8.8; D-011.

#### Q2.3 — Secondary journey: batch review
Walk through batch upload, lookahead behavior, mid-batch override, completion. Source: T8 stage 5; T6 §Q6.1–Q6.5; D-010.

#### Q2.4 — Failure-recovery journey: needs-better-photo
Walk through what the reviewer sees when extraction confidence is too low. Source: T4 Q4.6; T8 stage 4 (fixture-04); D-007 needs-review semantics.

#### Q2.5 — Override journey
Walk through what the reviewer does when they disagree with a system disposition. Three keystrokes per Dave's empathy map (`O → reason → ENTER`) and T8 stage 2. Source: T8 stage 2 + Stage 6; T10 Q10.5 ("30-second test").

### Section 3 — Scope

*Lift from BRD §6 in functional language. The BRD said "wine, spirits, malt at common-fields level"; the PRD says "the system shall accept and process applications declaring beverage class wine, spirits, or malt." Same scope, functional voice.*

#### Q3.1 — In-scope (MVP)
Lift S2 D-010 MVP rows in functional language. Anchor on the seven common fields (brand, class/type, ABV, net contents, bottler name+address, country of origin, government warning) and the spirits-deep rule pack per D-012. Source: S2 D-010; BRD §6.1; D-012.

#### Q3.2 — Stretch
Lift S2 D-010 stretch in functional language: wine depth (vintage/AVA/appellation/sulfite), malt depth (SoC/formula matching), batch-mode demo at importer-drop scale, calibrated needs-review routing, network-failure recovery demo. Source: S2 D-010; BRD §6.2.

#### Q3.3 — Out of scope
Lift S2 D-010 out-of-scope plus the explicit additions in BRD §6.3: COLAs Online integration, allowable-revisions review, post-approval change auditing, conditional fields (sulfite, organic, FD&C Yellow #5, cochineal/carmine, major-allergen), beverages outside Parts 4/5/7. Source: BRD §6.3; D-003; D-010; take-home Marcus.

### Section 4 — Assumptions and dependencies on BRD

#### Q4.1 — Assumed BRD positions
What the PRD treats as settled because the BRD says so: scope envelope (BRD §6), value framing (BRD §1.3, §7.8), compliance tier (BRD §8.2), stakeholder priority (BRD §4.3 / D-001), constraints register (BRD §9.1). List them; do not re-argue them. Source: BRD §3, §4, §6, §8, §9.

#### Q4.2 — Conflicts surfaced during PRD authoring
If anything in research or in the take-home conflicts with the BRD, log it here and route back to S6 (not papered over in the PRD). Empty on first issue. Source: ground-truth rule.

### Section 5 — Functional requirements

*Format: FR-### with one-line statement, rationale (one sentence), source, tier (Hard/Strong/Medium/Stretch from `01-requirements.md`), trace to BR (the BRD's Section 5), and a pointer to acceptance criteria in §8. Each FR is one externally observable behavior. Implementation specifics — algorithms, libraries, thresholds — go in the Arch Doc, not here.*

#### Q5.1 — Field-extraction requirements (FR-001 series)
For each field on the common-fields manifest, what extraction does the system perform? Brand, class/type, ABV, net contents, government warning text, government-warning typography (caps + bold per 27 CFR §16.22(a)(2)), bottler/importer name-and-address, country of origin (imports). For each field: what the system extracts at the boundary (the structured output the reviewer-facing surface presents), not how it extracts. Source: T4 Q4.1 (the field × extraction-property table); T1 §1.1 manifest; take-home tech requirements.

#### Q5.2 — Application-data ingest requirements (FR-100 series)
What does the system accept as application input? Form 5100.31 fields (items 1–18 per T2 Q2.1), label images (JPEG/PNG accepted; TIFF/PDF rejected per COLAs Online posture), batch envelope, perjury attestation field, applicant-vs-third-party-rep distinction. Source: T2 Q2.1 (full field schema), T2 Q2.10 (recommended JSON shape), T2 Q2.3 (artwork formats); D-010.

#### Q5.3 — Rule evaluation requirements (FR-200 series)
For each rule in S5's MVP rule manifest, the system shall produce a per-rule disposition with rule citation. Group by Common (Part 16), Wine (Part 4), Spirits (Part 5), Malt (Part 7). For each rule list rule_id, CFR citation, reason code, trigger condition, and tier. Specific anchors:
- ABV tolerances: spirits ±0.3 pp (§5.65(c)), malt ±0.3 pp + §7.65(c) hard 0.5% floor, wine ±1.0 pp >14% / ±1.5 pp ≤14% (§4.36(b)(1)) with §4.36(c) class-boundary anti-overlap (D-006; S5 §1).
- Government warning: verbatim text per §16.21; heading caps+bold per §16.22(a)(2); contrasting background per §16.22(a)(1); type-size minima per §16.22(b); CPI maximum per §16.22(a)(4) — encoded as cardinal table with `interpolation: none` per T3 §Q3.4 / S5.
- Spirits-deep extras: class/type vs. §5 Standard of Identity; age statement floor per D-012 / S2.

Source: S5 §1 final per-class MVP rule list; T1 §3 (warning specification); T1 §1.1 (field manifest); D-006 (ABV); D-012 (spirits depth).

#### Q5.4 — AI-orchestration requirements (FR-300 series)
What tasks does the AI orchestration layer perform, expressed as functional requirements? Three tasks per T5: (a) brand-name borderline disambiguation (only when the rule engine has emitted needs-review on the brand-name field), (b) reasoning-text enrichment (paraphrase template-derived reasoning into plain language), (c) OCR multi-reading reconciliation (when vision layer surfaces multiple plausible reads with no clear winner). The AI orchestrator does not decide pass/fail (D-002); it never flips a fail to pass; safe-failure mode is `needs_review` (T5 §Q5.10). Source: T5 Q5.1, §Recommendation #4; D-002.

#### Q5.5 — Batch processing requirements (FR-400 series)
How the system handles batch submissions: first label processed individually under the single-label latency budget; lookahead k = 2–3 (per T6 §Q6.2 open-loop recommendation for one-agent prototype; specific value is configuration, not FR); agent controls cadence (pull-based, reactive-streams `request(n)` semantics); mid-batch override does not stop the queue under the independence assumption; soft anomaly prompt fires on M-of-N consecutive same-reason fails. The PRD specifies the *behavior* (pull-based, no-stop-on-override, soft-anomaly-prompt); the Arch Doc specifies the *primitive* (asyncio.Queue, EWMA, etc.). Source: T6 §Q6.1–Q6.5; D-010.

#### Q5.6 — UX requirements (FR-500 series)
What surfaces the reviewer interacts with, lifted from T8's 17-component inventory: field-card grid (C-FieldCard), bbox overlay (C-BboxOverlay), evidence panel with citation chips (C-EvidencePanel, C-CitationChip), rule verdict block (C-RuleVerdict), AI suggestion block visibly separated from rule verdict (C-AISuggestionBlock), override drawer with reason-code picker (C-OverrideDrawer, C-ReasonCodePicker), needs-better-photo card (C-NeedsBetterPhotoCard), alerts/toasts (C-Alert, C-Toast), live region for screen readers (C-LiveRegion), raw-JSON drawer gated by DEV_MODE (C-RawJSONDrawer), batch table with sortable disposition (C-BatchTable, C-QueuePosition), confidence indicator (C-ConfidenceIndicator), disposition pill (C-DispositionPill). The PRD names the surface and its behavior; CSS, framework, and DOM specifics are S3/Arch-Doc material. Source: T8 component inventory; S3 D-013 (stack-shape boundary).

#### Q5.7 — Image-handling requirements (FR-600 series)
Accepted formats (JPEG, PNG); rejection of unsupported formats (TIFF, PDF) with a clear error message routed via C-Alert; minimum DPI for measurement-bearing rules (warning type-size lookup); needs-better-photo as a first-class disposition with a structured `WARNING_OR_FIELD.LEGIBILITY.LOW_RESOLUTION` (or equivalent) reason; no persistent storage beyond session; image is held in memory only for the duration of the disposition. Source: T2 Q2.3; T4 Q4.6; T3 §Q3.10 (`ENGINE.MEASUREMENT.MISSING_DPI`); 01-requirements.md Strong tier `[DATA]`; BRD §8.4.

#### Q5.8 — Disposition output requirements (FR-700 series)
Three-state per-label disposition (pass / fail / needs-review); per-field finding with extracted value, expected value, evidence (bbox + crop reference), CFR citation, structured reason code, plain-language explanation, confidence band (high/medium/low) plus numeric confidence; reason-code grammar `BIN.SUB.SPECIFIC[.QUALIFIER]` per T8 / S5; audit-trail object per disposition containing `evaluation_id`, `rule_set_version`, `model_version`, `prompt_version`, `input_hash`, `output_hash`, timestamps, and the full per-rule trace. Source: D-007; T3 §Q3.4 RejectionReason model; T1 §7.3 reason-code bins; T8 disposition-pill spec; S5 confirmation of confidence min-aggregation as the engine semantic (the *value* aggregation is FR; the implementation is Arch).

#### Q5.9 — Override and manual-review requirements (FR-800 series)
Reviewer may override any disposition at any time with structured reason code; override of the system's disposition is recorded in the session audit trail; manual review path is always reachable (independent of AI availability); override completes in three keystrokes (`O → reason → ENTER`) for the canonical case. Source: 01-requirements.md Strong tier `[UX]`; T8 stage 2; T10 Q10.5.

#### Q5.10 — Engine failure-mode requirements (FR-900 series)
The system shall never silently degrade to a pass; engine-internal failures emit a needs-review with a structured engine-error reason code from the T3 §Q3.10 taxonomy. Specifically: missing application data, missing label image, conflicting rules, ambiguous OCR, unknown beverage class, class disagreement (application vs. label), rule-set version mismatch, validator exception, per-rule timeout, whole-evaluation timeout. Each maps to a specific reason code (e.g., `ENGINE.INPUT.APPLICATION_MISSING`, `ENGINE.VALIDATOR.TIMEOUT`). Source: T3 §Q3.10 taxonomy; D-007.

### Section 6 — Data contracts at the system boundary

*The PRD owns the wire-format contracts (what the system accepts and emits at its external surface). The internal types (e.g., the in-process Pydantic `FieldObservation` class) live in the Arch Doc.*

#### Q6.1 — Application-input contract
JSON envelope mirroring Form 5100.31 items 1–18 plus a `labels: []` array of image references with face-tag (front/back/neck/side) and dimensions. Optional `formula: {ttb_formula_id, approval_date}` for products requiring pre-COLA evaluation. Schema *shape* only; do not commit to JSON Schema draft version (Arch Doc concern). Source: T2 Q2.10 recommendation; D-010.

#### Q6.2 — Disposition-output contract
The shape of what the system returns per label: per-rule findings, per-field evidence, overall disposition (pass/fail/needs-review), confidence band + numeric, audit-trail object, citations, reason codes. Reason-code grammar is part of the contract. Default-visible vs. drawer-visible split per T8 Q8.11. Source: T3 §Q3.4 RejectionReason; T8 Q8.11; D-007.

#### Q6.3 — Batch envelope contract
Wrapping for batch submissions and progressive results: batch identifier, agent_id (always set, single value in MVP per T6 Q6.7 multi-agent-aware-but-not-multi-agent), per-label streaming result envelope, queue-position metadata. Source: T6 Q6.7; T8 C-BatchTable.

#### Q6.4 — Error contract
The shape of errors at the boundary: rejected input (malformed JSON, missing required field, unsupported image format), engine failure (timeout, validator exception), partial completion (some labels in batch processed, others stalled). All errors carry a structured reason code from the T3 §Q3.10 taxonomy. Source: T3 §Q3.10; T8 C-Alert.

### Section 7 — Non-functional requirements

#### Q7.1 — Performance
NFR-PERF-001: ~5-second response time per single-label review (Hard; take-home Sarah verbatim; 01-requirements.md). NFR-PERF-002: batch lookahead does not block first-label response. NFR-PERF-003: P50 single-label processing ≤ 2.7s; P99 ≤ 5.0s under demo conditions per T6 TL;DR. Source: BRD BR-010, BR-011; T6.

#### Q7.2 — Usability
NFR-UX-001: senior-friendly UI (73-year-old benchmark). NFR-UX-002: keyboard-operable end-to-end. NFR-UX-003: override reachable in three keystrokes for the canonical case. Source: BRD BR-012, BR-013, BR-014; T8 keyboard model.

#### Q7.3 — Accessibility
NFR-A11Y-001: WCAG 2.0 AA conformance under the Revised 508 Standards (the legal floor; T7 §Q7.16 baseline). WCAG 2.1/2.2 success criteria from T8 (1.4.10 reflow, 1.4.11 non-text contrast, 1.4.13 hover-reveal, 2.5.5/2.5.7/2.5.8 target sizes, 2.4.11/2.4.12 focus appearance, 4.1.3 status messages) are design targets, not regulatory minima. NFR-A11Y-002: VPAT issued for the prototype at WCAG 2.0 AA / Revised 508 Standards mapping. NFR-A11Y-003: reduced-motion media query honored; state changes never signaled by motion alone. NFR-A11Y-004: layout reflows to 320 CSS px without two-dimensional scrolling. Source: T7 §508; T8 §Conformance testing posture; T8 §Reduced motion; T8 §Reflow.

#### Q7.4 — Auditability
NFR-AUDIT-001: every disposition produces an audit record per BR-009. The shape of the record is in §6.2; the persistence story (or lack thereof — session-only) is in §7.7. Source: BRD BR-009; D-007.

#### Q7.5 — Substitutability (production-parity)
NFR-PORT-001: the system shall be deployable in environments that block outbound cloud calls (BR-015 functional restatement). NFR-PORT-002: the system shall support a deployment mode in which inference runs on-prem (BR-016 functional restatement). The PRD says *that*; the Arch Doc says *how* (per S3 D-015 dual-mode `VISION_MODE={local,cloud,auto}`). Source: BRD BR-015, BR-016; S3 D-015.

#### Q7.6 — Determinism
NFR-DET-001: re-running the system on the same inputs within a session produces the same disposition. Cross-session determinism is out of scope per `05-gaps-and-limitations.md` and T5 Q5.10 (the prototype has no persistent storage; session-only canonicalized cache). The limitation is documented per T5 §Q5.10 mitigations. Source: T5 Q5.10.

#### Q7.7 — Data handling
NFR-DATA-001: no persistent storage of submitted artwork beyond session. NFR-DATA-002: audit records exist in-memory for the session and are not persisted to disk in the prototype tier. Source: BRD §8.4; 01-requirements.md Strong tier `[DATA]`; 05-gaps-and-limitations.md.

### Section 8 — Acceptance criteria per FR

*Format: AC-FR-### linked to FR-###. Each AC is a testable statement. Hard-tier FRs have at least one positive and one negative AC; Strong-tier FRs have at least one each where reasonable; Stretch FRs may have only a positive AC.*

#### Q8.1 — Demo-fixture acceptance
The six S2 / D-011 demo fixtures map to specific ACs:
- Fixture-01 (clean spirits happy path) → AC-FR-200 series pass; AC-NFR-PERF-001 (<2s observable);
- Fixture-02 (STONE'S THROW Bourbon) → AC-FR-200 brand normalized-pass per S2 recommended Stage 2 narration update;
- Fixture-03 (title-case "Government Warning") → AC-FR-200 fail with `WARNING.STYLE.HEADING_NOT_BOLD_CAPS` and 27 CFR §16.22(a)(2) citation;
- Fixture-04 (low-res unreadable) → AC-FR-600 needs-better-photo with structured reason;
- Fixture-05 (batch of 50) → AC-FR-400 first label returns under the latency bar; lookahead behavior visible;
- Fixture-06 (ABV out-of-tolerance) → AC-FR-200 fail with citation; AC-FR-800 override completes in three keystrokes.

Source: S2 D-011; T8 fixtures 01–06; S2 §Recommend updating T8 Stage 2 narration.

#### Q8.2 — Stakeholder-signal acceptance
Map each persona's signal to an AC: Sarah's <2s on Stage 1 first label (NFR-PERF-001); Dave's STONE'S THROW resolved at Stage A normalization with no reviewer override required (FR-200 brand-name + S2 recommendation); Jenny's title-case warning case fired with the right reason code and CFR citation chain (FR-200 + FR-700). Source: T10 Q10.4–Q10.5; S2 §Recommendation.

#### Q8.3 — Per-rule acceptance
For each MVP rule in S5, an AC pair (positive case passes; canonical negative case fails with the right reason code and citation). Boundary cases for tolerance rules (ABV exactly at limit, exactly outside, edge of class boundary). Source: S4 §Evaluation acceptance criteria; T9 Q9.8.

#### Q8.4 — Evaluation acceptance (corpus-level)
- Disposition macro-F1 ≥ 0.70 on full eval (MVP gate); ≥ 0.85 (v1 gate).
- Per-rule recall ≥ 0.80 on government-health-warning rules (R06–R09 equivalent).
- Per-rule positive coverage ≥ 43 cases per rule (95% CI ±15 pp).
- Happy-path coverage ≥ 97 fully-compliant labels.

Source: S4 §Evaluation acceptance criteria.

#### Q8.5 — Performance acceptance
NFR-PERF-001 demonstrated against fixture-01: P50 ≤ 2.7s wall-clock; P99 ≤ 5.0s under demo conditions. NFR-PERF-002 demonstrated against fixture-05: first label of 50-batch returns under the bar. Source: T6 TL;DR; BR-010, BR-011.

#### Q8.6 — Accessibility acceptance
Automated axe-core or Pa11y check passes on every PR with zero WCAG 2.0 AA violations on the six demo fixtures. Manual NVDA + VoiceOver smoke test on the field-card and bbox-overlay surfaces passes the keyboard-model exercises in T8. Source: T8 §Conformance testing posture.

### Section 9 — Evaluation plan

*Lift S4 / T9. The PRD specifies what the eval looks like and what passes; the Arch Doc implements the harness.*

#### Q9.1 — Test corpus shape
≥250 labels (worst-case Wald math). Class balance: wine 40–50%, malt 35–45%, spirits 10–20% per S4 acceptance criteria. Synthetic share ≤15% with C2PA metadata and `provenance.source` matching `^synthetic-`. Intra-rater reliability via solo-annotator double-pass with ≥48-hour gap; Krippendorff's α ≥ 0.80 reported with explicit limitation note. Source: S4 §Evaluation acceptance criteria; T9 Q9.1–Q9.4.

#### Q9.2 — Metrics framework
Disposition macro-F1; per-rule precision/recall; per-class small-multiples; calibration (does confidence track accuracy); time-to-disposition. Cost-of-error asymmetry: false-pass weighted higher than false-reject in the headline, per T9 Q9.1 and T3 §Q3.4 brand-name threshold rationale. Source: T9 Q9.1; S4.

#### Q9.3 — Stakeholder-mapped test cases
- Sarah → latency tests across realistic-difficulty inputs;
- Dave → fuzzy-match acceptance set (STONE'S THROW family);
- Jenny → warning-statement adversarial set (case modifications, missing words, font-weight swaps);
- Marcus → security smoke tests appropriate to the prototype tier (no PII in logs, no outbound calls outside whitelist in cloud mode).

Source: T9 Q9.5.

#### Q9.4 — Harness behavior
CI smoke subset (~20 labels) on every PR; full eval on merge to main; nightly scheduled full run with metrics persisted to `eval/history/`; `/eval` dashboard route renders disposition confusion matrix and per-rule P/R table; gated by `DEV_MODE` env flag. Datasheet follows Gebru et al. (2021) seven-section template. Source: S4 acceptance criteria.

### Section 10 — Demo plan

*Lift D-011 directly. The PRD nails down the demo as a delivered acceptance artifact, not as a marketing exercise.*

#### Q10.1 — Demo length and channels
5-minute recorded walkthrough (Loom or equivalent), linked from README. Plus deployed URL (public-readable, no auth gymnastics) reachable for the full 7-stage path including network-failure recovery (which is cut from the 5-min recording for time). Plus source repo + README per take-home deliverable. Hybrid live/cached: pre-warmed orchestrator at T-5 minutes pre-recording; LLM responses cached for the six demo fixtures, narrated transparently. Source: D-011; S2 §10–11.

#### Q10.2 — Six-stage demo path (recorded cut)
1. Clean spirits pass (fixture-01): Sarah signal — speed + simplicity, <2s observable.
2. STONE'S THROW Bourbon (fixture-02): Dave signal — Stage A normalization passes cleanly per S2 recommendation; no override needed.
3. Title-case "Government Warning" fail (fixture-03): Jenny signal — exact reason code + citation.
4. Needs-better-photo (fixture-04): honest failure mode.
5. Batch of 50 (fixture-05): lookahead + queue position + batch table.
6. ABV out-of-tolerance (fixture-06): override demo — three keystrokes.

Source: D-011 §1; T8 Q8.8; S2 §13a.

#### Q10.3 — Demo failure-recovery
Pre-warm strategy: hit `/healthz` and run fixture-01 once at T-5 minutes pre-recording. Cache strategy: LLM responses cached for the six demo fixtures with an in-memory canonicalized-input cache per T5 Q5.10 mitigation #2. Narration discloses caching honestly. Source: D-011 §3; T8 §Demo failure-recovery items 1–2.

### Section 11 — Operational and compliance constraints

*Reference BRD §8 and §9; do not redraw. The PRD's job is to ensure the FRs do not violate those constraints, not to re-derive the constraints.*

#### Q11.1 — Inherited constraints
Cite BRD §8.2 (prototype-tier compliance: no PII storage, no production ATO, no FedRAMP, "just don't do anything crazy"); BRD §8.4 (no persistent storage of submitted artwork beyond session); BRD §9.1 (firewall, latency, UX, standalone). Source: BRD §8, §9.

#### Q11.2 — Compliance-mapped FRs
Which FRs exist *because* of a compliance constraint:
- FR-700 audit-trail object exists because of BR-009 / D-007 audit requirement.
- FR-600 image-handling no-persistence behavior exists because of BRD §8.4 / D-007.
- FR-500 reason-code grammar exists because of D-007 audit-trail readability.
- NFR-PORT-001 exists because of BR-015 / Marcus's firewall constraint.

Source: BRD §8.5; D-007; BR-009, BR-015.

### Section 12 — Open questions and decisions deferred

*Lift from BRD §10.2 plus any new questions surfaced during PRD authoring.*

#### Q12.1 — Inherited open questions
OQ-1 application-input format (mocked JSON for prototype; production answer pending COLAs Online schema access); OQ-2 deployed-URL auth posture; OQ-3 structured reason codes for downstream filtering; OQ-4 confidence representation (numeric vs. tri-state band — partially resolved by T8 default-visible spec); OQ-5 eval-corpus sample selection. Source: BRD §10.2.

#### Q12.2 — PRD-specific open questions
Anything that surfaces during PRD authoring goes here, not buried in prose. Examples to evaluate during authoring:
- Should the override drawer require a free-text justification or just a reason-code selection?
- Are batch-mode failed-label retries automatic or reviewer-initiated?
- Does the audit-trail object include the LLM prompt and response verbatim (T5 / S3 ring-buffer says yes for developer mode), or only structured fields, in production framing?
- For multi-image labels (front + back + neck), what's the disposition-aggregation rule?

### Section 13 — Traceability matrix

#### Q13.1 — BR → FR mapping
Table: BR-001 through BR-018 from BRD §5, mapped to the FR-### that operationalize each. Every BR maps to ≥1 FR; every FR maps to exactly one BR (one-to-many BR→FR; many-to-one FR→BR). Surface fan-out explicitly: e.g., BR-007 (citation-grounded disposition) produces FR-700 series + parts of FR-500 (citation chip in UI) + FR-900 (engine-failure reason codes). Source: BRD §5.

### Section 14 — Glossary delta

#### Q14.1 — PRD-only terms
Terms used in this PRD that are not in the BRD glossary, with one-line definitions: field card, evidence panel, disposition pill, confidence indicator, bbox overlay, citation chip, override drawer, reason-code picker, lookahead, reason code, field manifest, rule pack, FR, NFR, AC, P50, P99, FIFO, EWMA, VPAT. Source: T8 component inventory; T3 §Q3.4; T6; T8 §Conformance testing.

### Section 15 — Appendices

#### Q15.1 — Cross-reference map
Pointers to:
- BRD (`BRD.md` — why we're building, business case)
- Architecture Doc (`ARCHITECTURE.md` — how it's built)
- Decision log (`03-decisions.md`)
- T-outputs in scope: T1, T2, T3, T4, T5, T6, T8, T9
- S-outputs in scope: S2, S3, S4, S5
- Original take-home brief

#### Q15.2 — Change log
PRD version history. Empty on first issue.

## Cross-topic synthesis questions consumed by this session

- **X-2** (where the system falls back to "needs human review" vs "automatic reject" — map the decision tree across components): the PRD is the natural home. §5.10 (engine failure modes) plus §2.4 (needs-better-photo journey) plus §5.8 (disposition output) together resolve it.
- **X-4** (which TTB rules require code logic vs. pure data): the PRD records the *which-rules* answer functionally in §5.3; the *how* (YAML vs. Python escape-hatch) is in the Arch Doc per D-014. Reference but do not redraw.

## Notes for the author

- **The take-home brief wins ties.** Same rule as S6.
- **Functional voice, not implementation voice.** "The system shall accept JPEG and PNG label images" (functional) vs. "The system uses Pillow to decode images" (implementation — Arch Doc). If you find yourself naming a library, a model, an algorithm, or a threshold inside an FR, stop and ask whether that detail is externally observable. If not, move it to the Arch Doc.
- **Match-policy specifics belong in the rule pack, not the PRD.** D-014 settled that match policies live in YAML under `rules/`. The PRD says "the brand-name match policy is fuzzy"; the YAML and the Arch Doc say "Jaro-Winkler ≥ 0.92 → pass, 0.85–0.92 → needs-review." This is the most common scope-leak in PRD authoring; watch for it.
- **Tier every FR.** Use the `01-requirements.md` tier system (Hard / Strong / Medium / Stretch). Tier drives acceptance: Hard FRs must pass to ship; Stretch FRs are nice-to-have. Tier determines AC density in §8.
- **Cite, don't regenerate.** S5 produced the rule manifest with reason codes and CFR citations. Lift it; don't re-derive it. Same for T9/S4 acceptance criteria.
- **One BR may produce many FRs.** Capture the fan-out explicitly in §13. This is the primary value of the traceability matrix.
- **Don't bleed into the BRD.** If you find yourself explaining *why* a requirement exists at length, that's BRD prose — keep the rationale to one sentence and link back to the BR. If you find yourself explaining *how*, that's Arch Doc — stop.
- **Length target: 15–25 pages.** PRDs are longer than BRDs because the FR list itself is long. If it's growing past 25, check whether scope has crept (§3 should still match BRD §6) or whether implementation has leaked (§5 should be free of vendor names, library names, algorithms, and thresholds).
- **New decisions surfaced during writing → ADRs.** Append D-016+ to `03-decisions.md`. Do not bury decisions in the PRD prose.
- **Section ordering is deliberate.** Roles before scope before FRs before contracts before NFRs before AC. Reviewers read top-down; the structure should let them stop reading when they have enough context.
- **Reason-code grammar is shared property.** `BIN.SUB.SPECIFIC[.QUALIFIER]` is set in T8 / S5 and used in FR-700, FR-800, FR-900, the audit-trail object, and the override flow. Define it once in §6.2 and reference everywhere else.

## What this session does *not* produce

- Component design (lives in `ARCHITECTURE.md`, S8 session).
- Vendor selections, library picks, model snapshots, prompts, thresholds, schema versions, framework choices.
- Cost estimates, sensitivity analysis, stakeholder analysis, compliance gradation matrices — all upstream in the BRD or in the Tn-outputs.
- A README — that's a deliverable artifact, downstream of all three docs.
- The rule pack itself — that's a delivered artifact (`rules/*.yaml`), referenced by the PRD's §5.3 manifest but not authored here.
