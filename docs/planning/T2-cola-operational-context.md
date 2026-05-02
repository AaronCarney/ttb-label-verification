# T2 — COLA System & Operational Context

**Phase:** 1 (Foundation)
**Status:** READY TO RESEARCH
**Prerequisites:** None
**Blocks:** T4, T6, T7, T8, T9 (and feeds T3 indirectly)

## Synopsis

We need to understand the real-world operational context our prototype is being designed against: how COLA applications are actually submitted, what data is captured in TTB Form 5100.31, what the agent workflow looks like in practice, what existing systems we'd integrate with (eventually), and what real-world distributions of batch sizes and review times look like. The take-home brief gives us anecdotal data from Sarah's interview (5–10 minutes per simple application, batches of 200–300 from large importers in peak season). We need to verify, expand, and quantify this where possible from public sources.

This research feeds the input handler design (T3 indirectly), batch architecture (T6), federal deployment design (T7), UX (T8), and test data sourcing (T9).

## Required reading

- TTB Form 5100.31 (current rev 04/2023) — both the form itself and the instructions
- COLAs Online public documentation: https://www.ttbonline.gov/colasonline/
- Public COLA Registry: https://www.ttbonline.gov/colasonline/publicSearchColasAdvancedProcess.do
- TTB COLA processing-time statistics page (if published)
- 27 CFR Part 13 (Labeling Proceedings) for rejection/appeal workflow

## Output expected

A `T2-output.md` covering:

1. **Form 5100.31 field schema.** Every field on the form, its data type, whether it's required, and how it relates to label fields we'd validate.
2. **Submission paths.** How applications enter the system (online vs. paper), what formats they arrive in, what metadata is captured.
3. **Public COLA Registry capabilities.** What's queryable, what data is exposed, how to programmatically pull labels for test data.
4. **Agent workflow reality check.** What we can confirm or refine from public sources about how agents actually process applications.
5. **Operational distributions.** Batch sizes, review times, processing-time statistics, peak-season patterns, rejection rates — whatever's publicly available.

## In-topic questions

### Q2.1 — Form 5100.31 field schema
List every field on the current TTB Form 5100.31. For each: field number/name, data type (text, numeric, enum, etc.), required vs. optional, and which label-side field it corresponds to (if any). The form has at least 18 numbered items in current revision; produce a complete inventory.

### Q2.2 — Submission path inventory
*Gated by Q2.1.* What submission paths exist? What format is the data in for each path?
- COLAs Online (electronic submission)
- Paper Form 5100.31
- Are there APIs (public or private) that expose application data?
- What attachments accompany the form (label artwork formats, photographs, etc.)?

### Q2.3 — Label artwork submission requirements
What does TTB require for the label artwork itself? File formats accepted, resolution requirements, color requirements, how etched/embossed/painted-on labels are handled. This shapes what our prototype's input image handling needs to support.

### Q2.4 — Public COLA Registry capabilities
What's in the Public COLA Registry?
- Search interface capabilities
- What data fields are exposed per record
- Whether label images are downloadable
- Date range coverage (we know images are available from 1999+)
- Programmatic access (any API or scraping considerations)

This matters because the registry is our best source of real test labels.

### Q2.5 — Rejected applications: are they public?
Can we see rejected applications and their rejection reasons publicly? If not, are aggregate rejection statistics published? This feeds rejection-reason taxonomy (T1 Q1.8) and test data (T9).

### Q2.6 — Agent workflow detail
What can we learn from public sources about how ALFD agents actually process applications? Sources to check:
- ALFD's published process documentation
- TTB's own modernization rules and Federal Register notices (T.D. TTB-176 discusses workflow)
- Industry-side guidance on how to anticipate ALFD review
- TTB Boot Camp materials (publicly available training decks)

The brief gave us Sarah's anecdotal version. We want to triangulate.

### Q2.7 — Operational metrics
*Gated by Q2.4 and Q2.6.* What public statistics exist on:
- Average processing time per application (currently and historically)
- Application volume per year (we have ~150–200K from various sources; verify)
- Distribution of submission sources (importers vs. domestic; small producers vs. large)
- Peak-season patterns (are batch surges seasonal, regulatory-deadline-driven, or both?)
- Rejection rates (overall and by class)

### Q2.8 — Existing tooling and prior modernization attempts
What's TTB already deployed or piloted in the labeling space? Any prior AI/automation pilots beyond the one Marcus mentioned? Any vendor RFPs or contracts that hint at what TTB has been pursuing?

### Q2.9 — Adjacent stakeholder identification
*Gated by Q2.6.* From public org-chart and process documentation, who else touches a COLA application beyond ALFD agents? Examples of likely candidates:
- Regulations & Rulings Division (rule interpretation)
- Trade Investigations Division (enforcement)
- Field offices (Sarah mentioned Janet in Seattle)
- Office of Chief Counsel (legal review of contested cases)
- Scientific Services / Nonbeverage Products Lab (formula evaluation)

This feeds future stakeholder analysis (T10) and potentially expands our user/consumer model.

### Q2.10 — Application input format for our prototype
*Open take-home question, partial answer expected.* Given what's documented about Form 5100.31 and COLAs Online, what's the most defensible assumption about what our prototype should accept as application data input? Recommend a format (JSON schema mirroring 5100.31 fields, PDF parse, etc.) with rationale.

## Cross-topic synthesis questions
*(Flagged for later; do not run here.)*

- **X-5 (T1 + T2 + T9):** Test corpus design. Hold until T9.
- **(T2 + T6):** Batch sizing math given measured review times. Hold until T6.

## Notes for the researcher

- Distinguish "what the regulation says" from "what TTB actually does in practice." Both matter; conflating them leads to false certainty.
- For the Public COLA Registry: actually test the search interface and document what works, not just what the docs claim.
- Quantitative answers (Q2.7) are best-effort. If a number isn't published, say so explicitly rather than estimate without basis.
- For Q2.10, rank the candidate input formats by defensibility and explain trade-offs. The take-home reviewer will probably accept any reasonable choice; the goal is to make the choice deliberately.
