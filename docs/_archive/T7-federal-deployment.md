# T7 — Federal Deployment: Policy Gradations & Compliance Pathways

**Phase:** 3 (Composed Architecture)
**Status:** PARTIAL — policy-landscape questions ready now; component-specific compliance posture needs T3, T4, T5
**Prerequisites:** T3, T4 for component-specific questions; T5 partial for AI-specific compliance; many questions ready now
**Blocks:** T8 partially; T11 partially; cross-topic synthesis X-3 and X-7

## Synopsis

The original framing of this topic treated federal compliance as a binary checklist: does this clear FedRAMP? Does it clear ATO? Does it pass Section 508? That framing is wrong. Federal cloud-and-AI compliance is **a gradient of allowability**, not a wall. Different workloads, data sensitivities, and authorization tiers enable different hosting and inference choices. The same architecture choice may be allowable, allowable-with-controls, or disallowed depending on what's running and on what data. Understanding the gradient is what lets us defend our architecture choices and project credible costs in T11.

This topic produces the policy-gradation map: **for what kind of workload, with what data sensitivity, what hosting and inference options are allowable, with what authorization timeline, at what compliance overhead cost.** That map then feeds the cost-of-each-option analysis in T11 and the headline trade-off chart in synthesis question X-7.

## Required reading

- All five core artifacts
- `R0-federal-cost-conventions.md` (compliance overhead enters the cost story; A-11 Exhibit 300 expects compliance posture as part of the business case)
- Background:
  - **FedRAMP authorization process and tiers** (Low, Moderate, High; agency ATO vs. Joint Authorization Board)
  - **FISMA categorization** (NIST SP 800-60, FIPS 199 / 200)
  - **NIST SP 800-53** control catalog
  - **OMB M-24-10** "Advancing Governance, Innovation, and Risk Management for Agency Use of Artificial Intelligence" and any successor memos
  - **NIST AI Risk Management Framework** (AI RMF 1.0, with Generative AI Profile)
  - **OMB M-22-09** "Moving the U.S. Government Toward Zero Trust Cybersecurity Principles"
  - **Section 508 / WCAG 2.1 AA** federal accessibility standards
  - **Treasury Acquisition Procedures** (TAP) for procurement-side requirements
  - **Azure Government** authorization scope and IL ratings (DoD Impact Levels, even though we're civilian)
  - **Privacy Act** and **PIA / SORN** requirements

## Output expected

A `T7-output.md` covering:

1. **Policy gradation map.** The headline output: matrix of workload type × data sensitivity × hosting/inference option → allowable / allowable-with-controls / disallowed → typical authorization timeline and overhead cost.
2. **AI-specific compliance landscape** under M-24-10 and successors.
3. **Per-option compliance posture** for the architectural choices in T4 and T5.
4. **Authorization timeline and cost overlay** that feeds T11.
5. **Treasury/TTB-specific posture** where it differs from cross-government baseline.
6. **Production-readiness gap** narrative that distinguishes "compliant" from "deployable."

## In-topic questions

### Policy-gradation map (headline output)

#### Q7.1 — Workload-sensitivity classification framework
*Architecture-level, can be researched now.* Federal compliance grades workloads along several axes. What are they?
- **Data sensitivity** (FIPS 199 categorization: Low / Moderate / High for confidentiality, integrity, availability)
- **Mission criticality** (does this directly support agency mission? Internal-process-only? Public-facing?)
- **PII content** (does the workload process personally identifiable information? What kind?)
- **AI characteristics** (rights-impacting? Safety-impacting? Per M-24-10 definitions)
- **Workload type** (compute, storage, AI inference, data labeling, etc.)

For our system: classify the realistic data sensitivity (probably Moderate confidentiality, Moderate integrity, Low availability — but verify), AI characteristics (likely "rights-impacting" under M-24-10 since it informs regulatory decisions), and mission posture.

#### Q7.2 — Hosting-option gradient
For each hosting option, what authorization is required?
- Public cloud commercial (AWS, GCP, Azure commercial): generally not allowable for federal data above Low
- FedRAMP-authorized cloud (Low, Moderate, High tiers)
- Cloud Service Offerings under Joint Authorization Board (JAB) vs. Agency ATO
- **Azure Government** specifically (TTB is on Azure per Marcus's interview)
- DoD-authorized clouds (IL2/4/5/6) — for context, not directly applicable to civilian
- On-premises agency-managed
- Air-gapped on-premises

For each: typical authorization timeline, controls required, overhead cost.

#### Q7.3 — Inference-option gradient
*The newer and less settled side of the gradient.* For each inference option, what's the policy posture?
- Cloud LLM API (OpenAI, Anthropic, Google) on commercial endpoints
- Cloud LLM API on FedRAMP-authorized endpoints (where they exist)
- Self-hosted LLM in FedRAMP-authorized cloud
- Self-hosted LLM on agency on-prem
- Self-hosted LLM in Azure Government

This intersects M-24-10 requirements specifically. AI use in rights-impacting contexts has additional controls regardless of where inference runs.

#### Q7.4 — Compose Q7.1 × Q7.2 × Q7.3 into the gradation matrix
*Synthesizes the prior three.* Build the matrix. For our specific workload classification (Q7.1 result): which combinations of hosting × inference are:
- **Allowable** with standard controls
- **Allowable-with-controls** (additional steps required)
- **Disallowed** (requires waiver, exception, or different approach)

Plus authorization timeline (months) and rough overhead cost per option.

This matrix is the most important output of T7. Everything downstream (T11, X-7) leans on it.

### AI-specific compliance

#### Q7.5 — OMB M-24-10 implications
*Architecture-level, ready now.* M-24-10 applies to federal AI use. What does it require?
- Inventory and reporting of AI use cases
- Risk-management practices for "rights-impacting" and "safety-impacting" AI
- Required risk controls (independent evaluation, ongoing monitoring, public engagement, etc.)
- Whether our system likely qualifies as rights-impacting (a regulatory-decision-support tool probably does)
- Implementation timelines and phased applicability
- Successor memos or amendments since initial issuance

#### Q7.6 — NIST AI RMF application
The AI Risk Management Framework provides operational guidance complementing M-24-10. What does it expect?
- The four core functions: Govern, Map, Measure, Manage
- Generative AI Profile additions
- How agencies are operationalizing this in 2024–2026

#### Q7.7 — AI-specific procurement and use restrictions
Beyond M-24-10, what other AI-specific federal restrictions apply?
- Restrictions on specific vendors / models (e.g., DeepSeek bans in some agencies)
- Open-weight vs. proprietary model considerations
- Training-data provenance requirements
- Licensing posture (Apache, MIT, OpenRAIL, custom)

### Per-option compliance posture

#### Q7.8 — OCR/vision options compliance posture [needs T4]
For each option T4 identifies, place it on the policy gradient:
- Cloud OCR (Google Document AI, AWS Textract, Azure Document Intelligence) — FedRAMP status, Azure Government availability
- Self-hosted OCR (Tesseract, PaddleOCR) — minimal compliance surface
- VLMs on cloud — combines hosting and AI compliance

#### Q7.9 — LLM/orchestration options compliance posture [needs T5]
For each option T5 identifies:
- Cloud LLM API (commercial vs. FedRAMP authorized variants where available)
- Self-hosted open-weight LLM (compliance posture by hosting environment)
- Hybrid arrangements

#### Q7.10 — Rule engine and deterministic components
*Mostly a non-issue.* Confirm that deterministic code components don't introduce compliance burden beyond standard application security. Note where they do (e.g., logging requirements, audit trail).

### Authorization timeline and cost overlay

#### Q7.11 — Typical authorization timelines
For each option in the gradation matrix:
- ATO duration (typical months from initial submission to authorization)
- FedRAMP authorization (where applicable)
- Continuous monitoring overhead
- Re-authorization cadence

These numbers feed T11 directly — compliance overhead is a real cost component, often underestimated.

#### Q7.12 — Compliance overhead cost components
What does compliance actually cost?
- Personnel (compliance specialists, security engineers)
- Audit and assessment (3PAO costs for FedRAMP)
- Tooling and continuous monitoring
- Documentation and POA&M maintenance
- Re-authorization

Express as ranges (per GAO-20-195G conventions). For a Moderate-tier IT investment this is typically substantial — credible figures are needed for T11.

### Treasury/TTB specific

#### Q7.13 — Treasury IT compliance baseline
*Architecture-level, ready now.* What does Treasury require beyond cross-government baseline?
- Treasury Acquisition Procedures (TAP) Subpart 1007.70 (referenced in IRS guidance)
- Treasury-specific security controls
- Treasury Office of CIO governance and review steps
- Bureau-level (TTB) specific controls

#### Q7.14 — TTB IT environment specifics
Marcus's interview mentioned TTB migrated to Azure in 2019, the prior vendor pilot was blocked by firewall, and FedRAMP took 18 months "just for the paperwork." What can we learn about TTB's specific environment?
- Azure Government usage (Commercial vs. Gov tenant)
- Outbound traffic posture (which domains allowed)
- Identity infrastructure (PIV/CAC, federation)
- Existing AI/ML deployments in TTB if any
- Recent TTB modernization initiatives

### Authentication, authorization, identity

#### Q7.15 — Identity and access patterns
*Standard, ready now.* For ~47 ALFD agents using the system:
- PIV/CAC authentication
- SAML/OIDC federation with Treasury identity infrastructure
- Role-based access control (agent / supervisor / admin)
- Audit logging requirements
- Composition with our prototype's simple-auth deployment

### Section 508 accessibility

#### Q7.16 — Section 508 specifications
*Ready now; feeds T8.* Federal IT must meet Section 508 standards (currently aligned with WCAG 2.1 AA via the Section 508 Refresh).
- Specific requirements (keyboard nav, screen reader support, contrast minimums)
- Conformance testing posture
- Implications for our UI components (image-region highlighting, batch UI, evidence display)

### Production-readiness narrative

#### Q7.17 — "Compliant" vs. "deployable" gap
*Synthesizes most prior questions.* For each architectural option, distinguish:
- **Compliant** — meets the legal/regulatory requirements
- **Deployable** — actually clears the agency's specific gauntlet (which is more than compliance; includes politics, legacy integrations, and idiosyncratic agency processes)

The gap between compliant and deployable is where federal IT projects historically die. Articulate it for our specific options.

#### Q7.18 — Production-readiness gap categories [needs T3, T4, T5]
Once components are known, classify gaps:
- "Acceptable for prototype, must be fixed for production"
- "Acceptable for production but suboptimal"
- "Architecturally blocking — requires redesign"

This becomes part of the README's trade-offs discussion.

## Cross-topic synthesis questions
*(Held for later.)*

- **X-3 (T3+T4+T5+T7):** End-to-end production-readiness gap. Hold.
- **X-7 (T7+T11+T12):** Cost × policy × technical fit per option. Hold for synthesis.

## Notes for the researcher

- The shift from "checklist compliance" to "policy gradient" is the headline framing of this topic. Resist sliding back into yes/no thinking.
- M-24-10 and AI-specific guidance is **moving fast**. Cite sources within the past 12 months where possible. Note when guidance is in transition.
- The gradation matrix (Q7.4) is the single most useful output. Everything else exists to inform it.
- Q7.11 and Q7.12 (timeline and cost overheads) are where this topic feeds T11 most directly. Get specific numbers, not generalities. Authorization timelines published by GSA, CISA, and FedRAMP PMO are concrete sources.
- For Q7.14 (TTB-specific): much may not be public. Note where speculation begins. Marcus's interview is one of our few primary sources — don't extrapolate beyond it without hedging.
- The "compliant vs. deployable" distinction (Q7.17) is genuinely important. A pure compliance answer that ignores agency-specific deployment friction is incomplete and federal audiences will know.
