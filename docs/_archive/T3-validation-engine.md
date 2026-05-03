# T3 — Validation / Rule Engine Architecture

**Phase:** 2 (Core Architecture)
**Status:** PARTIAL — architectural questions can be researched in parallel with T1, but rule-set–specific questions are gated on T1 output
**Prerequisites:** T1 (for full depth); generic architecture questions can run earlier
**Blocks:** T5, T6, T7

## Synopsis

The validation/rule engine is the determinism core of our system. Per decision D-002, AI orchestrates but does not decide; the rule engine does the actual evaluation against TTB regulations. Per D-005, each field has its own match policy (exact, fuzzy, tolerance, format). Per D-007, every fail or needs-review carries reasoning with rule citation.

We need to research how to build this engine to be: (a) fast enough for the 5s SLA, (b) auditable, (c) maintainable as TTB regulations change, and (d) honest about its uncertainty. This is the most consequential architecture topic because nearly every other component sits on top of it.

## Required reading

- All five core artifacts (00 through 05)
- `T1-output.md` once available (the rule set itself)
- Background reading on rule engines and decision tables: Drools, Cerberus, Pydantic validation, JSON Schema, ANTLR for DSLs

## Output expected

A `T3-output.md` covering:

1. **Rule representation choice and justification.**
2. **Validator interface specification.** What every field validator looks like, what it returns.
3. **Confidence-scoring methodology.** How a validator expresses uncertainty.
4. **Rejection-reason data model.** Structure of the reasoning attached to negative dispositions.
5. **Versioning and update strategy** for the rule set.
6. **Performance budget** within the 5s SLA.

## In-topic questions

### Q3.1 — Rule representation patterns
What are the architectural options for representing a regulatory rule set in code? Compare:
- Hard-coded validators (functions per field)
- Rules-as-data (YAML/JSON consumed by a generic engine)
- Decision tables (DMN-style)
- Domain-specific language (custom DSL)
- Hybrid (declarative for simple rules, code for complex)

For each, evaluate: maintainability, auditability, performance, ability to handle TTB-style nuance (tolerance, fuzzy, format checks).

### Q3.2 — Validator interface specification
*Gated by Q3.1.* What does a single validator look like? Specifically, design:
- Input contract (field value, expected value, beverage-class context, container-size context, etc.)
- Output contract (disposition, confidence, evidence, citation, structured reason code)
- How a validator declares its match policy
- How validators are composed when one field's validation depends on another

### Q3.3 — Match policy implementations
For each match policy required by D-005, what's the implementation choice?
- **Exact match:** trivial, but: how is whitespace, unicode normalization, line-break handling specified?
- **Tolerance match:** numeric tolerance with class-specific values from T1; how to express "±0.3 pp for spirits, X for wine, Y for malt" cleanly.
- **Fuzzy match:** see Q3.4.
- **Format match:** caps + bold detection for the warning, font-size compliance — how does the engine receive these inputs from upstream OCR/vision?

### Q3.4 — Fuzzy matching algorithm and threshold
For brand-name fuzzy matching specifically: which algorithm and threshold? Compare:
- Edit-distance variants (Levenshtein, Damerau-Levenshtein, Jaro-Winkler)
- Token-based (RapidFuzz, fuzzywuzzy)
- Embedding-based (semantic similarity)
- Rule-augmented (case-fold, strip punctuation, possessive normalization, then exact)

Provide a recommendation with threshold value, justified against Dave's STONE'S THROW vs. Stone's Throw example and similar real-world variants.

### Q3.5 — Confidence-scoring methodology
*Gated by Q3.2.* How does a validator express confidence?
- Sources of uncertainty: OCR confidence, fuzzy match score, ambiguous extracted text, etc.
- How is confidence combined across the pipeline (OCR confidence × match confidence)?
- What threshold(s) separate `pass` / `needs-review` / `fail`?
- How is confidence presented to the agent in the UI?

### Q3.6 — Rejection-reason data model
*Gated by Q3.2.* Specify the structure of a rejection reason:
- Structured reason code (machine-readable, useful for filtering and analytics)
- Human-readable text
- Field reference
- Rule citation (CFR section)
- Evidence (extracted text, image region, expected value)
- Confidence

This is the structure D-007 commits us to. Get it right.

### Q3.7 — Per-class rule routing
*Gated by Q1.1, Q1.6.* How does the engine decide which rules apply to a given application?
- Beverage class is in the application data — but should we also detect from the label?
- What happens when application data and label disagree on class?
- How do conditional rules (Q1.2 — country of origin only for imports) get triggered?

### Q3.8 — Versioning and update strategy
*Gated by Q3.1.* TTB regulations change (T.D. TTB-196 was Nov 2024). How should the rule set be versioned and updated?
- Rule-set versioning approach
- Migration strategy when rules change
- How a deployed version handles applications submitted under prior rule versions
- Audit trail for which rule version evaluated which application

### Q3.9 — Performance budget within 5s SLA
*Gated by Q3.2.* What's the time budget breakdown for the rule engine specifically?
- Expected number of rule evaluations per label
- Per-rule wall-clock target
- Where parallelism helps vs. hurts
- How this fits into the broader 5s budget alongside OCR (T4) and orchestration (T5)

This question synthesizes with X-1 (cross-topic time budget).

### Q3.10 — Failure-mode taxonomy of the engine itself
What are the engine's own failure modes (vs. label-level failures it detects)?
- Missing required input (e.g., no application data)
- Conflicting rules
- Ambiguous OCR input
- Unexpected beverage class
- Rule-set version mismatch

How are these surfaced to the user vs. logged for debugging?

## Cross-topic synthesis questions
*(Held for later.)*

- **X-1 (T3+T4+T5+T6):** End-to-end time budget. Hold for after T5, T6.
- **X-2 (T3+T4+T5):** Decision tree across components (pass/fail/review). Hold for after T4, T5.
- **X-3 (T3+T4+T5+T7):** Production-readiness gaps. Hold for after T7.
- **X-4 (T1+T3):** Rules expressible as data vs. requiring code. Run after T1 output is in hand.

## Notes for the researcher

- Architecture-pattern questions (Q3.1, Q3.2, Q3.5, Q3.8) can be researched independently of T1 in this conversation. Encode-the-actual-rules questions (Q3.3 specifics, Q3.4 thresholds with real test cases, Q3.7) need T1 output.
- Be explicit about the trade-offs of each approach. Avoid recommending the most sophisticated option when a simpler one suffices.
- The output of this topic is partially a recommendation, partially a specification. Distinguish between them.
