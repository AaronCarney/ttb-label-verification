# Research Topics — TTB Label Verification Prototype

**Status:** LIVING DOCUMENT
**Last updated:** 2026-04-28

Items are not in priority order within sections. Each carries a status:
**OPEN** · **IN PROGRESS** · **PARTIALLY RESOLVED** · **RESOLVED** (move to a closed-items section once resolved)

---

## A. Stakeholder & process research

### A-1. Additional stakeholder analysis frameworks worth applying
**Status:** OPEN

Frameworks beyond the Power/Interest grid that earn their keep early in projects like this:

- **Salience model (Mitchell, Agle & Wood, 1997).** Adds *legitimacy* and *urgency* to power. Useful here because Dave has strong legitimacy (28 years) without much formal power — Power/Interest alone misses this.
- **RACI matrix.** Once stakeholders are identified, RACI clarifies who Decides vs. who's Consulted. Sketch a quick RACI for the prototype: Sarah=A, Dave/Jenny=C, Marcus=C (with veto on production), us=R.
- **Empathy maps per persona.** Forces writing down what each stakeholder *says, thinks, does, feels*. Surfaces the unspoken stuff (Dave's "I've seen these come and go" is a feeling shaping demo strategy, not a requirement).
- **Job-to-be-done framing.** Sarah's JTBD isn't "verify labels faster" — it's "free my agents from data-entry verification so they can do judgment work." Reframing requirements against the JTBD often surfaces stretch goals.
- **Pre-mortem.** Imagine the project failed; ask why. Surfaces unstated risks (e.g., "demo crashed on Sarah's iPad," "Dave found three obvious misses in the first batch and lost trust").
- **Stakeholder onion / radius-of-influence.** Concentric rings: core users (Dave, Jenny), sponsors (Sarah), enablers (Marcus, CIO), affected outsiders (industry submitters, FDA on cider/saké edge cases). Helps spot who's being forgotten.

**Action:** Apply at least Salience and a quick RACI before next stakeholder revisit. Consider empathy map for Dave specifically.

### A-2. Cadence and best practices for re-doing stakeholder analysis
**Status:** Captured in Gaps doc (see 05-gaps-and-limitations.md §"Ongoing stakeholder analysis").

### A-3. Realistic agent review-time benchmarks
**Status:** OPEN — need empirical data for batch sizing math.

Sarah said 5–10 minutes per simple application, longer with issues. We need a tighter distribution for the lookahead sizing: median, p90, and how it varies by beverage class and complexity. Possible sources: TTB COLA processing-time public statistics; informal benchmarking in stakeholder interview round 2.

### A-4. Janet (Seattle office) as additional stakeholder
**Status:** OPEN.

Sarah mentioned Janet has been asking about batch upload "for years." Janet is a field-office voice we haven't heard directly. Worth a 15-minute conversation — she likely has the most concrete batch-workflow requirements.

### A-5. Procurement / production-stage stakeholders
**Status:** OPEN.

If this prototype goes to a real procurement, additional stakeholders activate: TTB CIO's office, contracting officers, FedRAMP review, accessibility (Section 508) reviewers, possibly the union (federal agents have one). Mapping these now lets us avoid surprises later.

---

## B. TTB regulatory documents

**Status:** OPEN — required for download and correct utilization to be future-determined.

### B-1. Primary regulatory texts (must read for production)
- **27 CFR Part 4** — Labeling and Advertising of Wine
- **27 CFR Part 5** — Labeling and Advertising of Distilled Spirits
- **27 CFR Part 7** — Labeling and Advertising of Malt Beverages
- **27 CFR Part 16** — Alcoholic Beverage Health Warning Statement (warning text + formatting rules live here)

### B-2. Closely adjacent regulatory texts
- **27 CFR Part 14** — Advertising regulations (consolidated under 2022 modernization, T.D. TTB-176)
- **27 CFR Part 13** — Labeling Proceedings (rejection / appeal process)
- **27 CFR Part 1** — Basic Permit Requirements (bottler/producer identity context)
- **27 CFR Part 9** — American Viticultural Areas (wine appellation claims)

### B-3. Cross-jurisdictional
- **21 CFR Part 101** — FDA labeling (applies to cider <7% ABV and other edge cases)
- **7 CFR Part 205** — National Organic Program (organic claims)
- **26 U.S.C. Chapter 51** — Internal Revenue Code excise tax classifications

### B-4. Operational guidance (TTB practice)
- **TTB Form 5100.31** — current rev 04/2023. Filed via COLAs Online or paper. Form fields publicly documented.
- **Beverage Alcohol Manual (BAM)** — TTB's labeling manual for distilled spirits and malt beverages.
- **TTB Industry Circulars** — operational guidance from TTB to industry.
- **TTB Boot Camp** slide decks (publicly available, used for ALFD training).
- **TTB Rulings and Procedures.**
- **Allowable Revisions list** — changes producers can make to approved labels without re-applying.
- **T.D. TTB-196** (Nov 2024) — most recent labeling amendments worth scanning for currency.
- **Public COLA Registry** — searchable database of approved COLAs back to 1999, with images. Free source of real test labels.

**Action:** Download primary texts (B-1) and TTB Form 5100.31 first. Tag each with relevance notes as we read. Defer B-2/B-3/B-4 until prototype scope is locked.

---

## C. Domain / operational research

### C-1. Application input format for prototype
**Status:** PARTIALLY RESOLVED.

Real submissions go through COLAs Online or paper TTB Form 5100.31. The form fields are publicly documented. The Public COLA Registry exposes structured data and images for past approvals. **Open question:** what specific format does the take-home reviewer expect our prototype to accept — JSON, PDF, mocked struct?

**Action:** Either ask for clarification or document the assumption explicitly in README.

### C-2. Empirical batch sizes and cadence
**Status:** OPEN.

Sarah described "200, 300 label applications at once" from large importers in peak season. Need: distribution of batch sizes, frequency, peak-season definition. Useful for sizing the lookahead queue and stress-testing.

### C-3. Real-world rejection reason taxonomy
**Status:** OPEN.

What categories of rejection do TTB agents actually issue? A structured reason-code vocabulary would be valuable for the rejection-reasoning output. ALFD likely has internal categories. Public sources: rejected-application data from COLAs Online may expose patterns.

### C-4. ABV tolerance values per beverage class
**Status:** OPEN.

We have ±0.3 pp for distilled spirits (T.D. TTB-158). Need exact tolerances for wine and malt to populate the rule set. Likely in 27 CFR Part 4 §4.36 and Part 7 §7.65 areas — confirm.

---

## D. Technical research

### D-1. On-prem inference options for federal deployment
**Status:** OPEN — required by D-004 (production parity).

Federal context restricts cloud inference. Options to evaluate:
- Self-hosted OCR: Tesseract, PaddleOCR, EasyOCR. Quality vs. throughput trade-offs.
- Self-hosted vision-language models. Hardware requirements, FedRAMP / ATO posture.
- On-prem deployment patterns (containerized, air-gapped acceptable).
- Latency budget on agency-grade hardware vs. cloud baseline.

### D-2. OCR robustness for difficult conditions
**Status:** OPEN — feeds the stretch goal.

Jenny called out angles, glare, low light. Research:
- Pre-processing pipelines (deskew, denoise, glare removal) — cost vs. benefit on the 5s SLA.
- When to fail-fast on unreadable images vs. attempt recovery.
- "Needs better photo" disposition as a first-class output.

### D-3. Fuzzy match algorithm choice and threshold
**Status:** OPEN.

Brand-name fuzzy matching needs: case-insensitive, punctuation-insensitive, possessive-aware, transliteration-aware (imports). Candidates: Levenshtein, Jaro-Winkler, RapidFuzz, embedding-based similarity. Need to set thresholds against real failure-mode examples.

### D-4. Versioning and updating the rule set
**Status:** OPEN.

TTB regulations change (T.D. TTB-196 was Nov 2024). The system should accommodate rule updates without code changes. Patterns: rules-as-data (YAML/JSON), feature flags, rule-engine libraries.

---

## How this doc is maintained

- New items go in OPEN with brief context.
- Items move through IN PROGRESS → PARTIALLY RESOLVED → RESOLVED.
- RESOLVED items move to a `closed-items.md` (TBD) so this doc stays focused on what's still open.
- Cross-link to Decisions doc whenever research resolves into a decision.
