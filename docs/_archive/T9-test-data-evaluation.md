# T9 — Test Data & Evaluation Strategy

**Phase:** 4 (User-facing & Eval)
**Status:** PARTIAL — strategy questions ready now; specifics need T1 (rules) and T3 (validators)
**Prerequisites:** T1, T3 for full depth; some questions usable earlier
**Blocks:** —

## Synopsis

The brief encourages us to "create or source additional test labels — AI image generation tools work well for this." But the deeper question is what corpus exercises every rule we encode, every failure mode we expect, and every edge case our stakeholders flagged. The Public COLA Registry has approved labels back to 1999 (per T2 Q2.4) — that's our best free source of real data.

This topic produces both the test corpus design and the evaluation methodology used to validate the prototype against requirements.

## Required reading

- All five core artifacts
- `T1-output.md` (required) — the rule set we're testing against
- `T2-output.md` (required) — for Public COLA Registry access details and label characteristics
- `T3-output.md` (required) — for the validator interface that defines what's testable
- `T4-output.md` (when available) — for image-quality test cases
- Background: precision/recall/F1 for classification, confusion matrix design, evaluation patterns for AI systems with human-in-the-loop

## Output expected

A `T9-output.md` covering:

1. **Test corpus design.** Stratified sample requirements across beverage class, container size, complexity, time period, and failure mode.
2. **Test data sources.** Public COLA Registry, synthetic generation, hand-crafted edge cases.
3. **Failure-mode catalog.** Specific scenarios the system should handle gracefully.
4. **Evaluation metrics.** What "good enough" looks like, quantified.
5. **Stakeholder-specific test cases.** Test cases that demonstrate handling of specific stakeholder concerns (Dave's nuance, Jenny's strictness).
6. **Evaluation harness specification.** How tests are run, scored, and reported.

## In-topic questions

### Questions that can be researched now

#### Q9.1 — Evaluation methodology for human-in-the-loop AI
*Architecture-level, independent of specific rules.* What evaluation patterns are appropriate for systems where the AI is augmentative (not autonomous)?
- Standard precision/recall/F1
- Cost-of-error asymmetry (false-pass vs. false-reject have different costs)
- Calibration metrics (does confidence track accuracy?)
- Time-to-disposition as a metric (a slow correct answer is still a problem)
- Human-disagreement metrics (what if the AI and the agent disagree — which is right?)

Recommend a metric framework.

#### Q9.2 — Public COLA Registry as a data source
*Partially gated by T2 Q2.4.* What can we extract from the Public COLA Registry?
- Search and bulk-extract patterns
- Image quality and format
- Coverage across beverage classes
- Coverage of time periods and rule generations (post-T.D. TTB-176, post-T.D. TTB-196, etc.)
- Programmatic access feasibility

#### Q9.3 — Synthetic label generation
The brief notes "AI image generation tools work well for this." How do we use them well?
- What prompts and tools produce realistic labels (Midjourney, DALL-E, Stable Diffusion, dedicated label-design tools)
- How do we generate labels with *intentional* compliance issues for negative test cases
- Verisimilitude vs. controllability trade-off
- Licensing of generated content

#### Q9.4 — Adversarial / edge case design
What does an adversarial test corpus look like for this system?
- Brand-name variants (Dave's STONE'S THROW family)
- Off-by-tolerance ABV (just outside / just inside the ±0.3 pp window)
- Altered warning text (one word changed, case modified, formatted wrong)
- Image quality degradations (controlled blur, glare, rotation)
- Multi-label submissions (front + back panels)
- Class-confused submissions (looks like spirits but submitted as malt)
- Empty / malformed inputs

#### Q9.5 — Stakeholder-specific test cases
*Architecture-level, refined as upstream completes.* Map each stakeholder's stated concerns to specific test cases:
- **Sarah's 5s SLA** → latency tests across realistic-difficulty inputs
- **Sarah's batch handling** → 200-, 300-label batch tests with varying review times
- **Dave's nuance** → fuzzy-match acceptance set
- **Jenny's strictness** → warning-statement adversarial set
- **Marcus's "don't do anything crazy"** → security smoke tests
- **Janet's batch** → upload-flow stress tests

#### Q9.6 — Evaluation harness design
What's the harness that runs these tests and produces a scorecard?
- Test case format (input → expected output)
- Per-test pass/fail criteria
- Aggregate scoring (per beverage class, per failure mode, per stakeholder concern)
- Regression suite for ongoing development
- Reporting format (what does the scorecard look like that goes in the README?)

#### Q9.7 — Confidence calibration evaluation
*Gated by T3 Q3.5 and T5 Q5.7.* Once components have confidence scores, do they track accuracy? Calibration is often poor in AI systems and matters for the "needs review" disposition.

### Questions that need prerequisites

#### Q9.8 — Per-rule test cases [needs T1, T3]
*Once the rule set is defined and validators are specified, every rule needs at least one positive and one negative test case.* Stub:

For each rule in `T1-output.md`, design:
- Positive case (rule passes)
- Negative case (rule fails, expected reason code matches)
- Edge case (boundary of the rule, e.g., exactly at tolerance limit)

#### Q9.9 — Coverage analysis [needs T1, T3]
*Once rules and tests exist, what's the coverage?*
- Rules with at least one test: target 100%
- Rules with at least one positive and one negative: target 100% for hard-tier rules
- Beverage classes covered: stretch goal
- Failure modes covered: target by stakeholder priority

#### Q9.10 — End-to-end SLA testing [needs T3, T4, T5, T6]
*Cannot meaningfully test until the system exists end-to-end.* Stub:

Latency tests at each component boundary. Where does the 5s SLA budget go in practice? Where are the surprises?

## Cross-topic synthesis questions
*(Held for later.)*

- **X-5 (T1+T2+T9):** Test corpus design with full coverage of rules and realistic data sources. Essentially this topic's headline output.
- **X-6 (T8+T9+T10):** Demo path that hits stakeholder signals. Hold for synthesis.

## Notes for the researcher

- "Test data" and "evaluation methodology" are different problems and the answers shouldn't be conflated.
- Don't over-index on synthetic data. Real labels from the Public COLA Registry are more credible.
- For Dave's nuance test cases (Q9.5): manually curate them. AI generation will miss the specifics.
- The evaluation harness output is what shows up in the README. Design it to communicate to the take-home reviewer, not just to be technically rigorous.
- A specific anti-pattern to avoid: testing only the happy path. The brief specifically called out that Dave looks for misses — the test corpus should make those misses easy to find if they're there.
