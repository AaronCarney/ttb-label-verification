# T8 — UX Design for Federal & Senior Users

**Phase:** 4 (User-facing & Eval)
**Status:** PARTIAL — design principles can be researched now; specifics need T2 (workflow), T7 (Section 508), and outputs from T3-T6 (what the UI actually shows)
**Prerequisites:** T2 for full depth on workflow; T7 for accessibility; T3-T6 partial for UI surface
**Blocks:** —

## Synopsis

Sarah set the bar: "my mother could figure it out" — 73 years old, just learned to video call last year. Half the team is over 50. Dave (28 years) prints his emails. Jenny (8 months) is digitally native. The UX must serve the senior end of this distribution without alienating the junior end.

Per D-007, the UI must surface field-level evidence, rule citations, and confidence. Per D-002, manual review is always available. Per the brief, the "didn't make my life harder" bar is real — Dave has seen modernization projects fail before, and his bar for "this is worth using" is high.

This is a design-principles topic as much as a research topic. The output is a design language and interaction patterns, not a Figma file.

## Required reading

- All five core artifacts
- `T2-output.md` (when available) — agent workflow detail
- `T7-output.md` (when available) — Section 508 / accessibility requirements
- `T3-output.md`, `T4-output.md`, `T5-output.md` (when available) — what data the UI surfaces
- Background: USWDS (U.S. Web Design System), age-inclusive design research, Nielsen-Norman age-related research, accessible data-table patterns

## Output expected

A `T8-output.md` covering:

1. **Design principles** for this user base (with rationale, not just a list).
2. **Information architecture** for single-label and batch flows.
3. **Specific component patterns** for high-value interactions (evidence display, manual override, batch review).
4. **Accessibility specifications** that feed implementation.
5. **Anti-patterns** — things specifically *not* to do, with reference to the failed pilot context.

## In-topic questions

### Questions that can be researched now

#### Q8.1 — Design principles for an age-diverse, mixed-comfort user base
What does the research say about designing for users who span 25 to 70+ in age and dramatically varying tech comfort? Draw on:
- Nielsen-Norman research on age-related UX considerations
- USWDS principles
- Government Digital Service (UK GDS) research on inclusive design
- Specific findings on text size, contrast, click target size, motion, cognitive load

Translate into 5-7 concrete design principles for our UI.

#### Q8.2 — Trust-establishment patterns for AI-assisted workflows
Dave doesn't trust modernization projects. The UI has to earn trust. What patterns build trust in AI-assisted decisions?
- Showing the "work" (what was checked, what was found)
- Calibrated confidence display
- Clear distinction between "AI thinks" and "rule says"
- Easy override / disagree paths
- Transparent failure modes

How do these compose into a coherent design philosophy?

#### Q8.3 — Evidence display patterns
*Architecture-level question, partially independent of T3-T5 outputs.* For each label, the UI surfaces:
- Pass/fail/needs-review disposition
- Per-field evidence (extracted text, image region, expected value)
- Rule citation
- Confidence

What patterns exist for displaying this densely without overwhelming a senior user? Compare:
- Card-per-field layouts
- Annotated-image overlays
- Side-by-side application/label diffs
- Progressive disclosure (summary → details)

Recommend a hierarchy.

#### Q8.4 — Manual override interaction design
The agent must be able to override any AI/rule decision. Design questions:
- Where is the override surface (per-field, per-label, batch-level)?
- What metadata is captured on override (reason, free text, both)?
- Does override feed back into the system (training data, rule tuning)?
- How do supervisors see override patterns?

#### Q8.5 — Batch review interaction design
*Some aspects gated by T6.* Architecture-level:
- One-at-a-time review vs. parallel grid
- How is queue position shown
- What's the keyboard model (this user base may live on keyboard, not mouse)
- How does the agent "tag out" mid-batch (lunch, escalation)

#### Q8.6 — "Needs better photo" disposition UX
*Gated partially by T4 Q4.6.* When the system says "I can't read this label," what does the agent see?
- The image, with what areas were unclear
- Suggested issues (low resolution, glare, angle)
- Path forward (request new image vs. proceed with manual review)

#### Q8.7 — Error and exception messaging
Government tools are notorious for cryptic error messages. What patterns produce clear, actionable error messaging without being condescending?

#### Q8.8 — Demo path design
*Synthesizes with X-6 (cross-topic).* The take-home is graded on a demo. What's the path through the UI that hits Sarah, Dave, and Jenny's strongest signals in 5–10 minutes?
- Sarah: speed, batch, simplicity
- Dave: nuance handling (STONE'S THROW), trust signals, override path
- Jenny: warning-statement strictness, edge cases

The UI should make this demo path natural without feeling staged.

### Questions that need prerequisites

#### Q8.9 — Workflow integration with agent's existing process [needs T2]
*Cannot fully formulate until T2 documents the real workflow.* How does our UI compose with the agent's existing tools (COLA system queries, internal ALFD systems, reference materials)? Does the agent flip between windows? Are there hand-offs we should anticipate?

#### Q8.10 — Section 508 specifications [needs T7 Q7.6]
*Concrete accessibility requirements feed implementation specs.* Once T7 nails the compliance bar, derive specific implementation requirements for our UI components.

#### Q8.11 — Information density vs. processing time tradeoff [needs T3, T4, T5 outputs]
*Once we know what data the upstream components produce, decide what gets surfaced where.* Information that helps an agent vs. clutter that slows them down.

## Cross-topic synthesis questions
*(Held for later.)*

- **X-6 (T8+T9+T10):** Demo path that hits all stakeholder signals. Hold for after T9, T10.

## Notes for the researcher

- Resist the temptation to design beautiful screens. The output should be principles and patterns, not pixel-perfect mockups. Mockups come later, downstream of these principles.
- The age-diversity angle is the easiest to underweight. Don't.
- Sarah's "my mother could figure it out" is a heuristic, not a test. It's useful for ruling things out, not for validating things in.
- Take Dave's "don't make my life harder" seriously. Every interaction we add costs trust if it doesn't earn its place.
- A good answer here distinguishes between *design principles* (durable, applied to many decisions), *interaction patterns* (specific recurring solutions), and *components* (specific UI elements). Confusing these levels weakens the output.
