# T13-output.md — Labeled Fail-Data Sourcing Survey

> **Status: PRODUCTION-APP REFERENCE.** Not used by the prototype. Captures sources we surveyed for a future production-app eval corpus (post-prototype, v1+). Borderline-confidence imagery — what the prototype actually needs — is handled in PRD §9 / §10.2, not here.

> **Source posture.** This output is produced from authoritative training knowledge of FOIA mechanics, TTB organizational structure, federal-records access patterns, PACER/CourtListener, and academic OCR corpora. It is **not** a live web survey; specific URLs, recent FOIA logs, and current Market Compliance bulletins are flagged for spot-verification. Honest yield estimates beat optimistic ones — every count below is a **realistic floor**, not a pitch.

## TL;DR

- **No bulk public corpus of labeled fail-images of TTB COLAs exists.** TTB's Public COLA Registry contains only approved labels; rejection records are not published.
- **TTB FOIA** (5 U.S.C. § 552) is the only path to a real, large labeled-fail corpus. Processing window: 6–12 weeks for a complex-track request. Production-app v1 work.
- **PACER / CourtListener litigation records** yield a small but real labeled-fail subset (~10–40 labels) for `BRAND.NAME.MISMATCH` and geographic-claim rules, drawn from Lanham Act §43(a) and state UDAP cases. Hand-curatable.
- **Federal Register, Market Compliance, Industry Circulars, State ABC** — text descriptions of violations, no images.
- **Academic OCR/document corpora** (FUNSD, IIT-CDIP, RVL-CDIP, DocLayNet) — useful for OCR robustness only, not rule evaluation.
- **Industry/trade associations** — closed data, NDA-bound.
- **Synthetic generation** with C2PA tagging — sole option for filling the prototype's negative-case slice.

---

## 1. Per-source survey

### 1.1 TTB FOIA (5 U.S.C. § 552; Treasury implementing regs at 31 CFR Part 1)

**Status:** Real path. Slow.

**Mechanism.** TTB is a Treasury bureau; FOIA requests go through TTB's FOIA Officer (a Public Affairs / FOIA Liaison role within TTB Headquarters in Washington, DC). TTB publishes a FOIA Reading Room and an annual FOIA report under the FOIA Improvement Act of 2016. Requests can be submitted by mail, fax, or electronically through the TTB website (verify current submission portal — Treasury bureaus have migrated to FOIAonline / National FOIA Portal in stages; spot-verify at submission time).

**What's potentially available.**
- Redacted COLA application packets where the application was rejected.
- Reviewer rejection letters (the formal "needs correction" or "rejected" notification to the applicant) with cited CFR sections.
- Appeal correspondence on contested rejections.
- Internal guidance documents on borderline-call adjudication (rare; usually pre-decisional and (b)(5)-redacted).

**Likely redactions.**
- (b)(4) trade secrets / confidential commercial information — likely applied to formula references, supplier identities, batch composition.
- (b)(6) and (b)(7)(C) personal privacy — applicant signatories, reviewer names.
- (b)(5) deliberative process — internal back-and-forth on borderline calls, often redacted to uselessness.

**Processing time.** Statutory 20 business days for simple requests, but complex-track multi-record requests routinely take **6–12 weeks** (TTB's own published bands; verify current annual FOIA report). Bulk requests for "100 representative rejected COLAs" land squarely in complex track.

**Fees.** Commercial-use requesters pay search + review + duplication; news media, educational, and non-commercial scientific requesters pay duplication only after the first 100 pages. A take-home or research project can plausibly claim non-commercial scientific use, but expect TTB to assess fee status (and contest aggressive categorizations).

**Reuse rights.** FOIA-released material is generally redistributable; verify per-record because TTB occasionally marks (b)(4)-redacted releases with use restrictions.

**Realistic yield.**
- **Prototype timeline (4–6 wk):** **0 records.** Cannot complete a FOIA cycle.
- **v1 timeline (6–12 mo):** **50–200 redacted COLA application packets** with label imagery, sufficient to materially shift the corpus mix.

**Recommendation.** **Skip for MVP. File early in v1.** The right move is to draft the FOIA request *now* (during prototype work) so it can be submitted on day 1 of the v1 effort.

### 1.2 TTB Market Compliance Office (post-market sweeps)

**Status:** Public-aggregate-only. Image yield near zero.

**Mechanism.** TTB's Trade Investigations Division (TID) and Tax Audit Division conduct post-market compliance work, including label reviews against approved COLAs. Findings feed enforcement actions (warning letters, OICs, permit suspensions). The TTB Annual Report aggregates statistics; per-action artifacts are typically not published.

**What's available.**
- TTB Annual Reports — aggregate counts of enforcement actions, no per-case imagery.
- Public press releases on major actions — text descriptions, occasional photo of the seized product but rarely the rejected label artifact in a usable form.
- TTB.gov compliance pages summarize common findings as guidance, not as a labeled corpus.

**Realistic yield.** **Near zero image artifacts** for either timeline. Useful as **failure-mode design input** (cross-checks rule-pack coverage against TTB's own observed-violation patterns) but not as eval images.

**Recommendation.** **Skip for corpus inclusion.** Use TTB Annual Report enforcement statistics in the BRD's BO-2 accuracy framing if helpful, but don't expect images.

### 1.3 Federal Register adverse-action notices

**Status:** Open-API access, image yield near zero.

**Mechanism.** federalregister.gov has an open API. Query for TTB-published consent orders, NOPDs (Notice of Proposed Disqualification), and permit-suspension notices.

**Content.** Federal Register filings are **text descriptions** — they cite the violation, the CFR section, and the disposition. They essentially never include label imagery as exhibits; the imagery (if any) lives in the underlying TTB administrative file, accessible only via FOIA (§1.1).

**Realistic yield.** **0 image artifacts**, both timelines. Useful as a **failure-mode taxonomy cross-check**: enumerate what TTB has actually adverse-actioned over the past N years to validate that the rule pack covers what TTB cares about.

**Recommendation.** **Skip for corpus inclusion. Use as a rule-pack coverage QA pass** — pull TTB's last 3 years of FR adverse-action notices, classify the cited violations against the rule-pack's reason-code taxonomy, and flag any gaps.

### 1.4 TTB Industry Circulars and "common rejection reasons" guidance

**Status:** Pattern guidance, not images.

**Mechanism.** TTB publishes Industry Circulars and TTB Bulletins on compliance topics. TTB.gov compliance guidance includes pages on common COLA rejection reasons (verify exact title — e.g., "Reasons for Rejection" or "Avoid Common Errors" — at execution time).

**Content.** Verbal/textual guidance, occasionally with stylized example imagery showing format requirements (e.g., what a compliant Government Warning *should* look like). **Not a labeled fail corpus.**

**Realistic yield.** **0 image artifacts of real rejected labels.** Useful for rule-pack design and reviewer-facing reasoning text (PRD FR-301), not eval images.

**Recommendation.** **Skip for corpus inclusion. Use for rule-pack design QA** — cross-check that every published rejection reason maps to a rule in our pack.

### 1.5 State ABC commission rejections

**Status:** Federal preemption limits state label review.

**Mechanism.** The Federal Alcohol Administration Act (FAA Act) federally preempts most label-content review for wine (≥7% ABV), distilled spirits, and malt beverages. State ABC commissions retain authority over distribution licensing, age verification, container labeling for state-specific concerns (e.g., California Prop 65 carcinogen warnings, New York type-size requirements for certain claims), and post-market enforcement.

**Content.** Per-decision rejection records with imagery are not generally published by state commissions. Some states publish enforcement bulletins; these are typically text-only and cover distribution/permit issues, not label content.

**Realistic yield.** **Very low** for both timelines. CA Prop 65 enforcement is the only state-side angle that touches label content meaningfully, and it's a separate warning regime from the federal Government Warning we're verifying.

**Recommendation.** **Skip for corpus inclusion.**

### 1.6 Litigation records (PACER, CourtListener)

**Status:** Small but real. Viable for the prototype.

**Mechanism.** Lanham Act §43(a) false-advertising suits (federal court) and state UDAP class actions (often removed to federal court) frequently attach the disputed label as an exhibit. PACER charges per page (~$0.10/page, capped at $3.00/document); CourtListener (a free aggregator from the Free Law Project) hosts a substantial subset of these filings without fees.

**Content.** Exhibits are real labels. The complaint and any rulings document the alleged misrepresentation in plain language — useful as ground-truth labels for "what's wrong" in the filed dispute. Not all cases yield image-quality exhibits (some are described in text only), but a meaningful subset do.

**Notable case lines (illustrative; verify each at execution time):**
- "Handmade" / "Crafted" claims on industrial-scale spirits — Tito's Handmade Vodka was named in multiple class actions in the mid-2010s; outcomes varied by jurisdiction.
- Geographic-origin claims — Kona Brewing (Hawaii claim on mainland-brewed beer), Templeton Rye (Iowa claim with Indiana sourcing), Maker's 46 (geographic and process claims).
- Aged-statement claims — Templeton Rye and other "small batch" / age-related litigation.
- Anheuser-Busch beer-labeling marketing/sales practices litigation.
- Malibu, Bacardi, and other geographic-association claims.

These are all primarily **brand and geographic-origin** disputes — they exercise the `BRAND.NAME.MISMATCH` rule and geographic-claim rules, not the warning-statement or ABV-tolerance rules.

**Realistic yield.**
- **Prototype timeline (4–6 wk):** **10–40 labels**, hand-curated, with cited dispute reasoning. Concentrated in brand-claim and geographic-origin failure modes.
- **v1 timeline (6–12 mo):** **50–100 labels**, expanded to a fuller class-action history and more recent filings.

**Cost.** PACER fees for a 50-case sweep: ~$50–150 if exhibits are dense; ~$0 if CourtListener carries them.

**Reuse rights.** Court-filed exhibits are public records; redistribution is generally permitted with attribution. Spot-verify any specific case's filing-rules order if it exists.

**Recommendation.** **Include in MVP corpus.** Hand-curate ~10 cases for the prototype slice, expand in v1.

### 1.7 Adjacent-domain academic corpora

**Status:** Useful for OCR robustness, not rule evaluation.

**Inventory.**
- **FUNSD** (Form Understanding in Noisy Scanned Documents) — ~200 forms, layout + entity annotations.
- **IIT-CDIP / RVL-CDIP** — 400K+ scanned business documents, classification labels.
- **DocLayNet** — 80K pages of document layout annotations across multiple formats.
- **DocVQA** — document visual question answering.
- **PubLayNet** — academic publication layout (~360K pages).
- **TableBank** — table detection and structure recognition.
- **ICDAR Robust Reading Challenges** — text in natural scenes, focused / blurred / glare scenarios.

**Use cases.**
- ICDAR robust-reading datasets exercise the **BRISQUE/NIQE legibility-gate** path (FR-603 needs-better-photo): low-res, glare, rotation, perspective distortion. **Useful for the OCR-robustness slice** of the eval.
- Form/document corpora are out-of-domain (alcohol labels are not forms or business docs) and don't help with rule evaluation.

**Licensing.** Most are research-use only; most permit redistribution within research bundles. Spot-verify each corpus's license at inclusion time.

**Realistic yield.** **0 alcohol-label artifacts.** ~50–200 image-quality stress cases for the BRISQUE/NIQE path.

**Recommendation.** **Use only for the OCR-robustness slice** (a small, separate slice of the eval corpus that exercises FR-603 / WARNING.LEGIBILITY.* reason codes). Do not use for any rule that requires interpreting label content.

### 1.8 Industry / trade-association data

**Status:** Closed. Not viable.

**Mechanism.** WSWA (Wholesalers), DISCUS (Distilled Spirits Council), Beer Institute, Wine Institute aggregate compliance data from members; sharing is industry-NDA-bound.

**Realistic yield.** **0 records** for either timeline absent a partnership negotiation that exceeds the project's scope.

**Recommendation.** **Skip.** If a v1 program builds a multi-stakeholder compliance partnership, revisit then.

### 1.9 Synthetic generation (DALL-E 3 / GPT-Image / Midjourney / Stable Diffusion + label-design tools)

**Status:** Primary fill for negatives. Defended.

**Mechanism.** T9-output already established this path. OpenAI's DALL-E 3 and the GPT-Image family embed C2PA Content Credentials by default since Feb 2024 (per T9 finding §4); this gives us audit-grade provenance on every synthetic asset.

**Strengths.**
- Full controllability — we know exactly what failure mode we built each fixture to test.
- Cost is low (compute time + prompt engineering).
- C2PA tagging satisfies the datasheet's transparency requirement.

**Weaknesses.**
- Verisimilitude is improving but imperfect — synthetic labels can have subtle artifacts (font irregularities, layout artifacts) that don't appear in real labels.
- Coverage is bounded by what we think to generate; we won't catch failure modes we didn't anticipate.

**Realistic yield.** Bounded only by compute time and prompt-engineering effort.

**Recommendation.** **Continue as primary negative-case fill** for the production-app eval corpus until FOIA-sourced real-fail data is available.

---

## 2. Decision matrix

| Source | MVP (4–6 wk) | v1 (6–12 mo) | Image yield (MVP) | Image yield (v1) |
|---|---|---|---|---|
| TTB FOIA | Skip | **File early** | 0 | 50–200 |
| Market Compliance | Skip (no images) | Crosscheck use | 0 | 0 |
| Federal Register | Skip (no images) | Crosscheck use | 0 | 0 |
| TTB Industry Circulars | Crosscheck rule pack | Same | 0 | 0 |
| State ABC | Skip | Skip | 0 | 0 |
| **PACER / CourtListener** | **Include** | **Expand** | **10–40** | **50–100** |
| Academic OCR (ICDAR etc.) | Use for OCR-robustness slice only | Same | ~50–200 (legibility-gate only) | Same |
| Industry / trade | Skip | Maybe partner | 0 | 0 |
| **Synthetic generation** | **Primary negative fill, ~12%** | Reduce share as FOIA lands | **~30** | **~30** (proportionally smaller) |
| **Public COLA Registry (positives)** | **Primary positive source** | Same | **~210** | **~600** |

---

## 3. Caveats

- **No live verification in this output.** Specific URLs (federalregister.gov API endpoints, CourtListener case URLs, TTB FOIA submission portal) and specific recent statistics (current Annual Report enforcement counts, current FOIA processing times) should be spot-verified at execution time. The framework, mechanisms, and legal authorities cited are stable; the surface details drift.
- **PACER yield is the soft number.** "10–40 labels" depends heavily on which case lines a curator focuses on and whether exhibits attached to specific filings carry usable image quality. The number could be as low as 5 or as high as 60. The right move is to budget the curation effort, not the count.
- **FOIA yield assumes a well-drafted request.** A poorly scoped FOIA can be rejected for vagueness or denied as overbroad. The request draft is itself a deliverable that should be peer-reviewed before submission.
- **Reuse rights on hand-curated retail photography (v1 slice) are not free.** A v1 datasheet entry needs an explicit use-rights determination per source. Default conservative posture: cite product photography as fair-use research/review; document reasoning.
- **The Lanham Act / UDAP cases skew toward consumer-deception framings** (handmade, geographic origin, age statements) and away from technical compliance failures (warning formatting, ABV tolerance numerics). PACER negatives won't help with most of the rule pack — they help with the brand and geographic rules specifically.

