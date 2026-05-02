# T1 — TTB Regulatory Framework Deep Dive

**Phase:** 1 (Foundation)
**Status:** READY TO RESEARCH
**Prerequisites:** None
**Blocks:** T3, T4, T5, T6, T7, T8, T9 (everything except T10)

## Synopsis

We need a structured, encodable rule set covering the TTB labeling regulations our prototype will validate. The take-home brief calls out brand name, class/type, alcohol content, net contents, bottler/producer name and address, country of origin, and the government health warning statement as the common mandatory elements, but states that exact requirements vary by beverage type. Our hard-tier requirements include exact-match validation of the government warning per 27 CFR § 16.21 with formatting rules from § 16.22, and tolerance-aware ABV checking. Stretch goals include beverage-class-specific rules (vintage, age statements, appellations) and font-size compliance.

The output of this research feeds directly into the validation engine architecture (T3) and indirectly into nearly everything else.

## Required reading

Beyond the standard artifact set:
- 27 CFR Part 4, 5, 7, 16 (primary)
- 27 CFR Part 14 (advertising — only if relevant to our scope)
- TTB Form 5100.31 (current rev 04/2023)
- T.D. TTB-196 (Nov 2024) for currency
- TTB Beverage Alcohol Manual (BAM)
- 04-research-topics.md §B for the full document inventory

## Output expected

A structured rule set document (`T1-output.md`) organized as:

1. **Per-beverage-class field manifest.** For wine, distilled spirits, malt beverages: full list of mandatory, conditional-mandatory, and prohibited fields, each with regulatory citation.
2. **Per-field validation rules.** For each field: match policy (exact / tolerance / fuzzy / format), expected values or value ranges, formatting requirements, and citation.
3. **Government warning specification.** Exact text, formatting rules, placement rules, font-size table by container size.
4. **Rejection categories.** TTB's working taxonomy of rejection reasons, mapped to regulatory citations where possible.

## In-topic questions

### Q1.1 — Mandatory field manifest per beverage class
For each beverage class (wine, distilled spirits, malt beverages), list every mandatory label field. For each field provide: field name, regulatory citation (CFR section), and where it must appear (brand label only, any panel, etc.).

### Q1.2 — Conditional mandatory fields
*Gated by Q1.1.* Within each beverage class, list fields that become mandatory only when certain product characteristics are present (e.g., country of origin only for imports; vintage only when claimed; appellation rules only when an appellation is stated). For each: the trigger condition and the resulting requirement.

### Q1.3 — Prohibited label elements
What does each CFR Part forbid on labels? Misleading health claims, certain comparative claims, prohibited terms, etc. Provide citation for each.

### Q1.4 — Per-field validation rule specification
*Gated by Q1.1, Q1.2.* For each field identified, what is the matching/validation rule? Provide:
- Match policy (exact / fuzzy / tolerance / format-only)
- Tolerance values where applicable (ABV by class is the key one — confirm wine and malt tolerances; we already have ±0.3 pp for spirits from T.D. TTB-158)
- Acceptable variants (case, abbreviation, equivalent unit forms)

### Q1.5 — Government warning specification
Provide the complete specification for the warning:
- Exact text (verify against current eCFR)
- Formatting rules (caps + bold for "GOVERNMENT WARNING," remainder not bold, continuous statement, contrasting background)
- Font-size minimums by container size (1mm / 2mm / 3mm thresholds)
- Maximum characters per inch table
- Placement rules (front / back / side acceptable)
- Anything else from § 16.22 we should encode

### Q1.6 — Beverage-class-specific designation rules
*Gated by Q1.1.* For the stretch goal of class-specific validation:
- Spirits: 12 standards of identity (whisky, gin, vodka, rum, brandy, etc.). What are they, and what triggers each?
- Wine: varietal, appellation, estate-bottled, vintage rules
- Malt: type designations, alcohol-content disclosure rules

### Q1.7 — Recent regulatory changes
What has changed in TTB labeling regulations in the past 3 years (T.D. TTB-158 2020, T.D. TTB-176 2022, T.D. TTB-196 2024, anything more recent)? Which changes affect any rules we'd encode?

### Q1.8 — Rejection vs. revision taxonomy
How does TTB internally categorize rejected vs. needs-revision applications? Is there a published rejection-reason taxonomy? Sources: 27 CFR Part 13 (Labeling Proceedings), TTB Industry Circulars, ALFD public guidance.

### Q1.9 — Allowable revisions
TTB publishes an "Allowable Revisions" list — changes producers can make to approved labels without re-applying. What's on that list, and does it imply anything about which fields are considered material vs. cosmetic for validation purposes?

### Q1.10 — Cross-jurisdictional edge cases
Where does TTB jurisdiction end and FDA jurisdiction begin? Specifically: cider <7% ABV (FDA), wine <7% or >24% ABV (FDA / spirits respectively), saké classification. Do we need to handle any of these in the validator, or are they out-of-scope inputs?

## Cross-topic synthesis questions
*(These are flagged in the master plan; do not run them in this conversation.)*

- **X-4 (T1 + T3):** Which rules can be expressed as pure data (rule-engine YAML/JSON) vs. which require code logic? Hold for after T3.
- **X-5 (T1 + T2 + T9):** What test corpus exercises every rule across every class with realistic failure modes? Hold for after T9.

## Notes for the researcher

- Cite CFR sections precisely. Vague citations are worse than no citation.
- Where TTB guidance documents (BAM, Industry Circulars) elaborate on regulations, distinguish between binding regulation and operational guidance.
- Where the regulation is ambiguous, say so explicitly and note where TTB's working interpretation can be inferred from public materials.
- This output will be encoded into a rule set. Format answers with that downstream use in mind — structured, parseable, citation-rich.
