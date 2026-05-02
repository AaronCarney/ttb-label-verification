# BRD.md — Business Requirements Document
## TTB AI-Powered Alcohol Label Verification Prototype

**Document type:** Business Requirements Document (BRD)
**Owner:** Project sponsor (TTB Alcohol Labeling and Formulation Division — ALFD)
**Audience (primary):** TTB program sponsor; Treasury / OMB reviewer reading as a real business case
**Audience (secondary):** Take-home reviewer evaluating candidate's grasp of business context
**Status:** Draft for review — prototype phase
**Companion documents:** PRD.md (functional requirements), ARCHITECTURE.md (component design), 03-decisions.md (decision log)

---

## 1. Executive Summary

**Problem.** TTB's Alcohol Labeling and Formulation Division reviews on the order of 150,000 Certificate of Label Approval (COLA) applications each year with roughly 47 label specialists, working inside a COLAs Online environment whose user interface and case-management posture date to the early-2000s .NET era. A senior reviewer ("Sarah") describes spending five to ten minutes per simple application doing what is effectively "data entry verification" — eyeball-matching brand name, alcohol-by-volume, net contents, government health warning, bottler/importer information, and (for imports) country of origin against the artwork the applicant uploaded — before any judgment-laden review begins. Reviewers are, in her words, "drowning in routine stuff," which crowds out the nuanced, class-of-product, and consumer-protection judgments that actually require a human regulator under 27 CFR Parts 4, 5, 7, and 16 (Source: take-home Sarah interview; T2 operational context; T1 §0 regulatory framework).

**Approach.** This prototype demonstrates an AI-orchestrated, deterministic-rule-core decision pattern with a human-in-the-loop disposition: vision/OCR extraction and a structured-output language model surface label fields and propose a disposition, while the regulatory verdicts themselves are reached by deterministic rule logic that maps each finding back to a specific CFR citation. The prototype is a standalone, web-deployable proof-of-concept that returns a draft disposition in approximately five seconds per single label and supports batch handling for peak-season importer drops. It is explicitly not a production system; it does not integrate with COLAs Online, does not write back, and does not replace a reviewer's signature (Source: take-home tech requirements; D-002; D-007; D-010).

**Headline value.** Even after applying a conservative realization-rate haircut (theoretical labor savings rarely convert one-for-one into budget), the labor-savings range projected by the cost-benefit model materially exceeds the prototype-tier and pilot-tier cost ranges across a 3- and 5-year horizon, and the dominant non-monetizable benefit — freeing senior specialists to spend their time on judgment work rather than data-entry verification — is large and directional even where the dollar figure is uncertain (Source: T11 Stage 2 Q11.7; T11 Q11.8 realization-rate caveat; T11 Q11.17 non-monetizable factors; T11 Q11.20 headline framing).

---

## 2. Background and Current State

### 2.1 Current TTB label review process

TTB's Alcohol Labeling and Formulation Division (ALFD) administers the Federal Alcohol Administration Act's pre-market label-approval requirement for wine (≥7% ABV), distilled spirits, and malt beverages through the COLA program (TTB Form 5100.31). Industry members file electronically via COLAs Online — an internet-facing system whose internal case-tracking module is the "sole internal database" ALFD uses to track every COLA submission, paper or electronic — and approved certificates are republished to the Public COLA Registry within roughly 48 hours of approval (Source: T2 operational context; TTB.gov COLA program pages cited in T1 §0).

Annual application volume is on the order of 150,000 applications across the three commodities, processed by a workforce of approximately 47 label specialists in ALFD (Source: take-home brief; T2 Q-volume). Processing-time targets vary by commodity and by submission channel, and ALFD publishes them publicly; the practical effect is that any given applicant waits days-to-weeks for a verdict, with peak loads driving longer queues.

The dominant per-application work pattern, as described by Sarah (a senior label specialist) in the take-home interview, is a 5–10 minute eyeball check on simple applications: confirm the brand name on the artwork matches the brand name on the application, confirm the ABV/alcohol-content statement matches and falls within class-permitted ranges, confirm the net-contents statement is one of the recognized standards of fill, confirm the government health warning under 27 CFR Part 16 is present and legible, and confirm bottler/importer name-and-address and (for imports) country of origin (Source: take-home Sarah interview; T1 §1.1 mandatory-field manifest).

The judgment-laden portion of review — class/type compliance for distilled spirits, age statements, geographical indications and appellations, prohibited practices, misleading-impression analysis, and consumer-protection edge cases — sits on top of that data-entry verification floor and is where reviewer expertise actually matters (Source: take-home Dave interview; T1 §§4–7).

The system of record (COLAs Online) is functional but architecturally dated; reviewer commentary frames the front-end as a relic of early-2000s government .NET application design, optimized for record-keeping rather than for reviewer cognitive workflow (Source: T2 system-context; take-home Marcus interview).

### 2.2 What is broken from the inside view

- **Sarah, senior label specialist:** "I'm drowning in routine stuff." She characterizes a meaningful share of her day as "data entry verification" — visually re-keying what the applicant already typed in the form to confirm the artwork matches — which she reports as the single largest drain on time available for substantive review (Source: take-home Sarah interview).
- **Dave, a more skeptical senior reviewer:** points out that even nominally simple checks involve nuance — e.g., a "Kentucky Straight Bourbon Whiskey" claim is not a string match, it is a regulatory claim with conditions; an age statement on a young whiskey is not optional; geographic indications carry conditions a literal OCR will not see. His skepticism is a feature, not a bug, of the requirements: any system that treats label review as pure string-matching will fail (Source: take-home Dave interview).
- **Jenny, a label specialist:** maintains a printed paper checklist at her desk because the system does not surface the regulatory rules in the order she actually applies them — a tell that the existing tooling has not absorbed reviewer workflow (Source: take-home Jenny interview).
- **Failed scanning-vendor pilot:** a prior modernization attempt fell over on latency. Reviewers reported the round-trip was on the order of multiple seconds per call in a workflow where they expect sub-five-second responsiveness; the tool was abandoned (Source: take-home Sarah and Marcus interviews; T2 prior-pilot context).

### 2.3 Prior modernization attempts and why they failed

Three threads from the take-home interviews and operational context are load-bearing for this BRD:

- **Latency killed the scanning-vendor pilot.** Five seconds is not an aspirational target; it is the empirically observed reviewer-tolerance ceiling above which the prior pilot lost adoption (Source: take-home Sarah; D-010 latency floor).
- **Federal firewall constrains the solution space.** Marcus, the IT/security stakeholder, stated bluntly that any production-bound design must be "deployable in environments that block outbound cloud calls." That is a hard architectural constraint, not a preference, and it has historically eliminated SaaS-only vendors before procurement (Source: take-home Marcus interview; D-004).
- **Reviewer skepticism is earned.** Dave's posture toward AI-assisted review is not generic technophobia; it is a rational response to tools that have over-promised on nuance and under-delivered. Any new system must give him reasons — citations, evidence, manual override — to trust it (Source: take-home Dave interview; T10 Q10.4 empathy map).

### 2.4 Why now

- Vision and OCR models that a few years ago required cloud-scale GPU clusters now run on commodity GPU hardware at price points compatible with federal IT budgets, opening the door to on-prem deployment behind a firewall (Source: S1 high-level findings).
- Structured-output language-model interfaces have matured to the point where a model can return a typed, schema-conforming object suitable for deterministic rule evaluation rather than free-text that needs post-hoc parsing — making the AI surface auditable (Source: S1 high-level findings).
- Federal-context on-prem inference is now operationally viable, which removes the last hard blocker that killed earlier pilots (Source: S1 high-level findings; D-004).

---

## 3. Business Objectives

### 3.1 SMART objective hierarchy

Targets are stated as ranges per D-009 (Federal Cost & Economic Conventions) and lift directly from T11 Stage 2 / Q11.7. Time horizons reference the post-pilot production state unless otherwise noted; the prototype itself is judged on demonstrability, not throughput.

| ID | Dimension | Metric | Target range | Time horizon | Source |
|----|-----------|--------|--------------|--------------|--------|
| BO-1 | **Throughput** | Reviewer minutes spent per simple application on data-entry verification | Reduction toward the lower end of the T11 Q11.4 range vs. the take-home 5–10 min baseline | Post-pilot, steady state | T11 Q11.4; take-home Sarah |
| BO-2 | **Accuracy** | Agreement between system-proposed disposition and reviewer disposition on retrospective Public COLA Registry sample | Within the calibration band defined in T11 Q11.7 with explicit false-approval and false-rejection sub-bounds | Prototype acceptance + steady state | T11 Q11.7; 01-requirements.md Hard tier |
| BO-3 | **Adoption** | Share of eligible simple applications routed through the assistive path with reviewer concurrence | Adoption-curve range from T11 Q11.7 sensitivity, conditional on Dave-class skeptic concurrence | 12–24 months post-pilot | T11 Q11.7; T10 Q10.4 |
| BO-4 | **Compliance** | Every disposition emitted carries a regulation-cited explanation suitable for audit | 100% of dispositions, no exceptions | Prototype acceptance | 01-requirements.md Hard tier; D-007 |

### 3.2 Strategic alignment

The prototype aligns with three concentric mandates: (i) TTB's own labeling-modernization arc, visible in Treasury Decisions TTB-158 (wine, 2020), TTB-176 (distilled spirits and malt beverages, 2022), and successor technical corrections, which has been simplifying and consolidating labeling regulation but has not modernized the *review* tooling at the same pace; (ii) Treasury's broader IT-modernization posture; and (iii) federal-wide expectations under OMB Circulars A-94 (Nov 2023, benefit-cost analysis of federal spending) and A-130 (information-as-strategic-resource), with cost-estimate quality benchmarked to GAO-20-195G (Source: T7 federal deployment / policy gradation; R0 federal cost conventions).

### 3.3 Non-objectives

- **Not a reviewer-replacement system.** The prototype is decision-support; final disposition remains with a human label specialist (Source: take-home Marcus "standalone proof-of-concept"; D-001).
- **Not a COLAs Online integration.** No reads from, no writes to, the system of record (Source: take-home Marcus; D-003).
- **Not a reviewer of allowable revisions.** Post-approval changes to approved labels under TTB's allowable-revisions guidance are out of scope (Source: S2 D-010; D-003).
- **Not a cross-commodity expansion** beyond wine, distilled spirits, and malt beverages governed by 27 CFR Parts 4, 5, 7 and the Part 16 health-warning regime. Beverages outside that perimeter (cider <7% ABV, certain saké products that fall under FDA labeling, etc.) are out of scope (Source: T1 scope; D-003; S2 D-010).
- **Not a class/type-specific reviewer for the long tail.** Conditional fields like sulfite declarations, organic claims, FD&C Yellow #5, cochineal/carmine, and major-allergen disclosures are explicitly deferred (Source: S2 D-010; D-003).

---

## 4. Stakeholders

### 4.1 Stakeholder roster

Roster lifts the salience model from T10 Q10.1–Q10.2. Influence is intentionally phase-dependent; D-001 explains why the order flips between prototype and production (see §4.3).

| Stakeholder | Role | Prototype-stage influence | Production-stage influence | Primary interest | Success criterion |
|-------------|------|---------------------------|----------------------------|------------------|-------------------|
| **Sarah** | Senior label specialist (the reviewer who feels the pain) | High | High | Get her time back from data entry; keep judgment work | Time-to-decision on simple applications drops noticeably; she still owns the call (Source: T10 Q10.1) |
| **Dave** | Senior label specialist (skeptic, nuance-sensitive) | High | High | System does not over-claim; nuance is respected; manual override always works | Every disposition cites the reg; he can override in one click (Source: T10 Q10.4) |
| **Jenny** | Label specialist (workflow-pragmatist, paper-checklist user) | Medium | Medium | Tooling matches the order she actually applies rules | The on-screen explanation reads the way her checklist reads (Source: T10 Q10.5) |
| **Marcus** | IT / security stakeholder | High | High | Standalone proof-of-concept; nothing crazy; firewall-deployable on the production path | Prototype clears prototype-tier security bar; design has a credible on-prem story (Source: take-home Marcus; T10 Q10.6) |
| **TTB CIO** *(emergent at production stage)* | Treasury IT authorizing leadership | Low | High | ATO posture, FedRAMP, sustainable cost | Production design has a documented authorization path (Source: T10 Q10.2; T7) |
| **FedRAMP Authorizing Official** *(emergent)* | Cloud authorization | None | High | Service categorization (Moderate vs. High) | Path to FedRAMP package is plausible at production (Source: T7) |
| **OMB program examiner** *(emergent)* | Budget oversight | None | High | A-94-conforming benefit-cost case | BCA holds up under A-94 sensitivity tests (Source: R0; T11) |
| **Industry applicants** *(indirect)* | Wineries, distillers, brewers, importers | None | Medium | Faster, more consistent decisions | Median processing time trends down; fewer arbitrary-feeling rejections (Source: T10 Q10.2) |

### 4.2 RACI for the prototype phase

Lifted from T10 Q10.3.

| Activity | Sarah | Dave | Jenny | Marcus | Project team |
|----------|:-----:|:----:|:-----:|:------:|:------------:|
| Define "simple application" scope | C | C | I | I | **R/A** |
| Define field manifest for Parts 4/5/7 | C | **R** | C | I | A |
| Define disposition explanation format | **R** | C | C | I | A |
| Set latency / UX bar | **R** | C | C | C | A |
| Approve security posture for prototype demo | I | I | I | **R/A** | C |
| Acceptance test the prototype | **R** | **R** | C | C | A |
| Approve scope cuts (D-010) | C | C | I | C | **R/A** |

(R = Responsible, A = Accountable, C = Consulted, I = Informed.)

### 4.3 Phase-dependent priority

D-001 records that stakeholder influence intentionally re-orders between prototype and production. **In the prototype phase**, the four take-home stakeholders (Sarah, Dave, Jenny, Marcus) are dominant — they are the people who decide whether the prototype is credible, whether it earns a pilot, and whether reviewers trust it. CIO/FedRAMP/OMB stakeholders are *informed* but not gating. **In the production phase**, the order flips: a working prototype that reviewers love is necessary but not sufficient, and the gating actors become the authorizing officials whose signatures unlock funding and ATO. Designing for the prototype audience first is a deliberate sequencing choice, not an oversight (Source: D-001; T10 Q10.2).

### 4.4 Top-tier concerns and mitigations

- **Sarah — "What if it's wrong and I miss the override?"** Mitigated by the always-available manual review path, by the senior-friendly UI bar (see §5.4), and by surfacing model uncertainty rather than hiding it (Source: T10 Q10.4; 01-requirements.md Strong tier).
- **Dave — "It will pretend to understand nuance it doesn't."** Mitigated by the deterministic rule core: the AI extracts and proposes; the verdict logic is explicit, regulation-cited, and inspectable. If the system can't cite a rule, it can't issue a disposition (Source: D-007; T10 Q10.4).
- **Jenny — "It won't read like my checklist."** Mitigated by aligning the explanation format to the reviewer's mental model (rule-by-rule, in the order she actually checks them) rather than to a model-output dump (Source: T10 Q10.5).
- **Marcus — "Don't drag me into a FedRAMP fight for a prototype."** Mitigated by an explicit prototype-tier compliance posture (see §8.2): no PII, no production data, no ATO claim, "just don't do anything crazy" (Source: take-home Marcus; T10 Q10.6; T7).
- **Pre-mortem composite — "Cold-start latency, vendor lock-in, and a regulatory change land mid-build."** All three are tracked in the §10.1 risk register with named mitigations (Source: T10 Q10.7).

---

## 5. Business Requirements

These are *business* requirements (what and why), not functional or technical (how). Functional decomposition belongs in the PRD; component design belongs in the Architecture Doc. Each requirement is BR-numbered, single-sentence, with rationale and source.

### 5.1 Core verification requirements

- **BR-001 — Brand-name verification.** The system shall confirm that the brand name appearing on the label artwork matches the brand name declared on the application. *Rationale:* the most basic identity check and the one that fails most often on data-entry grounds. *Source:* take-home tech requirements; T1 §1.1.
- **BR-002 — Alcohol-content (ABV / ALC/VOL) verification.** The system shall confirm that the alcohol-content statement on the artwork is present, legible, and consistent with the application and with class/type permitted ranges where applicable. *Source:* take-home tech requirements; 27 CFR Parts 4/5/7; T1 §1.1.
- **BR-003 — Net-contents verification.** The system shall confirm a net-contents statement is present on the artwork and consistent with the application. *Source:* take-home tech requirements; T1 §1.1.
- **BR-004 — Government health-warning verification.** The system shall confirm the government health warning statement required by 27 CFR Part 16 is present on the artwork. *Rationale:* a single mandatory statement, identical across commodities, the absence of which is a hard rejection ground. *Source:* 27 CFR 16.21; take-home tech requirements; T1 §1.1.
- **BR-005 — Bottler / importer name-and-address verification.** The system shall confirm the bottler or importer name-and-address block is present and consistent with the application. *Source:* take-home tech requirements; T1 §1.1.
- **BR-006 — Country-of-origin verification (imports).** For imported applications, the system shall confirm a country-of-origin statement is present. *Source:* take-home tech requirements; T1 §1.1.

### 5.2 Reasoning and audit-trail requirements

- **BR-007 — Citation-grounded disposition.** Every disposition emitted by the system shall include a human-readable explanation that cites the specific CFR section(s) supporting the finding and identifies the evidence used. *Rationale:* elevated to the Hard tier of 01-requirements.md after Dave's skepticism interview; the system is decision-support, not an oracle. *Source:* D-007; 01-requirements.md Hard tier; T10 Q10.4.
- **BR-008 — Non-disposition mode for low-confidence cases.** Where the system cannot extract a required field with sufficient confidence, it shall surface "needs human review" rather than fabricating a disposition. *Rationale:* failure mode shall be transparent ignorance, not confident error. *Source:* D-007.
- **BR-009 — Audit trail.** The system shall produce an audit record per disposition consisting of input artifact reference, fields extracted, rules applied, citations, and reasoning, in a form usable in regulatory audit. *Source:* D-007; 01-requirements.md Hard tier.

### 5.3 Throughput and latency requirements

- **BR-010 — Single-label latency.** The system shall return a draft disposition for a single typical label within approximately five seconds of submission. *Rationale:* this is the empirical reviewer-tolerance ceiling Sarah cited and the bar that killed the prior scanning-vendor pilot when missed. *Source:* take-home Sarah verbatim; D-010; T2.
- **BR-011 — Batch handling.** The system shall handle batches representative of peak-season importer drops on the order of 200–300 labels at a time without per-item latency degradation that would block reviewer use. *Source:* take-home Sarah verbatim; D-010.

### 5.4 Usability requirements

- **BR-012 — Senior-friendly UI ("73-year-old benchmark").** The user interface shall be usable by a senior reviewer at the upper end of the workforce age distribution: high contrast, predictable layout, explicit affordances, no hidden gestures. *Source:* take-home Sarah; 01-requirements.md Strong tier.
- **BR-013 — Always-available manual review path.** The reviewer shall always retain the ability to override, defer, or escalate a system-proposed disposition; the manual path is never gated by AI availability. *Source:* take-home Sarah and Dave; 01-requirements.md Strong tier; D-001.
- **BR-014 — Explanation legibility.** The on-screen explanation shall present rules in the order a reviewer applies them in practice, not in the order the model emitted them. *Source:* take-home Jenny; T10 Q10.5.

### 5.5 Production-parity design requirements (business language)

- **BR-015 — Deployable in firewalled federal environments.** The solution architecture shall be deployable in environments that block outbound cloud calls; reliance on any single SaaS endpoint at the inference path shall be a substitutable choice, not a structural assumption. *Rationale:* this is the firewall reality Marcus stated as non-negotiable for a production trajectory; designing the prototype against this constraint preserves the production option. *Source:* take-home Marcus; D-004.
- **BR-016 — On-prem inference path preserved.** The system's economic and operational model shall support an on-prem inference path as a credible production option, even if the prototype itself uses hosted inference for expediency. *Source:* take-home Marcus; D-004.

### 5.6 Regulatory coverage requirements

- **BR-017 — Common-fields coverage across three commodities.** The system shall cover the common mandatory-field manifest applicable to wine (Part 4), distilled spirits (Part 5), and malt beverages (Part 7), plus the universal Part 16 health-warning requirement. *Source:* T1 scope; D-003; D-010; 27 CFR Parts 4/5/7/16.
- **BR-018 — Class-specific deferrals.** Class-specific and conditional rules (e.g., distilled-spirits class/type conditions, age statements, appellations, sulfite/organic/allergen/cochineal disclosures) are deferred from the MVP and treated as future-phase extensions. *Source:* D-003; D-010; S2.

---

## 6. Project Scope

### 6.1 In-scope (MVP)

Lifts S2 D-010 in business language:

- A standalone web-deployable prototype that accepts a label artwork plus a mocked application record and returns, within the latency bar, a draft disposition for the common-fields manifest in §5.1.
- Coverage of wine (≥7% ABV), distilled spirits, and malt beverages at the common-fields level.
- A reviewer-facing screen that (a) shows the extracted fields, (b) shows the rule-by-rule findings with CFR citations, and (c) preserves a manual override path.
- An audit record per disposition.
- A demonstrable sample dataset drawn from the public COLA Registry, used as test corpus only.

(Source: S2 D-010 MVP section; take-home tech requirements.)

### 6.2 Stretch

- Class-specific rule packs for one of the three commodities, demonstrating extensibility (Source: S2 D-010 stretch).
- Batch-mode demo at importer-drop scale (200–300 labels) showing latency does not degrade unacceptably (Source: S2 D-010 stretch; take-home Sarah).
- A confidence-calibrated "needs human review" routing surface that is empirically validated against a held-out sample (Source: S2 D-010 stretch).

### 6.3 Out of scope

- COLAs Online integration of any kind (no reads, no writes, no auth federation) (Source: D-003; take-home Marcus).
- Allowable-revisions review of post-approval label changes (Source: S2 D-010; D-003).
- Post-approval change auditing or surveillance (Source: S2 D-010).
- Conditional / long-tail fields: sulfite declarations, organic claims, FD&C Yellow #5, cochineal/carmine, major-allergen labeling under TTB Notice 238 (Source: D-003; D-010).
- Beverages outside Parts 4/5/7 (e.g., wines <7% ABV under FDA, certain saké formulations) (Source: T1 scope; D-003).
- Any production ATO claim, FedRAMP package, or PIV/SAML integration (Source: take-home Marcus prototype-tier guidance; T7).

### 6.4 Future phases (informational, not committed)

These are sequenced for orientation, not promised:

- **Phase 2 — Production pilot** with a single ALFD reviewer cohort, real (non-PII) artwork, and an internal feedback loop.
- **Phase 3 — FedRAMP / ATO path,** likely targeting FedRAMP Moderate as the most common federal posture for sensitive-but-unclassified workloads, with FedRAMP High evaluated only if data sensitivity warrants.
- **Phase 4 — COLAs Online integration,** contingent on Treasury IT modernization roadmap and the broader myTTB platform direction.

(Source: T7 staging map.)

---

## 7. Cost-Benefit Analysis

This section synthesizes T11 (economic analysis) and T12 (decision communication) outputs. **Figures are cited, not regenerated**, and are presented as ranges per D-009.

### 7.1 Methodology statement

The cost-benefit analysis follows OMB Circular A-94 (revised November 9, 2023), "Guidelines and Discount Rates for Benefit-Cost Analysis of Federal Programs," for benefit-cost framing and discount-rate selection, and references GAO-20-195G ("Cost Estimating and Assessment Guide," March 2020) for cost-estimate structure and the "comprehensive / well-documented / accurate / credible" quality bar. Per D-009, all quantitative outputs are presented as ranges with explicit drivers, and a cost-effectiveness analysis (CEA) framing is used alongside benefit-cost where benefits are partly non-monetizable (Source: D-009; R0; OMB Circular A-94 §§9 and Appendix D; GAO-20-195G ch. 3).

### 7.2 Labor savings model summary

The labor-savings calculation is structured (per T11 Stage 1–2) as:

> **Annual labor savings range = (per-application minutes saved range) × (annual application volume range) × (loaded labor rate range), then haircut by a realization rate.**

The drivers, lifted from T11:

- **Per-application minutes saved.** The take-home baseline is 5–10 minutes per simple application; T11 Q11.4 reports the savings range as a fraction of that baseline, conservative on the low end and optimistic on the high end. The figure is *not* "minutes eliminated" but "minutes the reviewer would otherwise have spent on data-entry verification that the system can reliably handle."
- **Annual volume.** ~150,000 COLA applications/year, with a band reflecting year-over-year variance and the share that falls into the "simple application" envelope (Source: T11 Q11.4; T2).
- **Loaded labor rate.** Federal label specialists sit predominantly in the GS-12/GS-13 band; T11 Q11.4 uses a fully-loaded labor-rate range (base + locality + benefits + overhead) consistent with R0 federal cost conventions, not raw base salary.

The aggregate annual labor-savings range and its sensitivity bounds are the figures reported in T11 Q11.7. **The realization-rate haircut (see §7.6) is applied before any number is treated as a "budget savings" figure.** (Source: T11 Q11.4, Q11.7, Q11.8.)

### 7.3 Per-option cost summary

The options table below lifts the structure of T11 Stage 3 / Q11.10–Q11.15. Specific dollar ranges are not re-derived here; they are cited from T11 by row.

| Option | One-time cost range | Recurring cost range | Variable / per-application cost range | 3-yr horizon | 5-yr horizon | T11 source |
|--------|---------------------|----------------------|---------------------------------------|--------------|--------------|------------|
| **A. Status quo (do nothing)** | None | Existing labor cost (baseline) | Reviewer minutes per app | Baseline | Baseline | T11 Q11.10 |
| **B. Hosted-cloud AI service** (lowest build cost, highest production-friction) | Low | Low–medium SaaS subscription | Per-call API cost — exposed to vendor price moves | Q11.11 range | Q11.11 range | T11 Q11.11 |
| **C. Hybrid (cloud for prototype, on-prem path designed-in)** — the prototype's posture | Low–medium | Medium | Medium, declining if/when on-prem migration occurs | Q11.12 range | Q11.12 range | T11 Q11.12 |
| **D. On-prem inference** (highest build cost, lowest variable cost, firewall-clean) | Medium–high (GPU hardware + setup) | Medium (ops + maintenance) | Low marginal per call | Q11.13 range | Q11.13 range | T11 Q11.13 |

(Cost ranges and assumptions per T11 Q11.10–Q11.15. The prototype itself is Option C; Options B and D are evaluated as production-trajectory anchors.)

### 7.4 Net-value comparison

T11 Stage 4 / Q11.16 reports net-value ranges per option using the A-94 discount-rate guidance. The key comparisons (cited, not regenerated):

- **Option A (status quo)** is the comparator; net value is zero by construction.
- **Option C (the hybrid posture this prototype takes)** is positive across most of the sensitivity envelope on both 3- and 5-year horizons, with the dominant driver being labor savings net of build cost; break-even is reached well inside the 3-year window in the central case (Source: T11 Q11.16).
- **Option D (on-prem)** has higher upfront cost but the most favorable steady-state per-call economics; net-value crossover with Option C occurs further out and is sensitive to volume assumptions (Source: T11 Q11.16).
- **Option B (hosted-only)** has the lowest upfront cost but the highest exposure to vendor-pricing risk and federal-firewall risk; net-value is most fragile under sensitivity (Source: T11 Q11.16; T12 visualization recommendations).

T12 recommends presenting net-value comparisons as range bars rather than point estimates, with the realization-rate axis explicit on the chart — this BRD adopts that recommendation in any decision-pack derived from it (Source: T12).

### 7.5 Sensitivity findings

T11 Q11.18–Q11.19 report the sensitivity profile. The recommendation is robust to:

- ±20% on per-application minutes saved.
- ±20% on annual application volume.
- ±20% on loaded labor rate.

The recommendation **flips** under these conditions (Source: T11 Q11.19):

- A realization rate near the low end of the band combined with vendor price escalation favors Option D (on-prem) over Option B (hosted-only) on the 5-year horizon.
- A regulatory shock that materially changes the field manifest mid-build (e.g., a major-allergen final rule) shifts net value down across all active-build options and could push Option A back into contention temporarily.

### 7.6 Realization-rate caveat

The single most consequential and most uncertain number in this analysis is the **realization rate** — the conversion of theoretical reviewer-minutes-saved into actual budget savings or actual additional throughput. T11 Q11.8 makes this explicit: time saved on a single application does not automatically aggregate into a removable FTE or a re-deployable budget line, because (i) reviewer time freed up tends to be absorbed by judgment work that was previously crowded out, (ii) federal labor cost is largely fixed in the short run, and (iii) realization is mediated by adoption (BO-3). The headline-savings figures in §7.2 should not be read as a direct budget-reduction claim; they are a labor-capacity figure (Source: T11 Q11.8).

### 7.7 Non-monetizable factors

T11 Q11.17 identifies four classes of benefit that are real but not cleanly monetizable:

- **Risk reduction.** Citation-grounded dispositions reduce the rate of unexplained or inconsistent decisions, which lowers downstream litigation and challenge risk.
- **Agent experience.** Sarah's "drowning in routine stuff" is a retention-and-morale issue, not just a throughput issue.
- **Public trust.** Faster, more consistent decisions improve industry-side perception of TTB without changing the regulatory bar.
- **Optionality.** A working prototype that respects the firewall constraint preserves the option to scale to production without re-architecting; this option value is real and routinely under-counted.

### 7.8 Headline framing

Per T11 Q11.20: *Even on conservative realization assumptions, the prototype-tier and pilot-tier costs are materially smaller than the labor-capacity savings range across a 3- and 5-year horizon, and the dominant non-monetizable benefits — reviewer time redirected to judgment work, citation-grounded auditability, preserved on-prem option — point in the same direction.* This is not a "the AI will save $X million" claim; it is a directional, range-based, sensitivity-tested recommendation to proceed past the prototype gate (Source: T11 Q11.20).

---

## 8. Compliance and Regulatory Posture

### 8.1 Authority basis

The substantive regulatory authority the prototype's rule logic encodes derives from:

- **27 CFR Part 4** — Labeling and Advertising of Wine (≥7% ABV), per T.D. TTB-158 (Apr 2, 2020) and subsequent amendments.
- **27 CFR Part 5** — Labeling and Advertising of Distilled Spirits, per T.D. TTB-176 (Feb 9, 2022) and T.D. TTB-199 (Dec 18, 2024, addition of American Single Malt Whisky to the Standards of Identity).
- **27 CFR Part 7** — Labeling and Advertising of Malt Beverages, per T.D. TTB-176 (Feb 9, 2022).
- **27 CFR Part 16** — Alcoholic Beverage Health Warning Statement, implementing the Alcoholic Beverage Labeling Act of 1988.

(Source: T1 §0; eCFR Title 27, Chapter I, Subchapter A.)

### 8.2 Federal IT compliance posture — prototype phase

Marcus's guidance for the take-home prototype is operationally precise: *"for a prototype, just don't do anything crazy."* Concretely:

- **No PII storage or processing.** The prototype operates on label artwork (which is published in the Public COLA Registry once approved) and mocked application metadata.
- **No production data.** No live COLAs Online cases, no real applicant submissions in flight.
- **No ATO claim.** The prototype is not asserted as authorized to operate; it is a demonstration artifact.
- **No FedRAMP package.** Not in scope at this tier.
- **Standard prototype hygiene.** TLS, no secrets in source, no logging of sensitive content beyond what is required to reproduce a defect.

(Source: take-home Marcus interview; T7 prototype-tier compliance map.)

### 8.3 Federal IT compliance posture — production phase (informational)

For situational awareness only; not a commitment of this BRD:

- **FedRAMP Moderate** is the most common authorization level for sensitive-but-unclassified federal workloads and is the likely target if any cloud component remains in the production architecture; **FedRAMP High** would only be invoked if the data classification analysis at production scoping warrants.
- **ATO** under the agency's own NIST RMF process, with a Treasury or TTB authorizing official as signatory.
- **Identity:** PIV-card and/or SAML federation against Treasury identity infrastructure.
- **Document retention** consistent with Federal Records Act and TTB's records schedules.
- **Hosting:** on-prem behind the federal firewall, or a Government Community Cloud (e.g., Azure Government / AWS GovCloud) authorized at the appropriate FedRAMP level.

(Source: T7 staging map; FedRAMP.gov authorization framework.)

### 8.4 Data handling posture

The prototype shall not persist submitted artwork beyond the active session beyond what is required for the audit record under BR-009. This is a Strong-tier requirement in 01-requirements.md and a precondition of the prototype-tier compliance posture in §8.2 (Source: 01-requirements.md Strong tier; D-007).

### 8.5 Audit and traceability

Every disposition shall produce an audit trail consisting of (a) the input artifact reference, (b) the fields extracted with confidence indicators, (c) the rules evaluated, (d) the CFR citations supporting each finding, and (e) the reasoning trace. The audit trail shall be sufficient to reconstruct the disposition during a regulatory audit. (Source: D-007; BR-007; BR-009.)

---

## 9. Constraints, Assumptions, Dependencies

### 9.1 Constraints

- **C-1 Time-boxed take-home build.** The prototype is delivered against the take-home brief's schedule, not an open-ended R&D timeline (Source: take-home brief).
- **C-2 Federal firewall.** The production-trajectory architecture must be deployable in environments that block outbound cloud calls (Source: take-home Marcus; D-004).
- **C-3 Five-second latency ceiling.** Non-negotiable for single-label review based on Sarah's empirical reviewer-tolerance data and the failed prior pilot (Source: take-home Sarah; D-010).
- **C-4 Senior-friendly UX bar ("73-year-old benchmark").** The UI is designed for the upper end of the workforce age distribution, not for tech-forward early adopters (Source: take-home Sarah; 01-requirements.md Strong tier).
- **C-5 Standalone, no COLAs Online integration.** Prototype is intentionally decoupled from the system of record (Source: take-home Marcus; D-003).

### 9.2 Assumptions

- **A-1** Application input can be mocked for the prototype; the public COLA Registry is a reasonable test corpus (Source: take-home; T2).
- **A-2** A reviewer can run the deployed prototype against a URL from a standard browser without elevated privileges (Source: take-home Marcus, prototype tier).
- **A-3** Annual application volume of ~150,000/year is stable enough to support a 3-year economic horizon for the BCA (Source: T2; T11 Q11.4).
- **A-4** The common-fields manifest derived from Parts 4/5/7/16 is stable over the build horizon notwithstanding ongoing TTB modernization rulemaking (see Risk RR-04).

### 9.3 Dependencies

The prototype depends on:

- A vision/OCR component capable of extracting label fields from typical artwork formats.
- A structured-output language model for field disambiguation and disposition reasoning surfacing.
- The public text of 27 CFR Parts 4, 5, 7, 16 via eCFR.
- The TTB Public COLA Registry as a test data source.

**This BRD does not commit to specific vendors or models** — that is an Architecture Doc concern. Vendor selection is a substitutable choice and shall preserve BR-015 (firewall deployability) and BR-016 (on-prem path). (Source: D-004; Arch Doc scope boundary.)

---

## 10. Risks and Mitigations

### 10.1 Risk register

Lifted from T10 Q10.7 pre-mortem.

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|----|------|:----------:|:------:|------------|-------|
| **RR-01** | Cold-start latency exceeds five seconds in real reviewer workflow, repeating the prior-pilot failure mode | Medium | High | Latency budgeted explicitly in BR-010; pre-warm strategy designed-in; demo measured against the bar, not against a synthetic benchmark | Project team |
| **RR-02** | Realization-rate gap — labor minutes saved do not translate into budget savings or throughput | High | High (for the BCA, not for the prototype demo) | Headline framed as labor-capacity, not budget-cut, per §7.8; BCA presented in ranges per D-009; non-monetizable benefits stated explicitly per §7.7 | Sponsor + project team |
| **RR-03** | Vendor-API price escalation or vendor lock-in on hosted-cloud inference path | Medium | Medium | BR-015 / BR-016: substitutability designed-in at the inference seam; Option D (on-prem) economics tracked alongside Option C in §7.3 | Architect (Arch Doc) |
| **RR-04** | Regulatory change during build — e.g., wine modernization successor rulemaking, Notice 238 (major-allergen labeling) finalization, standards-of-fill amendments under TTB-200 | Medium | Medium | Field manifest scoped to Hard-tier common fields only (BR-017); class-specific deferrals explicit (BR-018); rule logic isolated from extraction so a citation update does not require model retraining | Project team |
| **RR-05** | Adoption friction — Dave-class skepticism vector dominates and the tool is rejected on principle | Medium | High | Citation-grounded explanations (BR-007); always-available manual override (BR-013); no-disposition mode for low confidence (BR-008); explanation legibility matched to reviewer mental model (BR-014) | Product/UX |
| **RR-06** | Federal authorization timeline in production phase blocks deployment past prototype | Medium (production), N/A (prototype) | High (production) | Prototype-tier compliance posture (§8.2) keeps the demo unblocked; production posture (§8.3) is informational and sequenced honestly | CIO / authorizing official (production) |
| **RR-07** | Prototype is mistaken for a production-ready system | Medium | Medium | Explicit non-objectives in §3.3; out-of-scope items in §6.3; BRD framing ("standalone proof-of-concept") repeated throughout | Sponsor |

### 10.2 Open questions and decisions deferred

Pulled from 01-requirements.md still-open items, 04-research-topics.md, and 05-gaps-and-limitations.md:

- **OQ-1** What is the canonical application-input format the prototype should accept? Mocked JSON suffices for the take-home; the production answer depends on COLAs Online schema access (Source: 04-research-topics.md).
- **OQ-2** What auth posture should the deployed-URL demo carry — open URL, basic auth, or a shared link with rotating token? (Source: 05-gaps-and-limitations.md.)
- **OQ-3** Should disposition codes be free-text or constrained to a structured reason-code enum? Structured codes improve auditability but require an upfront taxonomy decision (Source: 04-research-topics.md.)
- **OQ-4** How should the prototype represent confidence — a numeric score, a tri-state band (high/medium/low), or no-answer-below-threshold only? Linked to BR-008 design (Source: 01-requirements.md.)
- **OQ-5** What sample of the Public COLA Registry constitutes a defensible test corpus for accuracy reporting against BO-2? (Source: 04-research-topics.md.)
- **OQ-6** **Conflict log.** Where T-output research and the take-home brief disagree, the take-home wins per the project's ground-truth convention; remaining conflicts are tracked in 05-gaps-and-limitations.md.

---

## 11. Glossary

| Term | Definition |
|------|------------|
| **ABV** | Alcohol By Volume — the volumetric percentage of ethanol in a beverage. |
| **ALC/VOL** | The form in which alcohol content is typically stated on the label (e.g., "40% ALC/VOL"). |
| **ATO** | Authority to Operate — a federal authorizing official's signed acceptance of risk to run an information system in production, per the NIST Risk Management Framework. |
| **BRD** | Business Requirements Document — this document; states what the business needs and why, not how to build it. |
| **CFR** | Code of Federal Regulations — the codified version of federal regulations published in the Federal Register. |
| **COLA** | Certificate of Label Approval — TTB's pre-market approval issued on Form 5100.31 authorizing bottling, removal from customs, or distribution of an alcohol beverage under an approved label. |
| **CPI** *(TTB sense)* | Characters Per Inch — a typographic constraint TTB uses for label legibility (distinct from the economic Consumer Price Index). |
| **FedRAMP** | Federal Risk and Authorization Management Program — the standardized federal approach to security assessment and authorization of cloud products and services; impact levels are Low, Moderate, and High. |
| **GS-grade** | General Schedule grade — the federal civilian pay scale; label specialists sit predominantly in the GS-12/GS-13 band. |
| **OCR** | Optical Character Recognition — extracting text from images. |
| **PIV** | Personal Identity Verification — the federal smartcard-based identity standard (FIPS 201). |
| **PRD** | Product Requirements Document — the functional companion to this BRD. |
| **SAML** | Security Assertion Markup Language — a federation protocol for single sign-on. |
| **SoI** | Standard of Identity — the regulatory specification of what may be sold as a given class/type (e.g., "bourbon whiskey"). |
| **SoC** | Statement of Composition — required compositional declaration where a product does not meet a Standard of Identity. |
| **TD** | Treasury Decision — TTB's published rulemaking citation (e.g., T.D. TTB-176). |
| **TTB** | Alcohol and Tobacco Tax and Trade Bureau — the Treasury bureau that administers federal alcohol-labeling regulation. |

---

## 12. Appendices

### 12.1 Cross-reference map

| This BRD section | Companion artifact | Notes |
|------------------|--------------------|-------|
| §3 Objectives | T11 Q11.7 (target ranges), 01-requirements.md tiers | Targets stated as ranges per D-009 |
| §4 Stakeholders | T10 Q10.1–Q10.7 | Salience, RACI, empathy, JTBD, pre-mortem all originate in T10 |
| §5 Business requirements | 01-requirements.md (Hard / Strong / Should tiers); take-home brief | BRs are business-level; functional decomposition lives in PRD.md |
| §5.5 Production-parity | D-004; take-home Marcus | Engineering articulation lives in ARCHITECTURE.md |
| §6 Scope | S2 D-010 | MVP / stretch / out-of-scope lifted directly |
| §7 Cost-benefit | T11 Q11.4–Q11.20; T12 visualization | Cited, not regenerated |
| §7.1 Methodology | OMB Circular A-94 (Nov 9, 2023); GAO-20-195G; D-009; R0 | Federal cost conventions |
| §8 Compliance | T7 staging map; take-home Marcus; 27 CFR Parts 4/5/7/16 | Prototype-tier vs. production-tier explicit |
| §9 Constraints | D-001 through D-010 | Decision log is the canonical source |
| §10.1 Risks | T10 Q10.7 pre-mortem | Owner column reflects phase-dependent priority (D-001) |
| §10.2 Open questions | 01-requirements.md, 04-research-topics.md, 05-gaps-and-limitations.md | Conflict log lives in 05- |
| §11 Glossary | T1 §0; project-wide | — |
| §12 Appendices | This section; PRD.md §Appendix; ARCHITECTURE.md §Appendix | Three documents share a cross-reference convention |

### 12.2 Source documents consulted

- Take-Home_Project__AI-Powered_Alcohol_Label_Verification_App.docx (ground truth — wins ties).
- Project research outputs: 00-research-plan.md, 01-requirements.md, 02-architecture.md, 03-decisions.md, 04-research-topics.md, 05-gaps-and-limitations.md.
- Convention documents: R0-federal-cost-conventions.md.
- Topic outputs cited as primary in this BRD: T1 (regulatory framework), T2 (operational context), T7 (federal deployment / policy gradation), T10 (stakeholder analysis), T11 (economic analysis), T12 (decision communication).
- Topic outputs cited as secondary / "why now" tech context only: S1.
- Topic outputs explicitly excluded as primary sources for this BRD per scoping (PRD/Arch Doc material): T3, T4, T5, T6, T8, T9, S3, S4, S5.
- External anchoring references for federal-context facts: 27 CFR Parts 4, 5, 7, 16 (eCFR); T.D. TTB-158, TTB-176, TTB-196, TTB-199; OMB Circular A-94 (Nov 9, 2023); GAO-20-195G (March 2020); FedRAMP authorization framework.

---

*End of BRD.md*