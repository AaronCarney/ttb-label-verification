# PRD.md — Product Requirements Document
## TTB AI-Powered Alcohol Label Verification Prototype

**Document type:** Product Requirements Document (PRD)
**Owner:** Project sponsor (TTB Alcohol Labeling and Formulation Division — ALFD)
**Audience (primary):** TTB product owner / implementation team building from this spec
**Audience (secondary):** Take-home reviewer evaluating translation of stakeholder constraints into a buildable specification
**Status:** Draft for review — prototype phase
**Companion documents:** `BRD.md` (why we're building it), `ARCHITECTURE.md` (how it's built), `03-decisions.md` (decision log)
**Document version:** 0.5 (eval corpus right-sized for prototype tier; D-018 wire-example erratum applied)

---

## 1. Document Control and Purpose

### 1.1 Purpose

This document specifies *what* the TTB AI-Powered Alcohol Label Verification prototype does — the externally observable behavior an implementation team must deliver. It is read by the product owner who hands it to engineering, by the engineering team building against it, by QA defining acceptance tests, and by the take-home reviewer evaluating whether stakeholder constraints have been correctly translated into a buildable specification. It sits between the BRD (which states business need and value) and the Architecture Document (which states component design and technology choices); every functional requirement (FR) here traces upward to a business requirement (BR) in `BRD.md` §5 and downward to an acceptance criterion in §8.

### 1.2 Out-of-scope statements

This PRD does **not** cover:

- **Component design** (how components decompose, what their internal interfaces are) — see `ARCHITECTURE.md`.
- **Deployment topology** (where servers run, how containers are orchestrated, how scaling works) — see `ARCHITECTURE.md`.
- **Vendor selection, library choices, model identifiers, framework versions** — see `ARCHITECTURE.md`. The PRD is deliberately silent on whether vision is PaddleOCR or Florence-2, whether the LLM is Qwen2.5-VL or GPT-4o, or whether the rule format is YAML or JSON.
- **Internal data models inside components** (in-process Pydantic types, ORM models, queue primitives) — see `ARCHITECTURE.md`.
- **Algorithms, similarity thresholds, timeout values** as numeric constants in the FR text. Where match policies are referenced (e.g., "fuzzy match for brand names"), the policy *category* is functional; the threshold value is implementation and lives in the rule pack and the Architecture Doc.
- **Business case, cost analysis, stakeholder analysis, compliance posture rationale** — all upstream in `BRD.md`.

### 1.3 Reading order

Reviewers should read §2 (roles), §3 (scope), §5 (functional requirements), §8 (acceptance criteria) in that order to understand the prototype's behavior. §6 (data contracts) and §7 (non-functional requirements) elaborate the boundary; §13 (traceability) confirms BR coverage.

---

## 2. User Roles and Primary Journeys

### 2.1 User roles

The prototype recognizes three roles. Only personas who *interact with the system* are roles; project sponsors (e.g., the BRD's Sarah at the program level) are stakeholders, not user roles. (Source: T8 user-role discussion; T10 stakeholder roster filtered to system users; D-001.)

| Role | Definition | Authority in MVP |
|---|---|---|
| **Reviewer (label specialist)** | An ALFD label specialist using the prototype to triage one application or a batch. The "73-year-old benchmark" senior-friendly persona (Sarah/Dave/Jenny composite). | Reads dispositions; overrides any disposition; reaches manual review path at any time. |
| **Supervisor** | An ALFD supervisor observing reviewer activity at an aggregate level. **Informational only in MVP** — the supervisor calibration view is stretch (see §3.2). | Reads aggregate summaries when the stretch supervisor view is enabled; takes no per-application action in MVP. |
| **System administrator** | The operator who deploys and configures the prototype. Acts only at deployment time. | Sets the `VISION_MODE` flag (per D-015), provides API credentials when in cloud mode, runs the eval harness. Not a runtime user. |

### 2.2 Primary journey: single-label review

The reviewer opens the prototype, drops one label image plus its application metadata, and reaches a disposition. The seven-step canonical flow (anchored on T8 stages 1–3 and Q8.8; D-011 demo path):

1. **Open the prototype.** Reviewer navigates to the deployed URL; landing surface is the single-label intake screen with a drop zone and an application-metadata panel.
2. **Submit one label.** Reviewer drags a JPEG/PNG label image into the drop zone and either pastes a JSON application record or selects one from a fixture picker.
3. **Watch progress.** Within ≤ 5 seconds (NFR-PERF-001), the system surfaces a disposition (pass / fail / needs-review) with a per-field card grid.
4. **Read the verdict.** Each field card shows extracted value, expected value, rule verdict (block from the deterministic engine), AI suggestion (visibly separated, only present where AI orchestration ran), CFR citation, and confidence band.
5. **Inspect evidence.** Reviewer clicks a citation chip to open the evidence panel; bbox overlay highlights the region on the label that drove the finding.
6. **Decide.** Reviewer either accepts the system disposition (canonical happy path) or overrides (see §2.5).
7. **Move on.** Reviewer closes the disposition; the audit-trail object is sealed for the session. No persistence beyond session (NFR-DATA-001).

### 2.3 Secondary journey: batch review

The reviewer drops a batch of 50 labels and works through them at human pace while the system pre-fetches the next labels. Anchored on T8 stage 5; T6 §Q6.1–Q6.5; D-010.

1. **Drop the batch.** Reviewer drags a zip or multi-file selection into the batch intake surface.
2. **First label is processed individually** under the single-label latency budget; the reviewer sees a disposition for label 1 before label 2 begins extraction.
3. **Lookahead activates.** The system pre-fetches the next two-to-three labels (k=2–3, configurable; specific value is implementation, see §5.5) so the reviewer does not wait on extraction when they finish label N.
4. **Reviewer proceeds at human pace.** The agent controls cadence; the system uses pull-based demand semantics (`request(n)` style; see NFR-PERF-002) to keep the queue fed without overrunning.
5. **Mid-batch override does not stop the queue.** Under the independence assumption (each application is independent; one override does not invalidate others), processing continues.
6. **Soft anomaly prompt.** If M-of-N consecutive labels in the batch fail with the same reason code, the system surfaces a non-blocking advisory ("you've rejected 4 of the last 5 for missing health warning — flag the source?"). Reviewer dismisses or acknowledges; processing continues either way.
7. **Batch completion.** Reviewer sees the batch table with sortable disposition column; closes the batch.

### 2.4 Failure-recovery journey: needs-better-photo

The reviewer drops a label whose image quality is too low to extract a measurement-bearing field (e.g., warning-text type-size). Anchored on T4 Q4.6; T8 stage 4 (fixture-04); D-007 needs-review semantics.

1. **Reviewer submits a low-quality label image.**
2. **Vision layer flags low confidence on extraction.** Either OCR confidence below threshold, DPI metadata missing for a measurement-bearing rule, or glare/angle obscures the warning region.
3. **System emits needs-review.** Disposition is `needs_review` (not `fail`); the field card shows an amber state, a camera icon, and structured reason `WARNING.LEGIBILITY.LOW_RESOLUTION` (or the appropriate engine-error code from §5.10).
4. **Templated applicant message.** A pre-composed plain-language request ("we need a clearer photograph of the warning region; here's why") is shown alongside the disposition; the reviewer can copy it (sending is stretch in MVP, see §3.2).
5. **Manual review path remains available.** Reviewer can choose to proceed with manual review using the partial extraction.

### 2.5 Override journey

The reviewer disagrees with a system disposition and records an override. Anchored on T8 stage 2 + stage 6; T10 Q10.5 ("30-second test").

1. **Reviewer sees a disposition they disagree with** (e.g., a `needs_review` on brand-name where the reviewer recognizes both forms as the same brand).
2. **Reviewer presses `O`.** Override drawer opens with focus on the reason-code picker.
3. **Reviewer types or selects a reason code.** Reason-code picker is filtered/searchable.
4. **Reviewer presses `ENTER`.** Override is recorded; disposition flips; audit trail records the reviewer-applied disposition, the original system disposition, the reason code, the reviewer identity (session-scoped), and timestamp.
5. **Three-keystroke target met.** `O → reason → ENTER`. (Source: 01-requirements.md Strong tier `[UX]`; T10 Q10.5; the canonical case where the reason code starts with a unique prefix the picker resolves on first keystroke.)

---

## 3. Scope

### 3.1 In-scope (MVP)

Lifted from `BRD.md` §6.1 and S2 D-010 in functional language. The system shall:

- Accept and process applications declaring beverage class **wine** (≥7% ABV under 27 CFR Part 4), **distilled spirits** (Part 5), or **malt beverages** (Part 7).
- Verify the **seven common fields**: brand name, class/type, alcohol content (ABV), net contents, bottler/importer name and address, country of origin (imports only), and the Part 16 government health warning.
- Verify **government-warning specifics**: presence, verbatim text per 27 CFR §16.21, heading caps + bold per §16.22(a)(2), contrasting background per §16.22(a)(1), type-size minima per §16.22(b), CPI maximum per §16.22(a)(4), separate-and-apart placement per §16.21.
- Apply **ABV tolerances** per class: spirits ±0.3 percentage points (27 CFR §5.65(c)); malt ±0.3 pp with a hard 0.5% floor under §7.65(c); wine ±1.0 pp above 14% / ±1.5 pp at or below 14% (§4.36(b)(1)) with class-boundary anti-overlap under §4.36(c).
- Apply a **spirits-deep rule pack** including class/type vs. §5 Standard of Identity recognition and an age-statement floor check (per D-012).
- Surface dispositions with **citations and structured reason codes** following the `BIN.SUB.SPECIFIC[.QUALIFIER]` grammar.
- Support **batch upload** with adaptive lookahead and a sortable batch table.
- Provide a **manual override path** reachable in three keystrokes for the canonical case.
- Emit an **audit-trail object** per disposition.
- Run as a **standalone web-deployable prototype** with no integration into COLAs Online.

### 3.2 Stretch

- **Wine depth**: vintage / AVA / appellation / sulfite-declaration validators.
- **Malt depth**: Statement of Composition (SoC) and formula-matching validators where a TTB Formula ID is supplied.
- **Batch-mode demo at importer-drop scale**: 200–300 labels demonstrating non-degraded latency.
- **Calibrated needs-review routing**: confidence calibration empirically validated on a held-out sample.
- **Automated threshold re-calibration**: the brand-match Jaro-Winkler cutoffs (`pass_threshold`, `needs_review_threshold` per ARCHITECTURE.md §6.11), confidence-band edges (high/medium/low), and BRISQUE/NIQE legibility gates are tuned from eval-corpus performance via a held-out re-calibration sweep, rather than the hand-tuned rule-pack defaults shipped in MVP. Output is a regenerated rule-pack diff for human review, not a runtime auto-update.
- **Network-failure recovery demo**: graceful degradation on transient upstream loss.
- **Supervisor calibration view**: aggregate dispositions and override patterns across a session (no MVP write actions).
- **Templated applicant-message send**: outbound messaging from the needs-better-photo path.

### 3.3 Out of scope

- COLAs Online integration of any kind (no reads, no writes, no auth federation).
- Allowable-revisions review of post-approval label changes.
- Post-approval change auditing or surveillance.
- **Conditional fields**: sulfite declarations, organic claims, FD&C Yellow #5, cochineal/carmine, major-allergen disclosures (deferred per D-003 and Notice 238 status).
- Beverages outside Parts 4/5/7 (e.g., wines <7% ABV under FDA, certain saké formulations).
- Any production ATO claim, FedRAMP package, or PIV/SAML integration.
- Rule changes via UI; the rule pack is configuration shipped with the build (D-014).
- **Internationalization / localization.** English-only UI and English-only OCR/extraction in MVP; multilingual label support deferred. (Source: take-home brief; no persona signal for non-English; T1 manifest is anchored to English-language regulatory text.)

### 3.4 Success Metrics — BO-to-FR mapping

The PRD operationalizes the BRD's four business objectives (BRD §3.1, BO-1 through BO-4). This table is the accountability bridge: each BO names the FRs/NFRs that move it and the AC that demonstrates movement at prototype acceptance.

| BO | Dimension | Target horizon | FRs/NFRs that move it | Prototype-acceptance AC |
|---|---|---|---|---|
| **BO-1** | Throughput — reviewer minutes saved per simple application | Post-pilot steady state | NFR-PERF-001, NFR-PERF-003, FR-401, FR-402, FR-503, FR-803 | AC-NFR-PERF-001 (≤5s single label); AC-FR-803 (3-keystroke override); §8.2 Sarah signal |
| **BO-2** | Accuracy — agreement between system and reviewer disposition | Prototype acceptance + steady state | FR-200 series (rule manifest), FR-300, FR-303, FR-704, NFR-DET-001 | AC-FR-200 series (per-rule positive/negative); §8.4 corpus-level (macro-F1 ≥ 0.70 MVP gate, ≥ 0.80 recall on warning rules) |
| **BO-3** | Adoption — reviewer concurrence rate, especially Dave-class skeptics | 12–24 months post-pilot | FR-301, FR-303, FR-500, FR-502, FR-503, FR-800–FR-804 | §8.2 Dave signal (STONE'S THROW resolved without override); §8.2 Jenny signal (warning fail with citation chain); demonstrated in §10 demo plan |
| **BO-4** | Compliance — every disposition carries CFR-cited explanation | Prototype acceptance | FR-701, FR-702, FR-703, NFR-AUDIT-001, NFR-AUDIT-002 | AC-FR-701 (per-field finding shape); AC-FR-703 (audit-trail object present); 100% of dispositions, no exceptions |

The MVP gate is BO-4 (100% citation grounding) plus BO-2 (macro-F1 ≥ 0.70 on the §9 corpus). BO-1 and BO-3 are pilot-phase measurements; the prototype demonstrates *capability* for both via the §10 demo plan but does not produce steady-state metrics.

*Source: BRD §3.1; T11 Q11.7; D-009 (range-based reporting).*

---

## 4. Assumptions and Dependencies on the BRD

### 4.1 Assumed BRD positions

This PRD does not re-argue what the BRD has settled. It treats as established:

- **Scope envelope** (BRD §6): wine / spirits / malt at the common-fields level; class-specific deferrals; explicit out-of-scope list.
- **Value framing** (BRD §1 "Headline value" paragraph, §7.8): labor-capacity rather than budget-cut framing; range-based, sensitivity-tested recommendation.
- **Compliance posture** (BRD §8.2): prototype-tier, no PII, no production data, no ATO claim, no FedRAMP package.
- **Stakeholder priority** (BRD §4.3 / D-001): phase-dependent — Sarah, Dave, Jenny, Marcus dominate at prototype phase; CIO/FedRAMP/OMB emerge at production phase.
- **Constraints register** (BRD §9.1): time-boxed build, federal firewall, five-second latency ceiling, senior-friendly UX bar, standalone deployment.
- **Business requirements** (BRD §5): BR-001 through BR-018 are the authoritative business-need anchors that this PRD operationalizes.

### 4.2 Conflicts surfaced during PRD authoring

None at first issue. Where new conflicts surface during implementation, they route back to S6 (BRD revision) rather than being papered over here. (Source: ground-truth rule; the take-home brief wins ties; the BRD wins ties against research outputs.)

---

## 5. Functional Requirements

**Format.** Each FR has: ID, single-line statement, one-sentence rationale, source, tier (Hard/Strong/Medium/Stretch from `01-requirements.md`), trace to BR, and pointer to acceptance criteria in §8. Each FR specifies one externally observable behavior. Implementation specifics (algorithms, libraries, thresholds) are in `ARCHITECTURE.md` and the rule pack (D-014).

### 5.1 Field-extraction requirements (FR-001 series)

For each field on the common-fields manifest, the system shall present the structured output described below at the reviewer-facing surface. *How* extraction occurs (which OCR engine, which VLM) is in `ARCHITECTURE.md`.

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-001** | The system shall extract the **brand name** from the label and present its text, bounding box, and per-field confidence. | Hard | BR-001 | AC-FR-001 |
| **FR-002** | The system shall extract the **class/type designation** from the label and present its text, bounding box, and per-field confidence; for spirits, the extraction shall identify the candidate Standard-of-Identity match. | Hard (presence); Strong (SoI candidate, spirits-deep) | BR-002, BR-017 | AC-FR-002 |
| **FR-003** | The system shall extract the **alcohol-content statement** (ABV / ALC/VOL) including its numeric value and unit, bounding box, and per-field confidence. | Hard | BR-002 | AC-FR-003 |
| **FR-004** | The system shall extract the **net-contents statement** including its numeric value, unit, and bounding box. | Hard | BR-003 | AC-FR-004 |
| **FR-005** | The system shall extract the **government-warning text** as a contiguous string with bounding box. | Hard | BR-004 | AC-FR-005 |
| **FR-006** | The system shall extract **typographic properties** of the warning heading: capitalization, bold weight, type size in millimeters (where DPI metadata is sufficient), and contrasting-background indicator. | Hard (caps + bold); Stretch (type size, contrast) | BR-004 | AC-FR-006 |
| **FR-007** | The system shall extract the **bottler/importer name-and-address block** as a structured address (name, street, city, state/region) with bounding box. | Hard | BR-005 | AC-FR-007 |
| **FR-008** | The system shall extract the **country-of-origin statement** for imported applications and present its text and bounding box. | Hard (imports only) | BR-006 | AC-FR-008 |

*Source: T4 Q4.1 (field × extraction-property table); T1 §1.1 manifest; take-home tech requirements; S5 §1 rule manifest.*

### 5.2 Application-data ingest requirements (FR-100 series)

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-100** | The system shall accept an **application input record** mirroring TTB Form 5100.31 (rev. 04/2023) items 1–18 (see §6.1 for the boundary contract). | Hard | BR-001 through BR-006 | AC-FR-100 |
| **FR-101** | The system shall accept **label artwork** in JPEG and PNG formats. | Hard | BR-001 | AC-FR-101 |
| **FR-102** | The system shall **reject TIFF and PDF** label images at intake with a structured error reason code; rejection is signaled to the reviewer via a non-modal alert that names the supported formats. | Hard | BR-001 | AC-FR-102 |
| **FR-103** | The system shall accept a **batch envelope** wrapping one or more application+label pairs (see §6.3). | Strong | BR-011 | AC-FR-103 |
| **FR-104** | The system shall accept the **perjury attestation** field as a Boolean-or-equivalent indicator on the application record but does not validate the attestation. | Medium | BR-001 | AC-FR-104 |
| **FR-105** | The system shall preserve the **applicant-vs-third-party-representative distinction** on the application record (Item 1 REP. ID. NO. when present indicates third-party filing). | Medium | BR-005 | AC-FR-105 |
| **FR-106** | The system shall accept an **optional formula reference** (`{ttb_formula_id, approval_date}`) for products requiring pre-COLA evaluation. | Stretch | BR-018 | AC-FR-106 |

*Source: T2 Q2.1 (full field schema, rev. 04/2023); T2 Q2.10 (recommended JSON shape); T2 Q2.3 (artwork formats); D-010. The form's current field set was confirmed against `https://www.ttb.gov/system/files/images/pdfs/forms/f510031.pdf` (rev. 04/2023, OMB No. 1513-0020).*

### 5.3 Rule-evaluation requirements (FR-200 series)

For each rule in the MVP rule manifest (lifted from S5 §1), the system shall produce a per-rule disposition (pass / fail / needs-review) with rule_id, CFR citation, structured reason code, and evidence reference. Tiers and reason codes use the `BIN.SUB.SPECIFIC[.QUALIFIER]` grammar (T8 / S5).

#### 5.3.1 Common (Part 16 — applies to all classes)

| FR | rule_id | CFR | Reason code | Tier |
|---|---|---|---|---|
| **FR-200** | `common.warning.present` | §16.21 | `WARNING.PRESENCE.MISSING` | Hard |
| **FR-201** | `common.warning.verbatim` | §16.21 | `WARNING.VERBATIM.MISMATCH` | Hard |
| **FR-202** | `common.warning.heading_caps_bold` | §16.22(a)(2) | `WARNING.STYLE.HEADING_NOT_BOLD_CAPS` | Hard |
| **FR-203** | `common.warning.contrasting_bg` | §16.22(a)(1) | `WARNING.LEGIBILITY.NO_CONTRAST` | Stretch |
| **FR-204** | `common.warning.type_size_min` | §16.22(b) | `WARNING.TYPE_SIZE.UNDER_MIN` | Stretch |
| **FR-205** | `common.warning.cpi_max` | §16.22(a)(4) | `WARNING.TYPE_SIZE.CPI_EXCEEDED` | Stretch |
| **FR-206** | `common.warning.separate_apart` | §16.21 | `WARNING.PLACEMENT.NOT_SEPARATE` | Medium |

CPI, type-size, and contrast checks are encoded as cardinal decision tables with `interpolation: none` semantics — the value is looked up, not interpolated (per T3 §Q3.4 / S5).

#### 5.3.2 Wine (Part 4)

| FR | rule_id | CFR | Reason code | Tier |
|---|---|---|---|---|
| **FR-210** | `wine.brand.present` | §4.32(a)(1), §4.33 | `BRAND.PRESENCE.MISSING` | Hard |
| **FR-211** | `wine.class_type.present` | §4.32(a)(2), §4.34 | `CLASS_TYPE.PRESENCE.MISSING` | Hard |
| **FR-212** | `wine.alcohol.present_or_table` | §4.32(b)(1), §4.36(a) | `ALCOHOL_CONTENT.PRESENCE.MISSING` | Hard |
| **FR-213** | `wine.alcohol.format` | §4.36(b)(1) | `ALCOHOL_CONTENT.FORMAT.INVALID` | Strong |
| **FR-214** | `wine.alcohol.tolerance_band` | §4.36(b)(1) | `ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND` | Strong (±1.0 pp >14%; ±1.5 pp ≤14%) |
| **FR-215** | `wine.alcohol.no_class_boundary_cross` | §4.36(c) | `ALCOHOL_CONTENT.TOLERANCE.CROSSES_CLASS_BOUNDARY` | Strong |
| **FR-216** | `wine.name_address.present` | §4.32(a)(3), §4.35 | `NAME_ADDRESS.PRESENCE.MISSING` | Hard |
| **FR-217** | `wine.net_contents.present` | §4.32(b)(2), §4.37 | `NET_CONTENTS.PRESENCE.MISSING` | Hard |

#### 5.3.3 Distilled spirits (Part 5)

| FR | rule_id | CFR | Reason code | Tier |
|---|---|---|---|---|
| **FR-220** | `spirits.brand.present` | §5.63(a), §5.64 | `BRAND.PRESENCE.MISSING` | Hard |
| **FR-221** | `spirits.class_type.present` | §5.63(a), Subpart I | `CLASS_TYPE.PRESENCE.MISSING` | Hard |
| **FR-222** | `spirits.class_type.matches_soi` | §5 Subpart I (Standards of Identity) | `CLASS_TYPE.SOI.NO_MATCH` | Strong (spirits-deep per D-012) |
| **FR-223** | `spirits.alcohol.present` | §5.63(a), §5.65(a) | `ALCOHOL_CONTENT.PRESENCE.MISSING` | Hard |
| **FR-224** | `spirits.alcohol.format` | §5.65(b) | `ALCOHOL_CONTENT.FORMAT.INVALID` | Strong |
| **FR-225** | `spirits.alcohol.tolerance_band` | §5.65(c) | `ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND` | Hard (±0.3 pp) |
| **FR-226** | `spirits.same_field_of_vision` | §5.63(a) | `LEGIBILITY.FIELD_OF_VISION.SPLIT` | Medium |
| **FR-227** | `spirits.name_address.present` | §5.63(b)(1), §5.66/§5.67/§5.68 | `NAME_ADDRESS.PRESENCE.MISSING` | Hard |
| **FR-228** | `spirits.net_contents.present` | §5.63(b)(2), §5.70 | `NET_CONTENTS.PRESENCE.MISSING` | Hard |
| **FR-229** | `spirits.age_statement.floor` | §5.74 (where applicable) | `AGE_STATEMENT.FLOOR.MISSING` | Strong (spirits-deep per D-012) |

#### 5.3.4 Malt beverages (Part 7)

| FR | rule_id | CFR | Reason code | Tier |
|---|---|---|---|---|
| **FR-230** | `malt.brand.present` | §7.63(a)(1), §7.64 | `BRAND.PRESENCE.MISSING` | Hard |
| **FR-231** | `malt.class_type.present` | §7.63(a)(2), Subpart I | `CLASS_TYPE.PRESENCE.MISSING` | Hard |
| **FR-232** | `malt.alcohol.conditional_required` | §7.63(a)(3) | `ALCOHOL_CONTENT.PRESENCE.MISSING` | Hard (conditional on state law / ABV range) |
| **FR-233** | `malt.alcohol.format` | §7.65(b) | `ALCOHOL_CONTENT.FORMAT.INVALID` | Strong |
| **FR-234** | `malt.alcohol.tolerance_band` | §7.65(c) | `ALCOHOL_CONTENT.TOLERANCE.OUT_OF_BAND` | Hard (±0.3 pp) |
| **FR-235** | `malt.alcohol.floor_05` | §7.65(c) | `ALCOHOL_CONTENT.TOLERANCE.BELOW_HARD_FLOOR` | Hard (0.5% hard floor; not relaxed by tolerance) |
| **FR-236** | `malt.name_address.present` | §7.63(a)(4), §7.66/§7.67/§7.68 | `NAME_ADDRESS.PRESENCE.MISSING` | Hard |
| **FR-237** | `malt.net_contents.present` | §7.63(a)(5), §7.70 | `NET_CONTENTS.PRESENCE.MISSING` | Hard |

#### 5.3.5 Brand-name match policy

**FR-240** — The brand-name validator shall use a fuzzy-match policy that recognizes brand-name variants differing only in case or punctuation as a pass disposition; brand-name variants that differ in word order, root tokens, or substantive content shall surface as `needs_review` for AI orchestration disambiguation (see FR-300). *Tier: Strong. BR: BR-001 + Dave-class skepticism mitigation per D-005, D-012. Note: specific algorithm and threshold values are implementation, captured in the rule pack (D-014) and the Architecture Doc.*

*Source for §5.3: S5 §1 final per-class MVP rule list; T1 §3 (warning specification); T1 §1.1 (field manifest); D-006 (ABV tolerances); D-012 (spirits depth, brand match policy).*

### 5.4 AI-orchestration requirements (FR-300 series)

The AI orchestration layer performs three tasks. It does **not** decide pass/fail (D-002); it never flips a fail to pass; its safe-failure mode is `needs_review` (T5 §Q5.10).

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-300** | The AI orchestrator shall perform **brand-name borderline disambiguation** when, and only when, the rule engine has emitted `needs_review` on the brand-name field. | Strong | BR-001 | AC-FR-300 |
| **FR-301** | The AI orchestrator shall perform **reasoning-text enrichment**: paraphrase template-derived rule reasoning into plain language for reviewer-facing display. The original template-derived text is preserved in the audit trail; the enriched text is presented in the AI-suggestion block visibly separated from the rule verdict block. | Strong | BR-007, BR-014 | AC-FR-301 |
| **FR-302** | The AI orchestrator shall perform **OCR multi-reading reconciliation** when the vision layer surfaces multiple plausible reads of a single field with no clear winner; reconciliation may resolve to one read or escalate to `needs_review`. | Medium | BR-008 | AC-FR-302 |
| **FR-303** | The AI orchestrator shall **never override a rule-engine `fail` into a `pass`**; AI suggestions that disagree with a rule-engine fail are recorded in the audit trail but do not change the disposition. | Hard | BR-007, D-002 | AC-FR-303 |
| **FR-304** | When AI orchestration is unavailable (model endpoint down, timeout), the rule engine shall continue to function; AI-orchestration tasks shall return `needs_review` with reason code `ENGINE.MODEL.UNAVAILABLE`. | Hard | BR-013, BR-015 | AC-FR-304 |

*Source: T5 Q5.1, §Recommendation #4; D-002.*

### 5.5 Batch processing requirements (FR-400 series)

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-400** | The system shall accept a **batch submission** of multiple labels and process them under the same per-label rules as single-label review. | Strong | BR-011 | AC-FR-400 |
| **FR-401** | The **first label of a batch** shall be processed individually under the single-label latency budget (NFR-PERF-001). | Strong | BR-010, BR-011 | AC-FR-401 |
| **FR-402** | The system shall apply **lookahead** to pre-fetch and pre-extract the next two-to-three labels (k=2–3, configurable) so that the reviewer does not block on extraction when finishing a label. The specific value of k is a configuration parameter, not a fixed FR. | Strong | BR-011 | AC-FR-402 |
| **FR-403** | The agent shall **control batch cadence** via pull-based demand semantics: the producer shall not enqueue additional labels for review beyond outstanding demand. (Reactive Streams `request(n)` style; see NFR-PERF-002.) | Strong | BR-011 | AC-FR-403 |
| **FR-404** | A **mid-batch override** of any single disposition shall not stop the queue under the independence assumption; processing of subsequent labels continues. | Strong | BR-013 | AC-FR-404 |
| **FR-405** | The system shall fire a **soft-anomaly advisory** when M-of-N consecutive labels in a batch fail with the same reason code; the advisory is non-blocking and dismissable. | Medium | BR-007 | AC-FR-405 |
| **FR-406** | The batch surface shall present a **sortable batch table** with disposition column and queue-position metadata. | Strong | BR-011, BR-014 | AC-FR-406 |

*Source: T6 §Q6.1–Q6.5; D-010. The PRD specifies the behavior (pull-based, no-stop-on-override, soft-anomaly advisory); the Architecture Doc specifies the primitive (asyncio.Queue, EWMA, etc.).*

### 5.6 UX requirements (FR-500 series)

The system surfaces lifted from T8's 17-component inventory. The PRD names the surface and its behavior; framework, CSS, and DOM specifics live in `ARCHITECTURE.md` (per S3 D-013).

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-500** | The reviewer surface shall present a **field-card grid** (one card per common field) showing extracted value, expected value, rule verdict, AI suggestion (when present), citation, and confidence band. | Hard | BR-014 | AC-FR-500 |
| **FR-501** | Each field card shall support a **bbox-overlay** view that highlights the region of the label image driving the finding; overlay regions shall be keyboard-navigable and screen-reader accessible. | Strong | BR-012, BR-013 | AC-FR-501 |
| **FR-502** | Citation chips (one per CFR citation) shall open an **evidence panel** showing the cited regulation text and the extracted evidence side by side. | Strong | BR-007, BR-014 | AC-FR-502 |
| **FR-503** | The **deterministic-engine output** and the **AI-orchestration output** (when present) shall be visibly separated with distinct labels on the reviewer surface; the AI-orchestration output is never rendered in a position or styling that suggests it is the verdict. | Hard | BR-007, D-002 | AC-FR-503 |
| **FR-504** | An **override drawer** shall be reachable by keyboard (`O`) from any field card; the drawer presents a reason-code picker. | Strong | BR-013 | AC-FR-504 |
| **FR-505** | A **needs-better-photo card** shall be a first-class disposition surface (not an error message), showing the structured reason code and a templated applicant message. | Hard | BR-008 | AC-FR-505 |
| **FR-506** | **Alerts** (system-level, e.g., format-rejection) and **toasts** (transient confirmations) shall be presented in surfaces that meet the WCAG status-message pattern (4.1.3). | Strong | BR-012 | AC-FR-506 |
| **FR-507** | A **live region** shall announce disposition changes and override confirmations to assistive technology. | Strong | BR-012 | AC-FR-507 |
| **FR-508** | A **raw-JSON drawer** showing the full audit-trail object shall be available behind a `DEV_MODE` env-flag gate. | Medium | BR-009 | AC-FR-508 |
| **FR-509** | The **batch table** shall be sortable on disposition and queue position (FR-406); each row shall be selectable by keyboard. | Strong | BR-011, BR-012 | AC-FR-509 |
| **FR-510** | A **confidence indicator** (numeric + tri-state band: high / medium / low) shall be shown on each field card and at the disposition level. | Medium | BR-008 | AC-FR-510 |
| **FR-511** | A **disposition pill** at the disposition level shall use color, shape, and text — not color alone — to communicate pass / fail / needs-review state. | Hard | BR-012 (WCAG A 1.4.1) | AC-FR-511 |

*Source: T8 component inventory (17 components: C-FieldCard, C-BboxOverlay, C-EvidencePanel, C-CitationChip, C-RuleVerdict, C-AISuggestionBlock, C-OverrideDrawer, C-ReasonCodePicker, C-NeedsBetterPhotoCard, C-Alert, C-Toast, C-LiveRegion, C-RawJSONDrawer, C-BatchTable, C-QueuePosition, C-ConfidenceIndicator, C-DispositionPill); S3 D-013 (stack-shape boundary, ARIA semantics).*

### 5.7 Image-handling requirements (FR-600 series)

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-600** | The system shall accept **JPEG and PNG** label images. | Hard | BR-001 | AC-FR-600 |
| **FR-601** | The system shall **reject** TIFF, PDF, GIF, BMP, WebP, HEIC, and other non-JPEG/PNG image formats with a clear error message routed via the alert surface (FR-506). | Hard | BR-001 | AC-FR-601 |
| **FR-602** | The system shall require sufficient **DPI metadata** for measurement-bearing rules (warning type-size lookup, contrast computation); when DPI metadata is missing, affected rules shall return `needs_review` with reason code `ENGINE.MEASUREMENT.MISSING_DPI` (per T3 §Q3.10). | Strong | BR-008 | AC-FR-602 |
| **FR-603** | **Needs-better-photo** shall be a first-class disposition with a structured reason code from the legibility taxonomy (e.g., `WARNING.LEGIBILITY.LOW_RESOLUTION`, `WARNING.LEGIBILITY.GLARE`). | Hard | BR-008 | AC-FR-603 |
| **FR-604** | The system shall **not persist** submitted artwork beyond the active session; the image is held in memory only for the duration of the disposition. | Hard | BR-009 (per BRD §8.4) | AC-FR-604 |

*Source: T2 Q2.3; T4 Q4.6; T3 §Q3.10; 01-requirements.md Strong tier `[DATA]`; BRD §8.4.*

### 5.8 Disposition output requirements (FR-700 series)

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-700** | The per-label disposition shall be one of three states: `pass`, `fail`, `needs_review`. | Hard | BR-007 | AC-FR-700 |
| **FR-701** | Each disposition shall include a **per-field finding** containing: field name, extracted value, expected value, evidence (bbox + image-crop reference), CFR citation, structured reason code, plain-language explanation, and confidence (band + numeric). | Hard | BR-007, BR-009 | AC-FR-701 |
| **FR-702** | Reason codes shall follow the grammar **`BIN.SUB.SPECIFIC[.QUALIFIER]`** where BIN is one of: `BRAND`, `CLASS_TYPE`, `ALCOHOL_CONTENT`, `NAME_ADDRESS`, `NET_CONTENTS`, `WARNING`, `ALLERGEN`, `LEGIBILITY`, `ENGINE`. | Hard | BR-007, BR-009 | AC-FR-702 |
| **FR-703** | Each disposition shall be accompanied by an **audit-trail object** (see §6.2) containing `evaluation_id`, `rule_set_version`, `model_version`, `prompt_version`, `input_hash`, `output_hash`, timestamps, and the full per-rule trace. | Hard | BR-009 | AC-FR-703 |
| **FR-704** | The **disposition-level confidence** shall not exceed the lowest per-field confidence on any contributing field; downward propagation is required, upward inference is not permitted. The aggregation algorithm is implementation (see `ARCHITECTURE.md`). | Strong | BR-008 | AC-FR-704 |

*Source: D-007; T3 §Q3.4 RejectionReason model; T1 §7.3 reason-code bins; T8 disposition-pill spec; S5 confirmation of confidence min-aggregation.*

### 5.9 Override and manual-review requirements (FR-800 series)

| FR | Statement | Tier | BR | AC |
|---|---|---|---|---|
| **FR-800** | The reviewer shall be able to **override any disposition** at any time with a structured reason code from the active reason-code registry. | Strong | BR-013 | AC-FR-800 |
| **FR-801** | An override shall be recorded in the **session audit trail** with: original system disposition, reviewer-applied disposition, reason code, free-text justification (optional), reviewer identity (session-scoped), timestamp. | Hard | BR-009 | AC-FR-801 |
| **FR-802** | The **manual review path** shall always be reachable, independent of AI orchestration availability; if the orchestrator is unreachable, manual review remains available against the rule-engine output alone. | Hard | BR-013 | AC-FR-802 |
| **FR-803** | Override of the canonical case shall complete in **three keystrokes**: `O → reason → ENTER`. | Strong | BR-013 (UX) | AC-FR-803 |
| **FR-804** | Free-text justification on override shall be **optional** in MVP; reason-code selection alone is sufficient to record the override. (See OQ-PRD-1 in §12.2.) | Medium | BR-013 | AC-FR-804 |

*Source: 01-requirements.md Strong tier `[UX]`; T8 stage 2; T10 Q10.5.*

### 5.10 Engine failure-mode requirements (FR-900 series)

The system shall **never silently degrade to `pass`**. Engine-internal failures emit `needs_review` with a structured engine-error reason code from the T3 §Q3.10 taxonomy. (Source: T3 §Q3.10; D-007.)

| FR | Failure mode | Reason code | Tier |
|---|---|---|---|
| **FR-900** | Application data missing | `ENGINE.INPUT.APPLICATION_MISSING` | Hard |
| **FR-901** | Label image missing | `ENGINE.INPUT.LABEL_IMAGE_MISSING` | Hard |
| **FR-902** | Conflicting rules at runtime | `ENGINE.RULE.CONFLICT` | Hard |
| **FR-903** | Ambiguous OCR (multiple plausible reads, no winner after orchestration) | `ENGINE.OBSERVATION.AMBIGUOUS` | Hard |
| **FR-904** | Unknown beverage class | `CLASS_TYPE.UNKNOWN` | Hard |
| **FR-905** | Class disagreement (application vs. label) | `CLASS_TYPE.APPLICATION_LABEL_DISAGREE` | Hard |
| **FR-906** | Rule-set version mismatch | `ENGINE.RULESET.VERSION_NOT_FOUND` | Strong |
| **FR-907** | Validator exception (uncaught error inside a rule) | `ENGINE.VALIDATOR.EXCEPTION` | Hard |
| **FR-908** | Per-rule timeout exceeded | `ENGINE.VALIDATOR.TIMEOUT` | Strong |
| **FR-909** | Whole-evaluation timeout (5 s SLA exhausted) | `ENGINE.SLA.TIMEOUT` | Hard |
| **FR-910** | Missing measurement (e.g., DPI absent for type-size) | `ENGINE.MEASUREMENT.MISSING_DPI` | Strong |
| **FR-911** | Reference data unavailable (e.g., AVA whitelist load failed) | `ENGINE.REFERENCE_DATA.UNAVAILABLE` | Strong |
| **FR-912** | Model unavailable (LLM endpoint down) | `ENGINE.MODEL.UNAVAILABLE` | Hard |

All FR-900-series failures map to BR-007 (citation-grounded disposition) and BR-008 (no-disposition mode for low-confidence cases). Acceptance criteria AC-FR-900 through AC-FR-912 mirror the FR list.

---

## 6. Data Contracts at the System Boundary

The PRD owns wire-format contracts at the external surface. Internal types (in-process Pydantic models, ORM types) live in `ARCHITECTURE.md`.

### 6.1 Application-input contract

The system accepts a JSON envelope mirroring TTB Form 5100.31 (rev. 04/2023) items 1–18 plus a `labels` array of image references. Schema *shape* only; specific JSON Schema draft version is an Architecture Doc concern. The block below is an annotated example — the wire format is JSON, not JSONC; comments are author annotation.

```jsonc
{
  "rep_id": "string | null",                     // Item 1 (optional, third-party filer)
  "permit_number": "string",                     // Item 2 (required: Plant Registry / Basic Permit / Brewer's Notice)
  "source_of_product": "domestic | imported",    // Item 3 (required)
  "serial_number": "string",                     // Item 4 (required, ≤ 6 chars, year-prefixed)
  "type_of_product": "wine | distilled_spirits | malt_beverages",  // Item 5 (required)
  "brand_name": "string",                        // Item 6 (required)
  "fanciful_name": "string | null",              // Item 7 (conditional)
  "applicant": {                                 // Item 8 (required) + 8a (optional)
    "name": "string",
    "address": { "street": "...", "city": "...", "state": "...", "zip": "...", "country": "..." },
    "mailing_address": "address | null"
  },
  "formula": {                                   // Item 9 (conditional, FR-106)
    "ttb_formula_id": "string",
    "approval_date": "ISO-8601 date"
  } | null,
  "grape_varietals": ["string", ...] | null,     // Item 10 (wine only, conditional)
  "wine_appellation": "string | null",           // Item 11 (wine only, conditional)
  "phone": "string",                             // Item 12 (required)
  "email": "string | null",                      // Item 13 (optional)
  "type_of_application": {                       // Item 14 (required: at least a or b)
    "cola": true,
    "exemption": false,
    "exemption_state": "string | null",
    "distinctive_bottle": false,
    "bottle_capacity": "string | null",
    "resubmission": false,
    "prior_ttb_id": "string | null"
  },
  "blown_branded_embossed_text": "string | null",  // Item 15 (conditional)
  "date_of_application": "ISO-8601 date",          // Item 16 (required)
  "applicant_signature": "string | null",          // Item 17 (required; e-filed flag)
  "applicant_print_name": "string",                // Item 18 (required)
  "perjury_attested": true,                        // FR-104
  "labels": [
    {
      "image_ref": "string (URI or content-id)",
      "face_tag": "front | back | neck | side",
      "dimensions": { "width_px": 0, "height_px": 0, "dpi": 0 }
    }
  ]
}
```

*Note on numbering: the field set above reflects TTB Form 5100.31 rev. 04/2023 as confirmed via primary-source verification of `https://www.ttb.gov/system/files/images/pdfs/forms/f510031.pdf`. Earlier project notes referenced an item ordering that did not match the current form; rev. 04/2023 is authoritative.*

*Source: T2 Q2.10 recommendation; T2 Q2.1 (rev. 04/2023 schema); D-010.*

### 6.2 Disposition-output contract

The shape returned per label:

```jsonc
{
  "evaluation_id": "uuid",
  "label_ref": "string",
  "disposition": "pass | fail | needs_review",
  "disposition_confidence": {
    "band": "high | medium | low",
    "numeric": 0.0
  },
  "fields": [
    {
      "field_name": "brand_name | class_type | alcohol_content | net_contents | warning | name_address | country_of_origin",
      "extracted_value": "...",
      "expected_value": "...",
      "evidence": {
        "bbox": [x, y, w, h],
        "crop_ref": "string",
        "extraction_confidence": 0.0
      },
      "rule_findings": [
        {
          "rule_id": "string",
          "cfr_citation": "27 CFR §X.YY(z)",
          "disposition": "pass | fail | needs_review",
          "reason_code": "BIN.SUB.SPECIFIC[.QUALIFIER]",
          "plain_language_explanation": "string"
        }
      ],
      "ai_suggestion": {
        "present": false,
        "task": "brand_borderline | reasoning_enrichment | ocr_reconciliation | null",
        "text": "string | null",
        "model_disposition": "pass | needs_review | null"
      },
      "field_confidence": {
        "band": "high | medium | low",
        "numeric": 0.0
      }
    }
  ],
  "audit_trail": {
    "evaluation_id": "uuid",
    "rule_set_version": "semver",
    "model_version": "string | null",
    "prompt_version": "string | null",
    "input_hash": "sha256",
    "output_hash": "sha256",
    "started_at": "ISO-8601",
    "completed_at": "ISO-8601",
    "per_rule_trace": [
      { "rule_id": "...", "disposition": "...", "evidence_ref": "..." }
    ],
    "overrides": [
      {
        "field_name": "...",
        "original_disposition": "...",
        "applied_disposition": "...",
        "reason_code": "...",
        "justification_text": "string | null",
        "reviewer_id": "session-scoped",
        "timestamp": "ISO-8601"
      }
    ]
  },
  "metrics": {
    "total_duration_ms": 0,
    "per_rule_durations_ms": [
      { "rule_id": "...", "duration_ms": 0 }
    ],
    "vision_duration_ms": 0,
    "orchestrator_duration_ms": 0
  }
}
```

**Default-visible vs. drawer-visible split.** The reviewer-facing surface displays per-field findings, citations, AI suggestions, and confidence indicators by default; the full `audit_trail` object is drawer-visible behind `DEV_MODE` (FR-508). (Source: T8 Q8.11.)

### 6.3 Batch envelope contract

```jsonc
{
  "batch_id": "uuid",
  "agent_id": "session-scoped string",     // single value in MVP per T6 Q6.7
  "submitted_at": "ISO-8601",
  "items": [
    { "label_ref": "...", "application_ref": "..." }
  ]
}
```

Per-label results stream out as individual disposition-output objects (§6.2) augmented with `queue_position` and `batch_id` fields. The system is **multi-agent-aware but not multi-agent** in MVP: `agent_id` is structurally present and always set, but a single agent is assumed. (Source: T6 Q6.7; T8 C-BatchTable.)

### 6.4 Error contract

All boundary errors carry a structured reason code from the T3 §Q3.10 taxonomy:

```jsonc
{
  "error_kind": "rejected_input | engine_failure | partial_completion",
  "reason_code": "BIN.SUB.SPECIFIC[.QUALIFIER]",
  "message": "human-readable plain-language explanation",
  "details": { /* shape varies by reason_code */ }
}
```

- **`rejected_input`** — malformed JSON, missing required field, unsupported image format, attestation missing.
- **`engine_failure`** — timeout, validator exception, model unavailable.
- **`partial_completion`** — some labels in batch processed, others stalled (per FR-909).

(Source: T3 §Q3.10; T8 C-Alert.)

---

## 7. Non-Functional Requirements

### 7.1 Performance

- **NFR-PERF-001 (Hard).** The system shall return a draft disposition for a single typical label within ≤ 5 seconds of submission.
- **NFR-PERF-002 (Strong).** Batch lookahead shall not block first-label response; the producer shall not enqueue additional labels beyond outstanding demand from the consumer. (Reactive Streams `Subscription.request(n)` style: pull-based, demand-driven backpressure — the upstream producer is contractually prohibited from emitting beyond outstanding demand, so throughput is governed by consumer capacity rather than producer rate.)
- **NFR-PERF-003 (Strong).** Single-label processing shall meet **P50 ≤ 2.7 s** and **P99 ≤ 5.0 s** under demo-condition fixtures.

*Source: BRD BR-010, BR-011; T6 TL;DR; verbatim Sarah constraint; Reactive Streams Specification v1.0.4 rule 1.1 (publishers MUST NOT signal more `onNext` invocations than outstanding cumulative demand).*

### 7.2 Usability

- **NFR-UX-001 (Hard).** The user interface shall meet a senior-friendly bar (the "73-year-old benchmark"): high contrast, predictable layout, explicit affordances, no hidden gestures.
- **NFR-UX-002 (Strong).** The system shall be keyboard-operable end-to-end; no action required for primary review or override shall depend on a mouse or pointer.
- **NFR-UX-003 (Strong).** Override of the canonical case shall complete in three keystrokes (FR-803 restated).
- **NFR-UX-004 (Strong).** The system shall function correctly on current evergreen versions of Chromium-based browsers (Chrome, Edge), Firefox, and Safari; minimum viewport 320 CSS px width (per NFR-A11Y-005). Pointer (mouse) and touch input shall both be supported; keyboard remains the primary mode for reviewer workflows.

*Source: BRD BR-012, BR-013, BR-014; T8 keyboard model; WCAG 2.1 SC 1.4.10.*

### 7.3 Accessibility

- **NFR-A11Y-001 (Hard).** The system shall conform to **WCAG 2.0 Level A and Level AA Success Criteria** as incorporated by reference in the Revised Section 508 Standards (36 CFR Part 1194, Appendix A, §§ E205.4 and E207.2).
- **NFR-A11Y-002 (Strong).** A completed Accessibility Conformance Report (ACR) shall be authored on the ITI **VPAT® 2.5 Revised Section 508 Edition**, declaring conformance against WCAG 2.0 Level A/AA per NFR-A11Y-001. Each criterion shall be marked `Supports`, `Partially Supports`, `Does Not Support`, `Not Applicable`, or `Not Evaluated`, with remarks for any non-full Supports.
- **NFR-A11Y-003 (Strong).** Selected WCAG 2.1 / 2.2 success criteria shall be honored as design targets (not regulatory minima); the specific SC set is enumerated in the §15 appendix accessibility design-targets list (per T8 §Conformance testing posture).
- **NFR-A11Y-004 (Strong).** The reduced-motion media query (`prefers-reduced-motion: reduce`) shall be honored; no state change shall be signaled by motion alone.
- **NFR-A11Y-005 (Strong).** Layout shall reflow to 320 CSS px width without two-dimensional scrolling (WCAG 2.1 SC 1.4.10).

*Source: T7 §508; T8 §Conformance testing posture; T8 §Reduced motion; T8 §Reflow. Section 508 baseline confirmed as WCAG 2.0 Level AA via Access Board / 36 CFR 1194; VPAT 2.5 conformance vocabulary verified against ITI / Section508.gov primary documentation.*

### 7.4 Auditability

- **NFR-AUDIT-001 (Hard).** Every disposition shall produce an audit record with the shape specified in §6.2 (`audit_trail` object).
- **NFR-AUDIT-002 (Strong).** Audit records shall be sufficient to reconstruct the disposition during a regulatory audit: input hash, output hash, rule-set version, per-rule trace, and override history.

*Source: BRD BR-009; D-007.*

### 7.5 Substitutability (production-parity)

- **NFR-PORT-001 (Hard).** The system shall be deployable in environments that block outbound cloud calls.
- **NFR-PORT-002 (Hard).** The system shall support a deployment mode in which inference runs on-prem.

The Architecture Doc specifies *how* (per S3 D-015 dual-mode `VISION_MODE={local,cloud,auto}`); the PRD specifies *that*.

*Source: BRD BR-015, BR-016; S3 D-015.*

### 7.6 Determinism

- **NFR-DET-001 (Strong).** Re-running the system on the same inputs **within a session** shall produce the same disposition.
- **NFR-DET-002 (Stretch).** Cross-session determinism is out of scope; the prototype has no persistent state across sessions. The limitation is documented per T5 §Q5.10.

*Source: T5 Q5.10; 05-gaps-and-limitations.md.*

### 7.7 Data handling

- **NFR-DATA-001 (Hard).** No persistent storage of submitted artwork beyond session.
- **NFR-DATA-002 (Hard).** Audit records exist in-memory for the session and are not persisted to disk in the prototype tier.

*Source: BRD §8.4; 01-requirements.md Strong tier `[DATA]`; 05-gaps-and-limitations.md.*

### 7.8 Security

The prototype tier inherits "just don't do anything crazy" (BRD §8.2). Concretely:

- **NFR-SEC-001 (Hard).** All network communication to and from the deployed prototype shall use TLS.
- **NFR-SEC-002 (Hard).** API credentials, signing keys, and any secrets shall not be checked into source; the system shall load them from environment configuration at deployment time.
- **NFR-SEC-003 (Hard).** The system shall sanitize and validate inbound JSON envelopes (§6.1) and image uploads against the declared schema and supported-format allowlist (FR-101, FR-601) before any processing; malformed or unsupported inputs are rejected with the §6.4 error contract.
- **NFR-SEC-004 (Hard).** The system shall not log submitted application content, label artwork, or extracted field values beyond what is required to populate the §6.2 audit-trail object for the active session.

*Source: BRD §8.2; take-home Marcus interview; 05-gaps-and-limitations.md §1.*

### 7.9 Observability

- **NFR-OBS-001 (Strong).** The system shall emit structured logs at engine-failure events (FR-900 series) with the field schema specified in T3 §Q3.10 — at minimum: `evaluation_id`, `reason_code`, and the per-failure-mode fields enumerated in T3 §Q3.10.
- **NFR-OBS-002 (Medium).** The system shall expose latency percentiles (P50, P95, P99) for single-label evaluations to support NFR-PERF-001 / NFR-PERF-003 acceptance.

The PRD specifies *what* is observable; log destinations, transport, and retention live in `ARCHITECTURE.md`.

*Source: T3 §Q3.10; T6 TL;DR; BR-009.*

---

## 8. Acceptance Criteria

Format: AC-FR-### linked to FR-###. Each AC is testable. Hard-tier FRs have at least one positive and one negative AC; Strong-tier FRs have at least one of each where reasonable; Stretch FRs may have a positive AC only.

### 8.1 Demo-fixture acceptance (per D-011)

| Fixture | ACs satisfied |
|---|---|
| **Fixture-01** (clean spirits happy path) | AC-FR-200 series pass; AC-NFR-PERF-001 demonstrates < 2s observable latency. |
| **Fixture-02** (STONE'S THROW Bourbon) | AC-FR-240 brand normalized-pass at the case-only-difference policy stage; no reviewer override required (per S2 recommended Stage-2 narration update). |
| **Fixture-03** (title-case "Government Warning") | AC-FR-202 fail with `WARNING.STYLE.HEADING_NOT_BOLD_CAPS` and citation 27 CFR §16.22(a)(2). |
| **Fixture-04** (low-res / glare image) | AC-FR-603 needs-better-photo with structured legibility reason. |
| **Fixture-05** (batch of 50) | AC-FR-401 first label returns under NFR-PERF-001; AC-FR-402 lookahead behavior is observable. |
| **Fixture-06** (ABV out-of-tolerance) | AC-FR-225 fail with citation 27 CFR §5.65(c); AC-FR-803 override completes in three keystrokes. |
| **Fixture-07** (borderline-confidence `needs_review`) | AC-FR-704 disposition-level confidence lands in medium band; AC-FR-501 / FR-502 affected fields and evidence are surfaced; reviewer confirms or overrides via the same FR-800-series path. |

*Source: S2 D-011; T8 fixtures 01–06; S2 §Recommend updating T8 Stage 2 narration.*

### 8.2 Stakeholder-signal acceptance

| Persona | Signal | Mapped AC |
|---|---|---|
| **Sarah** (sponsor) | < 2s observable on Stage 1 first label | AC-NFR-PERF-001 / AC-NFR-PERF-003 |
| **Dave** (skeptic) | STONE'S THROW resolved at case-only normalization with no override | AC-FR-240 + S2 recommendation |
| **Jenny** (workflow) | Title-case warning fires with right reason code + CFR chain | AC-FR-202 + AC-FR-701 |

*Source: T10 Q10.4–Q10.5; S2 §Recommendation.*

### 8.3 Per-rule acceptance

For each MVP rule in §5.3, an AC pair: (a) positive case passes; (b) canonical negative case fails with the correct reason code and CFR citation. Boundary cases for tolerance rules (FR-214 / FR-225 / FR-234) include: ABV exactly at the tolerance limit (pass), exactly outside (fail), and at a class boundary (FR-215 anti-overlap rule fires).

*Source: S4 §Evaluation acceptance criteria; T9 Q9.8.*

### 8.4 Evaluation acceptance (corpus-level)

Right-sized for prototype tier per the v0.4 review (the original S4 targets are stretch — see §9.1 note):

- Disposition macro-F1 ≥ 0.70 on the full eval corpus (MVP gate). The 0.85 v1 gate is deferred to pilot phase, where corpus expansion enables tighter confidence intervals.
- Per-rule recall ≥ 0.80 on government-health-warning rules (FR-200 through FR-205) — these rules carry the highest cost-of-error asymmetry per T9 Q9.1 and warrant a dedicated recall floor even at prototype N.
- Per-rule positive coverage: ≥ 1 positive AC per rule (statistical-defensibility expansion to ≥ 43 per rule is pilot-phase work; flagged in §9.1 right-sizing note).
- Happy-path coverage: ≥ 10 fully-compliant labels in the full corpus (was ≥ 97 — pilot-phase target).

*Source: S4 §Evaluation acceptance criteria, right-sized at v0.4 to match prototype-tier corpus (see §9.1).*

### 8.5 Performance acceptance

- **NFR-PERF-001** demonstrated against fixture-01: P50 ≤ 2.7s wall-clock; P99 ≤ 5.0s under demo conditions.
- **NFR-PERF-002** demonstrated against fixture-05: first label of 50-batch returns under NFR-PERF-001; producer respects pull-based demand from agent.

*Source: T6 TL;DR; BR-010, BR-011.*

### 8.6 Accessibility acceptance

- Automated axe-core or Pa11y check passes on every PR with **zero WCAG 2.0 Level AA violations** on the six demo fixtures.
- Manual NVDA + VoiceOver smoke test on the field-card and bbox-overlay surfaces passes the keyboard-model exercises in T8.
- Reduced-motion smoke test confirms no state change is signaled by motion alone.
- Reflow test confirms no two-dimensional scrolling at 320 CSS px width.

*Source: T8 §Conformance testing posture.*

---

## 9. Evaluation Plan

The PRD specifies what the eval looks like and what passes. The Architecture Doc and the eval harness implement it.

### 9.1 Test corpus shape

**Right-sizing note (v0.4).** The original S4 spec called for ≥ 250 hand-labeled labels with worst-case Wald math, ≥ 43 cases per rule, and Krippendorff's α ≥ 0.80 from a 48-hour-gap solo-annotator double-pass. That is pilot-phase scope. Prototype tier ships a defensible-but-smaller corpus:

- **Smoke subset:** ~ 20 labels — runs on every PR; ≤ 60 s wall clock.
- **Full corpus:** ~ 50 labels (smoke is a strict subset). Stratified across class × difficulty × rule families so every MVP rule is exercised by ≥ 1 positive case.
- **Class balance:** spirits 30–40%, wine 30–40%, malt 20–30%. (Spirits is the largest rule surface per S5; wine and malt are weighted to absolute coverage rather than industry mix in the prototype corpus.)
- **Synthetic share ≤ 30%** of the full corpus with `provenance.source` matching `^synthetic-` (relaxed from 15% — at N=50, controlled synthetic degradations are the only practical way to exercise the borderline slice without compromising provenance honesty).
- **Borderline-confidence slice (≥ 10 labels)**, scaled from the original ≥ 20: images intentionally degraded into the medium-confidence band so the disposition lands at `needs_review` rather than clean pass/fail. Sources: (a) controlled synthetic degradation of clean COLA Registry images (mild blur, glare, JPEG compression, rotation, perspective transforms tuned to drop OCR confidence into the borderline band); (b) hand-curated retail/mobile product photography with real-world quality issues (reflections, partial occlusion, motion blur); (c) ICDAR Robust Reading Challenge derivations applied to label crops. This slice exercises FR-704 confidence aggregation and the human-in-the-loop disposition path.
- **Happy-path coverage ≥ 10** fully-compliant labels in the full corpus.
- **Intra-rater reliability:** the original Krippendorff's α ≥ 0.80 target is **deferred to pilot phase** — at N=50 the statistic's confidence interval is too wide to support a hard gate, and the expected pilot-phase corpus expansion is the right place to land it. The MVP corpus is single-pass with the labeling protocol documented in `eval/datasheet.md` for transparency.
- **Datasheet** still follows Gebru et al. (2021) seven-section template — the documentation discipline holds at any N.

The pilot-phase expansion path (≥ 250 labels, ≥ 43 per rule, Krippendorff's α gate) remains the production-trajectory target and is recorded in §12.2 OQ-PRD-5.

*Source: S4 §Evaluation acceptance criteria, right-sized at v0.4 for prototype tier; T9 Q9.1–Q9.4.*

### 9.2 Metrics framework

- **Disposition macro-F1** as headline metric.
- **Per-rule precision/recall** as drilldown.
- **Per-class small-multiples** (wine / spirits / malt).
- **Calibration curve** (does confidence track accuracy).
- **Time-to-disposition** distribution (P50 / P95 / P99).
- **Cost-of-error asymmetry**: false-pass weighted higher than false-reject in the headline aggregation per T9 Q9.1 and T3 §Q3.4 brand-name threshold rationale.

*Source: T9 Q9.1; S4.*

### 9.3 Stakeholder-mapped test cases

| Persona | Mapped test set |
|---|---|
| **Sarah** | Latency tests across realistic-difficulty inputs |
| **Dave** | Fuzzy-match acceptance set (STONE'S THROW family) |
| **Jenny** | Warning-statement adversarial set (case modifications, missing words, font-weight swaps) |
| **Marcus** | Security smoke tests appropriate to prototype tier (no PII in logs, no outbound calls outside whitelist in cloud mode) |

*Source: T9 Q9.5.*

### 9.4 Harness behavior

- A **smoke subset** (~20 labels) shall run on every code change.
- A **full eval** shall run on integration to the main branch.
- A **scheduled full eval** shall run on a recurring cadence with metrics persisted for trend analysis.
- An **eval dashboard surface** shall render the disposition confusion matrix and per-rule precision/recall table; the surface is gated to non-production / development use.

Specific paths, schedules, env-flag names, and storage locations are eval-harness implementation; see `ARCHITECTURE.md` and the eval-harness design.

*Source: S4 acceptance criteria.*

---

## 10. Demo Plan

Demo is a delivered acceptance artifact, not a marketing exercise. Lifts D-011 directly.

### 10.1 Length and channels

- **5-minute recorded walkthrough** (Loom or equivalent), linked from README.
- **Deployed URL** (public-readable, no auth gymnastics) reachable for the full 7-stage path including network-failure recovery (which is cut from the 5-min recording for time).
- **Source repo + README** per take-home deliverable.
- **Hybrid live/cached**: pre-warmed orchestrator at T-5 minutes pre-recording; LLM responses cached for the six demo fixtures, narrated transparently.

*Source: D-011; S2 §10–11.*

### 10.2 Six-stage demo path (recorded cut)

1. **Clean spirits pass** (fixture-01) — Sarah signal: speed + simplicity, < 2s observable.
2. **STONE'S THROW Bourbon** (fixture-02) — Dave signal: case-only normalization passes cleanly per S2 recommendation; no override needed.
3. **Title-case "Government Warning" fail** (fixture-03) — Jenny signal: exact reason code + citation chain.
4. **Needs-better-photo** (fixture-04) — honest failure mode (legibility-gate fail; system declines to evaluate).
5. **Batch of 50** (fixture-05) — lookahead + queue position + batch table.
6. **ABV out-of-tolerance** (fixture-06) — override demo, three keystrokes.
7. **Borderline-confidence `needs_review`** (fixture-07) — a label image with mild quality degradation (e.g., light glare on the Government Warning region) such that OCR confidence drops into the medium band. The system completes a full disposition with a numeric confidence below the auto-pass threshold, surfaces the affected fields with their per-evidence confidences, and routes to `needs_review` — demonstrating the human-in-the-loop slice between clean pass/fail. The reviewer eyeballs the flagged region and confirms or overrides.

*Source: D-011 §1; T8 Q8.8; S2 §13a.*

### 10.3 Demo failure-recovery

- **Pre-warm.** The system shall support a pre-warm path so that the first demonstrated label is not penalized by cold-start latency.
- **Cache.** LLM responses for the six demo fixtures shall be cached for the recorded walkthrough; rule-engine and orchestration paths run live.
- **Disclosure.** Narration discloses caching honestly: "we cached the LLM call for the demo fixtures so the walkthrough is reproducible — the orchestration and rule engine run live."

Specific endpoints, cache keys, and pre-warm timing are demo-runbook implementation; see the demo runbook and `ARCHITECTURE.md`.

*Source: D-011 §3; T8 §Demo failure-recovery items 1–2.*

---

## 11. Operational and Compliance Constraints

This PRD inherits constraints from the BRD; it does not redraw them. The PRD's job is to ensure the FRs do not violate those constraints.

### 11.1 Inherited constraints

- **BRD §8.2** — prototype-tier compliance: no PII storage, no production ATO, no FedRAMP, "just don't do anything crazy."
- **BRD §8.4** — no persistent storage of submitted artwork beyond session.
- **BRD §9.1** — firewall, latency, UX, standalone constraints.

Compliance-derived FRs are tagged in the §13 traceability matrix; see the "Compliance-derived" column.

---

## 12. Open Questions and Decisions Deferred

### 12.1 Inherited open questions (from BRD §10.2)

| ID | Question | Status |
|---|---|---|
| **OQ-1** | Canonical application-input format | Mocked JSON for prototype (per FR-100, §6.1); production answer pending COLAs Online schema access. |
| **OQ-2** | Deployed-URL auth posture | Public-readable for prototype demo (per D-011); production answer is PIV/SAML federation, out of scope for prototype. |
| **OQ-3** | Structured reason codes for downstream filtering | **Resolved.** Reason-code grammar specified in FR-702. |
| **OQ-4** | Confidence representation (numeric vs. tri-state band) | **Partially resolved.** Both shipped (FR-510): tri-state band + numeric. |
| **OQ-5** | Eval-corpus sample selection | **Resolved.** Specified in §9.1. |

### 12.2 PRD-specific open questions

| ID | Question | Disposition |
|---|---|---|
| **OQ-PRD-1** | Should the override drawer require a free-text justification or just a reason-code selection? | **Decided MVP**: reason-code selection alone is sufficient (FR-804). Free-text is optional. Production posture may require justification for high-impact overrides; defer to pilot phase. |
| **OQ-PRD-2** | Are batch-mode failed-label retries automatic or reviewer-initiated? | **Decided MVP**: reviewer-initiated. Automatic retry would require a retry policy with backoff and would complicate the audit trail without persona signal demand. |
| **OQ-PRD-3** | Does the audit-trail object include the LLM prompt and response verbatim? | **Decided MVP**: yes for `DEV_MODE` raw-JSON drawer (FR-508), via T5 / S3 ring-buffer pattern; production posture may redact for PII review. |
| **OQ-PRD-4** | For multi-image labels (front + back + neck), what's the disposition-aggregation rule? | **Open.** MVP supports single front-label submissions; multi-image aggregation deferred to stretch. Provisional rule: any-fail aggregates to fail; any-needs-review without fail aggregates to needs-review; otherwise pass. To validate with reviewers in pilot phase. |
| **OQ-PRD-5** | When does the eval corpus expand to the original S4 statistical-defensibility targets (≥ 250 labels, ≥ 43 cases per rule, Krippendorff's α ≥ 0.80, ≥ 97 happy-path)? | **Pilot phase.** §9.1 right-sized the prototype corpus to ~ 50 labels + ~ 20 smoke; the original S4 targets remain the production-trajectory target and ship with the pilot. |

---

## 13. Traceability Matrix

Every BR maps to ≥ 1 FR; every FR maps to exactly one BR (one-to-many BR→FR; many-to-one FR→BR). Fan-out is shown explicitly. The "Compliance-derived" column flags FRs/NFRs that exist primarily because of a compliance constraint (audit, no-persistence, accessibility, firewall) rather than a substantive business need.

| BR | BR statement (abbreviated) | FRs/NFRs that operationalize it | Compliance-derived items |
|---|---|---|---|
| **BR-001** | Brand-name verification | FR-001, FR-100, FR-101, FR-102, FR-210, FR-220, FR-230, FR-240, FR-600, FR-601 | — |
| **BR-002** | ABV verification | FR-002, FR-003, FR-212–FR-215, FR-223–FR-225, FR-232–FR-235 | — |
| **BR-003** | Net-contents verification | FR-004, FR-217, FR-228, FR-237 | — |
| **BR-004** | Government health-warning verification | FR-005, FR-006, FR-200–FR-206 | — |
| **BR-005** | Bottler/importer name-and-address verification | FR-007, FR-105, FR-216, FR-227, FR-236 | — |
| **BR-006** | Country-of-origin verification (imports) | FR-008, FR-100 | — |
| **BR-007** | Citation-grounded disposition | FR-301, FR-303, FR-500, FR-502, FR-503, FR-700–FR-703, FR-900 series | FR-702 (reason-code grammar exists per D-007 audit readability) |
| **BR-008** | No-disposition mode for low-confidence | FR-302, FR-505, FR-510, FR-602, FR-603, FR-704, FR-900 series | — |
| **BR-009** | Audit trail | FR-508, FR-703, FR-801, NFR-AUDIT-001, NFR-AUDIT-002 | FR-703, NFR-AUDIT-001/002 (audit derives directly from D-007) |
| **BR-010** | Single-label latency (~5s) | NFR-PERF-001, NFR-PERF-003, FR-401 | — |
| **BR-011** | Batch handling | FR-103, FR-400–FR-406, FR-509, NFR-PERF-002 | — |
| **BR-012** | Senior-friendly UI | FR-501, FR-507, FR-509, FR-511, NFR-UX-001, NFR-A11Y-001 through NFR-A11Y-005 | NFR-A11Y-001/002 (Section 508 / 36 CFR 1194 §§ E205.4, E207.2) |
| **BR-013** | Always-available manual review | FR-304, FR-504, FR-800–FR-804, NFR-UX-002, NFR-UX-003 | — |
| **BR-014** | Explanation legibility | FR-301, FR-500, FR-502, FR-506 | — |
| **BR-015** | Firewall-deployable | FR-304, NFR-PORT-001, NFR-PORT-002 | NFR-PORT-001 (Marcus firewall constraint) |
| **BR-016** | On-prem inference path preserved | NFR-PORT-002 | — |
| **BR-017** | Common-fields coverage across three commodities | FR-001 through FR-008, FR-200 through FR-237 | — |
| **BR-018** | Class-specific deferrals | §3.3 (out of scope); FR-106, FR-222, FR-229 (limited spirits-deep per D-012) | — |
| *(cross-cutting)* | Data handling, security, observability | NFR-DATA-001/002, NFR-SEC-001 through NFR-SEC-004, NFR-OBS-001/002 | FR-604, NFR-DATA-001/002 (BRD §8.4 prototype-tier no-persistence); NFR-SEC-001 through NFR-SEC-004 (BRD §8.2 prototype-tier hygiene) |

*Source: BRD §5; BRD §8.2, §8.4; D-007.*

---

## 14. Glossary Delta

PRD-only terms not in the BRD glossary, with one-line definitions:

| Term | Definition |
|---|---|
| **AC** | Acceptance Criterion — a testable statement that confirms an FR is satisfied. |
| **bbox overlay** | An SVG layer rendered over a label image that highlights the bounding box of an extracted field. |
| **citation chip** | A clickable UI element bearing a CFR section reference (e.g., "27 CFR §16.22(a)(2)") that opens an evidence panel. |
| **confidence indicator** | A visual element communicating extraction or disposition confidence as both a tri-state band (high/medium/low) and a numeric value. |
| **disposition pill** | A colored, shaped, and labeled badge communicating one of pass / fail / needs-review at the disposition level. |
| **EWMA** | Exponentially Weighted Moving Average — a smoothing technique referenced in the soft-anomaly detector (T6); implementation only. |
| **evidence panel** | A drawer showing the extracted evidence and the cited regulation text side by side. |
| **field card** | A reviewer-facing surface element presenting one common field's extraction, rule verdict, AI suggestion, citation, and confidence. |
| **field manifest** | The list of fields the system extracts and validates per beverage class. |
| **FIFO** | First-In-First-Out — a queue discipline reference; implementation only. |
| **FR** | Functional Requirement — an externally observable behavior the system must exhibit. |
| **lookahead** | The number of labels (k=2–3) the batch system pre-extracts ahead of the reviewer's current position. |
| **NFR** | Non-Functional Requirement — a quality attribute (performance, accessibility, etc.) the system must meet. |
| **override drawer** | A keyboard-accessible UI surface where the reviewer enters a reason-code-bearing override of a system disposition. |
| **P50 / P99** | The 50th-percentile (median) and 99th-percentile values of a latency distribution. |
| **reason code** | A structured code following the grammar `BIN.SUB.SPECIFIC[.QUALIFIER]` that classifies a finding for downstream filtering and audit. |
| **reason-code picker** | A keyboard-operable selector inside the override drawer presenting valid reason codes. |
| **rule pack** | The set of rule definitions for a beverage class (e.g., `rules/spirits.yaml`) loaded by the rule engine. |
| **VPAT** | Voluntary Product Accessibility Template — the ITI-published template (currently version 2.5) for reporting product accessibility conformance; the Revised Section 508 Edition is the federal-procurement-targeted variant. |

*Source: T8 component inventory; T3 §Q3.4; T6; T8 §Conformance testing.*

---

## 15. Appendices

### 15.1 Cross-reference map

| Companion artifact | Relationship to this PRD |
|---|---|
| **`BRD.md`** | Why we're building it; business case; BR-001 through BR-018 (the upward trace targets of every FR). |
| **`ARCHITECTURE.md`** | How it's built; component design; technology choices; algorithms; thresholds. |
| **`03-decisions.md`** | Decision log; D-001 through D-016 cited throughout. |
| **`01-requirements.md`** | Hard / Strong / Medium / Stretch tier system used to tier each FR. |
| **`02-architecture.md`** | High-level architecture preview; full design lives in `ARCHITECTURE.md`. |
| **`04-research-topics.md`** | Source of inherited open questions (§12.1). |
| **`05-gaps-and-limitations.md`** | Source of accepted prototype gaps cited in NFR-DET-002, NFR-DATA-002. |
| **T1-output.md** | Regulatory field manifest, government-warning specification, reason-code taxonomy — primary source for §5.3. |
| **T2-output.md** | Form 5100.31 schema (rev. 04/2023), submission paths — primary source for §6.1. |
| **T3-output.md** | Validator interface, RejectionReason data model, engine failure-mode taxonomy — primary source for §5.10 and §6. |
| **T4-output.md** | Per-field extraction requirements, needs-better-photo posture — primary source for §5.1 and §5.7. |
| **T5-output.md** | AI orchestrator task list and failure handling — primary source for §5.4. |
| **T6-output.md** | Batch processing semantics, lookahead, backpressure — primary source for §5.5. |
| **T8-output.md** | UX components, demo path, accessibility — primary source for §5.6 and §10. |
| **T9-output.md / S4-output.md** | Evaluation methodology and acceptance criteria — primary source for §8 and §9. |
| **S2-output.md** | D-010 MVP scope, D-011 demo shape, D-012 spirits depth — lifted into §3 and §10. |
| **S3-output.md** | D-013 stack-shape, D-014 rule format, D-015 dual deployment — referenced as boundary commitments. |
| **S5-output.md** | Final per-class MVP rule list, reason-code grammar, ABV tolerance values — primary source for §5.3 and §6.2. |
| **Take-home brief** | Ground truth; wins ties against all other sources. |

### 15.2 Accessibility design-targets list (per NFR-A11Y-003)

WCAG 2.1 / 2.2 success criteria honored as design targets beyond the WCAG 2.0 AA regulatory baseline:

- **1.4.10** Reflow
- **1.4.11** Non-text contrast
- **1.4.13** Content on hover or focus
- **2.4.11** Focus not obscured (minimum)
- **2.4.12** Focus not obscured (enhanced)
- **2.5.5** Target size (enhanced)
- **2.5.7** Dragging movements
- **2.5.8** Target size (minimum)
- **4.1.3** Status messages

*Source: T8 §Conformance testing posture.*

### 15.3 Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-02 | Project team | Initial issue. |
| 0.2 | 2026-05-02 | Project team | Self-review pass. Added §3.4 Success Metrics (BO→FR map); added i18n out-of-scope; added NFR-UX-004 (browser/viewport), NFR-SEC-001 through NFR-SEC-004 (security baseline), NFR-OBS-001/002 (observability). Softened FR-503 component naming, FR-704 algorithm leak, NFR-DET-002 mechanism leak. Trimmed §9.4 (paths/env vars) and §10.3 (endpoints/timing) to behavior; implementation specifics moved to `PRD-deferred-content.md` for downstream docs. Removed redundant §11.2; folded compliance-derived flags into §13 traceability matrix. Compacted NFR-A11Y-003 SC list to §15.2 appendix. Annotated §6.1 JSONC block as illustrative. |
| 0.3 | 2026-05-02 | Project team | Added §3.2 stretch bullet: automated threshold re-calibration (brand-match cutoffs, confidence-band edges, BRISQUE/NIQE gates) sweeping from eval-corpus performance. |
| 0.4 | 2026-05-03 | Project team | Applied ARCH ADR D-018 erratum to §6.2 wire example: moved per-rule `duration_ms` out of `audit_trail.per_rule_trace[]` (audit) into a sibling `metrics` block (telemetry). `audit_trail` retains regulatory-reconstruction fields only; `metrics` carries `total_duration_ms`, `per_rule_durations_ms[]`, `vision_duration_ms`, `orchestrator_duration_ms`. |
| 0.5 | 2026-05-03 | Project team | Eval corpus right-sized for prototype tier: §8.4 acceptance and §9.1 corpus shape revised — full corpus ~ 50 labels (was ≥ 250), smoke ~ 20, borderline slice ≥ 10 (was ≥ 20), happy-path ≥ 10 (was ≥ 97), per-rule positive coverage ≥ 1 (was ≥ 43), Krippendorff's α gate deferred to pilot. macro-F1 ≥ 0.70 MVP gate held; 0.85 v1 gate deferred. New OQ-PRD-5 records the pilot-phase expansion target. Synthetic share cap relaxed from 15% to 30%. Class balance rebalanced for absolute rule coverage at the smaller N. |
| 0.4 | 2026-05-02 | Project team | Added borderline-confidence corpus slice (§9.1) and demo fixture-07 (§10.2 / §8.1) — images that land in the medium-confidence `needs_review` band, demonstrating the human-in-the-loop slice between clean pass/fail. |
