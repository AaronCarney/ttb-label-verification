# Architecture — TTB Label Verification Prototype

**Status:** DRAFT
**Last updated:** 2026-04-28

## Guiding principles

1. **Deterministic where possible, AI where necessary.** Most label verification is rule-matching. AI orchestrates and handles ambiguity (fuzzy brand-name match, OCR cleanup); deterministic code does the actual rule evaluation.
2. **Human-in-the-loop is the design center, not a fallback.** The agent is the decision-maker. The system surfaces evidence; it does not decide.
3. **Production parity in design scope.** Even though this is a prototype, design choices should not box out an on-prem / firewall-friendly production deployment. Federal compliance environments are unlikely to permit unrestricted cloud inference.
4. **Reasoning is a first-class output.** Every disposition (pass / fail / needs-review) carries field-level evidence and rule citations.

## High-level data flow

```
[Application data]  +  [Label image(s)]
        |
        v
+----------------------------+
|     Input handler          |  validate inputs, normalize
+----------------------------+
        |
        v
+----------------------------+
|  Vision / OCR layer        |  extract text + regions from label
+----------------------------+
        |
        v
+----------------------------+
|  AI orchestration layer    |  decide which checks apply
|  (lightweight, supervisory)|  resolve ambiguity (e.g. fuzzy brand)
+----------------------------+
        |
        v
+----------------------------+
|  Deterministic rule core   |  per-field validators with policies
|  - Exact match (warning)   |
|  - Tolerance match (ABV)   |
|  - Fuzzy match (brand)     |
+----------------------------+
        |
        v
+----------------------------+
|  Reasoning assembler       |  per-field disposition + evidence
+----------------------------+
        |
        v
+----------------------------+
|  Agent UI                  |  pass/fail/review + manual review path
+----------------------------+
```

## Core components

### Input handler
Accepts an application payload (format TBD — see Requirements doc) and one or more label images. Normalizes encodings, validates that required fields are present.

### Vision / OCR layer
Extracts text and bounding regions from label images. For the prototype, cloud OCR is acceptable. For production parity, design must accommodate swap to on-prem (Tesseract, PaddleOCR, or a self-hosted vision model).

### AI orchestration layer
Lightweight. Decides which deterministic checks apply (based on beverage class, container size, etc.) and resolves ambiguities the rule core can't handle alone (e.g., is "STONE'S THROW" the same brand as "Stone's Throw"?). Should be small enough to run reasonably fast and to be replaceable with a self-hosted model later.

### Deterministic rule core
Per-field validators, each with an explicit policy:

| Field | Policy | Notes |
|---|---|---|
| Government warning text | Exact match | Word-for-word per 27 CFR § 16.21 |
| "GOVERNMENT WARNING" formatting | Exact (caps + bold) | Per 27 CFR § 16.22(a)(2) |
| Brand name | Fuzzy match | Configurable similarity threshold |
| ABV | Tolerance match | ±0.3 pp for spirits; class-specific |
| Net contents | Exact (after unit normalization) | mL ↔ fl oz |
| Bottler / producer | Fuzzy match | Address fields normalized |

Each validator returns: `{disposition, confidence, evidence, rule_citation}`.

### Reasoning assembler
Combines per-field results into an overall label disposition with structured rejection reasons. Output schema includes both human-readable text and a machine-readable reason code.

### Agent UI
- Single-label view with field-level evidence (image crop + extracted text + rule check + disposition).
- Batch view with sortable queue.
- One-click manual review override.
- Always shows what was checked and what wasn't.

## Batch architecture

Per stakeholder feedback, batches of 200–300 labels arrive from large importers in peak season. Naive parallel processing would either bury the SLA or starve the queue.

**Approach:** priority queue with adaptive lookahead.

1. First label in a batch processed individually under the 5s SLA → returned immediately so the agent can start reviewing.
2. While the agent reviews label N, the system processes a lookahead group of size *k*.
3. *k* is sized so the next label is ready when the agent finishes the current one. *k* depends on:
   - Average per-label processing time (measured)
   - Average agent review time per label (measured; needs empirical data — see Research doc)
   - Available worker capacity
4. Adapt *k* as the batch progresses. If the agent reviews faster than expected, increase *k*. If slower, throttle to avoid wasted compute.

**Open architecture question:** how to handle agent override/rejection mid-batch — does it stop the queue, or continue?

## Production parity considerations

Things to avoid baking in even at prototype stage, because they'd block a production path through the federal procurement / FedRAMP gauntlet:

- Hard dependency on a single cloud OCR/vision provider. Wrap behind an interface so it can be swapped.
- Storing label artwork or PII anywhere outside session memory.
- Authentication patterns incompatible with PIV / SAML federation.
- Outbound calls to domains not in a typical agency allow-list.

The IT admin (Marcus) explicitly noted that the prior vendor pilot failed in part because the agency firewall blocked their ML endpoints. Designing now for self-hosted inference later is cheap; refactoring later is not.

## Open architecture questions

- How does the AI orchestration layer pick which fields to even check? (Beverage class detection from the label vs. from the application form)
- Where does the OCR confidence threshold live for triggering a "needs review" instead of a "fail"?
- How do we represent and version the rule set so updates to TTB regulations don't require code changes?
- Should the manual review path be a separate UI mode, or integrated into the same view?
