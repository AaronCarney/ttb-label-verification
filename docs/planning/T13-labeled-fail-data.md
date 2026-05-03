# T13 — Labeled Fail-Data Sourcing

**Phase:** 4 (User-facing & Eval)
**Status:** EXECUTED — see `docs/research/T13-output.md`
**Prerequisites:** T2 (Public COLA Registry access), T9 (corpus design + datasheet posture)
**Blocks:** Final eval-corpus construction; datasheet "Collection Process" section.

## Synopsis

T9 settled annotation methodology (Krippendorff's α ≥ 0.80, double-pass with adjudication, Gebru datasheet) and assumed-by-default that the negative-case share of the eval corpus would be **synthetically generated** because the Public COLA Registry only publishes **approved** labels (no fail records). That assumption was never tested against alternative sources of labeled fail data.

This topic surveys real-world labeled-negative sources, estimates their yield against the prototype timeline and a hypothetical v1 timeline, and produces an informed sourcing recommendation. The synthetic+retrospective approach may still win on prototype timeline grounds — but it should win as a documented choice, not an unexamined default.

This research is **data-sourcing survey work** — the same kind of curatorial inventory done before any ML eval-corpus build, just applied to labeled COLA-fail records instead of generic image data. Some sources are federal (FOIA, Federal Register, Market Compliance) and some are not (academic corpora, industry/trade publications, litigation records). The federal-ness of a few sources is incidental to the access mechanism, not the topic itself. Live browser-based research is not required; the researcher (or candidate) can execute it from authoritative training knowledge, with spot-verification of any cited URL.

## Required reading

- All five core artifacts
- `T2-output.md` (required) — for what the Public COLA Registry exposes (and confirms the no-bulk-download finding)
- `T9-output.md` (required) — for the corpus shape we're trying to fill (≥250 labels, ≤15% synthetic, datasheet posture)
- `T1-output.md` (helpful) — for the failure-mode taxonomy that a real-fail corpus would need to cover
- Background: federal FOIA framework (5 U.S.C. § 552), TTB organizational structure (ALFD, Market Compliance Office, Trade Investigations Division), Federal Register publishing conventions, PACER/court-opinion access patterns

## Output expected

A `T13-output.md` covering:

1. **Source inventory.** Every plausible source of labeled fail data, with type (FOIA, public bulletin, court record, etc.) and known access mechanism.
2. **Per-source yield estimate.** For each source: realistic count of recoverable labeled-fail records, image-vs-text-only mix, processing time, fee/cost, redaction risk, legal/ATO exposure.
3. **Decision matrix.** Sources × {prototype-timeline (4–6 wk), v1-timeline (6–12 mo)} with a yield-vs-cost recommendation per cell.
4. **Recommended sourcing plan.** Concrete corpus-construction strategy for MVP and for v1, with an explicit synthetic share justified against the survey rather than assumed.
5. **Datasheet-update text.** Drop-in language for `eval/datasheet.md` "Collection Process" section that records the survey and the chosen path, satisfying Gebru et al. transparency.

## In-topic questions

### Questions that can be researched now

#### Q13.1 — TTB FOIA scope and yield
*Federal-process question; primary sources are 5 U.S.C. § 552, TTB FOIA Handbook, and TTB published FOIA logs.*

- What COLA-related records are FOIA-eligible? Rejected applications, reviewer rejection notes, revision-cycle artifacts, internal correspondence on borderline calls?
- TTB's published processing-time ranges (simple / complex / expedited tracks) — confirm the working assumption that bulk requests fall in the 6–12 week window.
- Fee structure: search hours, duplication, review. At what record count does the fee waiver bar trigger?
- Common redactions on COLA records: applicant PII, business-confidential trade information (b)(4), pre-decisional reviewer deliberation (b)(5).
- Historical FOIA releases that touched COLA review: search MuckRock, the FOIA.gov archive, and TTB's FOIA Reading Room. Have any released label-rejection bundles?
- Reuse path: does FOIA-released material carry a license that permits eval-corpus inclusion?

Output: realistic record count recoverable in 6–12 weeks; flagged risks; sample FOIA request draft.

#### Q13.2 — TTB Market Compliance Office (post-market sweeps)
*Public-source question; primary sources are TTB.gov enforcement pages and TTB Annual Reports.*

The Market Compliance Office samples products off-shelf and checks labels against the approved COLA. Mismatches and post-approval label drift are documented.

- What does Market Compliance publish, and at what cadence? Annual report aggregates? Per-action bulletins?
- Are individual finding artifacts (label scans, mismatch descriptions) public, or are only aggregate counts published?
- Is the Trade Investigations Division a separate but parallel source for misbranding cases?
- Estimate annual count of documented post-market label findings; what share are surfaced with image artifacts?

Output: yield estimate, access path, image-availability assessment.

#### Q13.3 — Federal Register adverse-action notices
*Public-source question; primary source is federalregister.gov (open API).*

TTB occasionally publishes adverse actions, permit suspensions, and consent orders in the Federal Register.

- Frequency of TTB adverse-action notices in the FR; query strategy via the FR API.
- Typical content: are these text-only descriptions of misbranding, or do filings include the rejected artwork?
- Are settlement / consent-order references useful for extracting concrete failure modes even without artwork?

Output: API query, expected hit rate, image-yield assessment (likely low).

#### Q13.4 — TTB Industry Circulars and "common rejection reasons" guidance
*Public-source question; primary source is TTB.gov compliance pages.*

TTB publishes Industry Circulars and a "common reasons COLA applications are rejected" page.

- Inventory of the rejection-reason guidance currently published.
- Map each published reason to the rule-pack failure modes (T1-output) — useful as a cross-check on rule-pack completeness even though it doesn't yield images.
- Do Industry Circulars include before/after label imagery?

Output: rule-pack coverage cross-check; image-yield assessment (low).

#### Q13.5 — State ABC commission rejections
*Federal-preemption question; primary sources are state ABC commission websites and the FAA Act preemption doctrine.*

The FAA Act federally preempts most label-content review; states regulate distribution and permitting.

- Which states have meaningful additional label-content review beyond federal preemption? Likely candidates: California (Prop 65), New York (type-size requirements), Maryland (specific commodity rules).
- Do any state commissions publish rejected-label decisions with imagery?
- Yield estimate per state; preemption-doctrine sanity check.

Output: per-state yield estimate (likely very low overall).

#### Q13.6 — Litigation records (PACER, court opinions)
*Public-record question; primary sources are PACER, CourtListener, Justia.*

Lanham Act false-advertising suits and state UDAP class actions sometimes attach the disputed label as exhibits.

- Search strategy: terms in case captions / docket entries (e.g., "false advertising" + "alcohol", "mislabeled" + "spirits", named brands in known disputes — Tito's Handmade Vodka, Kona Brewing geographic claims, Maker's Mark wax-cap dispute).
- PACER fee structure for exhibit retrieval; CourtListener as a free fallback.
- Yield estimate: small N, but real labels with documented dispute and reviewer/court reasoning.

Output: search strategy, expected count, fee estimate.

#### Q13.7 — Adjacent-domain academic corpora
*Academic literature question; primary sources are ICDAR proceedings, IIT-CDIP archive, public OCR benchmarks.*

General document/OCR corpora (FUNSD, IIT-CDIP, RVL-CDIP, DocLayNet) are not TTB-specific but exercise OCR robustness.

- Suitability for the OCR-quality slice of the eval corpus (BRISQUE/NIQE gates, low-res, glare, rotation).
- Licensing for redistributable inclusion in our eval bundle.
- Map academic-corpus failure modes to our T4 image-quality taxonomy.

Output: which corpora are usable for the OCR-robustness slice (not the rule-eval slice).

#### Q13.8 — Industry / trade-association data
*Industry-relationship question; primary sources are WSWA, DISCUS, Beer Institute, Wine Institute publications.*

Members of trade associations have internal compliance records that could include rejected labels.

- Which associations publish compliance casework or compliance-trends data?
- Are there academic partnerships or shared-corpus initiatives that have crossed industry-NDA lines?
- Realistic outreach path for prototype scope (probably none); outreach path for v1 scope.

Output: outreach feasibility per association; realistic v1 timeline.

#### Q13.9 — Synthetic generation as informed choice
*Synthesis question; depends on Q13.1–Q13.8 outputs.*

Given the surveyed-source yield, is synthetic+retrospective still the right MVP choice?

- Restate the synthetic share (≤15%, C2PA-tagged) as a *chosen* parameter, not a default.
- If the survey reveals a viable real-fail source within prototype timeline, propose a revised MVP corpus mix.
- If it does not, document the timeline-driven rationale with a v1 sourcing roadmap.

Output: defended synthetic share for MVP; proposed v1 mix.

#### Q13.10 — Decision matrix and recommendation
*Synthesis question.*

Build a sources × timelines matrix:

| Source | Prototype (4–6 wk) | v1 (6–12 mo) |
|---|---|---|
| TTB FOIA | yield, cost, recommendation | yield, cost, recommendation |
| Market Compliance | … | … |
| Federal Register | … | … |
| Industry Circulars | … | … |
| State ABC | … | … |
| PACER / litigation | … | … |
| Academic OCR | … | … |
| Industry / trade | … | … |
| Synthetic generation | … | … |

Output: matrix populated with realistic estimates; recommended MVP and v1 sourcing plans.

### Questions that need prerequisites

*(None — Q13.1–Q13.10 are independent of any T-output not already produced.)*

## Cross-topic synthesis questions

- **X-7 (T9 + T13):** Final corpus-construction plan. Folds T13's sourcing recommendation into T9's annotation methodology. Owner: synthesis stage S6/S7 follow-up if T13 lands after BRD/PRD; otherwise direct revision of T9-output.
- **X-8 (T7 + T13):** Federal-context constraints on data sourcing. Confirms FOIA-released material carries no ATO blocker for prototype-tier inclusion; flags any redaction-driven content that would need re-anonymization before eval inclusion.
- **X-9 (T11 + T13):** Cost-benefit impact. If FOIA delivers a real-fail corpus at v1, the calibration-curve metric (PRD §9.2) becomes empirically defensible rather than internally circular; this strengthens the BO-2 accuracy claim and the BCA case.

## Notes for the researcher

- **No browser-research mode required.** This topic is built on stable federal-process and public-records knowledge. Cite primary sources (5 U.S.C. § 552, TTB FOIA Handbook, federalregister.gov, etc.) and spot-verify any URL. Don't invent recent press releases or specific FOIA logs without verification.
- **Honest yield estimates beat optimistic ones.** A "small but real" estimate is more useful than an aspirational one. Most non-FOIA paths will yield text descriptions, not images — say so.
- **Don't over-claim FOIA outcomes.** A FOIA submission can be partially denied, redacted to uselessness, or moved to a complex track that exceeds the prototype timeline. The recommendation should account for tail risk.
- **The output's most important deliverable is Q13.9.** The whole topic exists to convert "synthetic-by-default" into "synthetic-by-defended-choice." Without that, the work is filing.
- **Scope discipline.** This is not a re-do of T9. It's a sourcing survey that ends with a corpus-mix recommendation and a datasheet update. Don't re-litigate annotation methodology or metric framework.
- **Ethics check.** Any path that involves real applicants needs a redaction strategy (PII) and a use-rights review (FOIA-released material is generally usable, but verify per-record). Document it once in the datasheet, don't re-derive per source.
