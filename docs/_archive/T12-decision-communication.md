# T12 — Decision Communication & Visualization

**Phase:** 4 (User-facing & Eval)
**Status:** PARTIAL — principles and pattern research can run now; specific applications need T11 (primary) and other topics' outputs (secondary)
**Prerequisites:** None for principles; T11 for primary application; T7, T8, T9, T10 for secondary applications
**Blocks:** —

## Synopsis

T11 produces the economic analysis as a staged, range-based model. T12 is about how that analysis — and other decision-relevant material in this project — gets communicated to humans. The bias of this topic is heavy on T11's economic analysis, since that's where the visualization burden is highest and where bad communication does the most damage. But the principles surfaced here also apply to other artifacts: architecture diagrams, stakeholder maps, evaluation scorecards, the demo path, the README itself.

Visualization is a real research topic, not decoration. There's substantial literature on what works for what audience and what decision type. The questions worth researching deliberately are the non-obvious ones: how to show uncertainty without losing credibility, how to communicate staged analysis without drowning the audience in stages, how to handle audiences with different needs from the same underlying material. The "what chart type for what data" basics don't need their own research — they're well-trodden.

## Required reading

- All five core artifacts
- `T11-output.md` (primary application target)
- `T7-output.md`, `T8-output.md`, `T9-output.md`, `T10-output.md` (secondary application targets, when available)
- Background reading priorities:
  - Edward Tufte's principles (esp. data-ink, small multiples, sparklines)
  - Cole Nussbaumer Knaflic, *Storytelling with Data* — practitioner-oriented
  - Stephen Few on dashboard design
  - Federal/policy-audience visualization conventions: GAO report graphics, CBO publication style, OMB exhibits
  - Uncertainty visualization research: Spiegelhalter, fan charts, hypothetical outcome plots (HOPs), error bars vs. distributions
  - Decision-tree and scenario-tree visualization
  - Tornado diagrams and sensitivity-analysis visualization
  - Progressive disclosure and layered reveal patterns

## Output expected

A `T12-output.md` covering:

1. **Audience analysis.** Who's reading what; what they need; what biases they bring.
2. **Visualization principles** for this project specifically (not a generic style guide).
3. **High-leverage visualization decisions** — the 4–6 specific places where research-backed choices matter most.
4. **Pattern library** for staged analysis with uncertainty, applied to T11.
5. **Application notes** for secondary artifacts (architecture diagrams, stakeholder maps, etc.).
6. **Anti-patterns** specific to this project's context.

## In-topic questions

### Audience analysis

#### Q12.1 — Audience map for the project's communication artifacts
Who reads what, in what context, with what time budget, with what biases?
Candidate audiences:
- **The take-home reviewer** (Sarah's team): primary audience for the README and demo
- **Sarah herself**: defends the choice upward; needs ammunition for procurement conversations
- **Marcus / IT**: needs technical-architecture clarity and policy-fit defensibility
- **A federal procurement officer** (hypothetical, but the analysis should anticipate them)
- **A CIO presenting upward**: needs a one-pager that survives executive scrutiny
- **Ourselves**: working artifacts that update as the project evolves

For each: what they need, time budget, what convinces them, what loses them.

#### Q12.2 — Audience-specific framing of the same analysis
*Gated by Q12.1.* For T11's economic analysis specifically, how does the framing change by audience?
- The contracting officer wants a defensible number with a stated method
- Sarah wants a story she can tell upward
- Marcus wants confidence the technical claims hold up
- The reviewer wants to see we thought rigorously

Same numbers, different lead-with. What's the right approach to producing audience-tailored views from a single underlying analysis?

### Visualization principles

#### Q12.3 — Federal/policy audience conventions
Federal audiences have specific conventions and biases. What are they?
- GAO and CBO publication style — what makes their charts trusted
- OMB exhibit conventions
- "Confidence intervals" vs. "ranges" vs. "scenarios" — which framing reads as rigorous vs. evasive
- Color conventions (red/green has political coding in some contexts)
- Density preferences — federal audiences often skew toward higher-density tables-and-text vs. mass-market dashboard aesthetics
- Citation expectations within the visual itself

#### Q12.4 — Uncertainty visualization
*This is the single highest-leverage research area in this topic.* How do you show uncertainty without losing the audience?
- Error bars: when they help and when they confuse
- Fan charts: appropriate for projections; common in BoE and CBO publications
- Hypothetical Outcome Plots (HOPs): research shows people understand them better than error bars; rarely used in practice
- Density strips and gradient plots
- Multiple-scenario small-multiples vs. single chart with overlays
- Showing "we don't know" explicitly — does this hurt or help credibility?
- Audience effects: technical audiences tolerate more density; policy audiences often respond better to scenario framing than to distributions

Recommend specific techniques for T11's outputs.

#### Q12.5 — Staged analysis visualization
T11 is explicitly staged: Stage 1 → 2 → 3 → 4 → 5, with uncertainty propagating forward. How do you communicate this without overwhelming the audience?
- Single chart with progressive layering (interactive only)
- Small multiples showing each stage's range
- Sankey-style flow showing uncertainty propagation
- Step-charts with annotation
- Layered reveal in presentation (hide detail behind clicks/scroll)

Different techniques for different artifacts (README vs. presentation vs. interactive demo).

#### Q12.6 — Sensitivity-analysis visualization
For Stage 5 specifically:
- Tornado diagrams: standard for sensitivity analysis; what makes a good one
- Spider/radar charts: usually bad, but sometimes apt
- Two-way sensitivity charts (heatmaps over two variables)
- Decision-flip-point charts (showing where recommendation changes)
- Tabular sensitivity vs. visual sensitivity — when each is appropriate

#### Q12.7 — Showing "we don't know X" credibly
*Genuinely hard.* When the analysis includes "we don't know the realization rate within ±30%," how do you communicate that without:
- Making the analysis look sloppy
- Letting the audience anchor on the wrong end of the range
- Inviting a "come back when you know" response

Research conventions and patterns. This question alone justifies the topic.

### High-leverage visualization decisions for T11

#### Q12.8 — Headline chart for T11
*Gated by T11 outputs.* What's the single chart that goes at the top of the economic-analysis section? Candidates:
- Net-value range per option (bar with range bars or distribution)
- Break-even chart (recommendation flips at variable X)
- Cost-vs-savings scatter with options as points
- Decision matrix (option × audience-relevant criterion)

#### Q12.9 — Per-stage charts for T11
*Gated by T11 outputs.* For each of the five stages, what's the right visualization?
- Stage 1 (time saved, scenarios) → small multiples or grouped ranges
- Stage 2 (aggregate savings) → fan chart or scenario range
- Stage 3 (per-option costs) → comparison chart with stack/range
- Stage 4 (net value) → headline chart from Q12.8
- Stage 5 (sensitivity) → tornado + flip-point chart

#### Q12.10 — Interactive vs. static
For the deployed prototype's README and demo: should economic-analysis visualizations be interactive (the user can adjust assumptions and see the answer change)? What's the cost-benefit of building this?
- Interactive demonstrates rigor and lets the audience play
- Static is faster to produce and harder to misinterpret
- Hybrid: static for the README, interactive linked separately

### Application to other artifacts

#### Q12.11 — Architecture diagrams [secondary]
*Gated by T3, T4, T5, T6, T7 outputs.* What patterns make a good architecture diagram for this kind of system?
- C4 model (context / container / component / code)
- Sequence diagrams for key flows (single-label, batch)
- Where simple ASCII boxes-and-arrows beats elaborate diagrams
- Federal audiences vs. engineering audiences

#### Q12.12 — Stakeholder maps [secondary]
*Gated by T10 output.* Visualization patterns for the salience model, RACI, stakeholder onion. What works on paper vs. in a slide vs. interactively.

#### Q12.13 — Evaluation scorecards [secondary]
*Gated by T9 output.* How to display test results: precision/recall/F1 per rule, per beverage class, etc. The README's evaluation section likely needs this.

#### Q12.14 — Demo path visualization [secondary]
*Gated by T8 output.* The demo itself is a kind of visualization. How does it pace, when does it pause for context, when does it move?

### Anti-patterns

#### Q12.15 — Anti-patterns specific to this project
What should we explicitly *not* do?
- Vanity metrics (e.g., "processed N labels" without precision/recall)
- Charts that compress range to look like point estimates
- Cherry-picked scenarios presented as "the case"
- 3D charts, gratuitous color, dashboard chrome
- Federal-context-specific: anything that looks like marketing collateral; anything that buries the methodology

## Cross-topic synthesis questions

- **X-6 (T8+T9+T10+T12):** Demo path that hits stakeholder signals and uses appropriate visualization throughout. Hold for synthesis.

## Notes for the researcher

- The bias is toward T11's economic analysis. Spend the most depth on Q12.4 (uncertainty), Q12.5 (staged), Q12.7 (don't-know), Q12.8 and Q12.9 (the actual T11 charts).
- Q12.11–Q12.14 are deliberately lighter — they're real applications but not the headline.
- Don't survey general visualization theory. Cite it where it informs a specific recommendation, but the output should be project-specific decisions, not a textbook.
- **A specific risk:** the "best practice" answer is often anodyne ("use clear labels, avoid 3D"). Push past it. The actually-useful answers are the ones that resolve genuine tension — like "do you show the range or the point estimate when the range is wide and the audience is impatient." Don't dodge those.
- **Federal/policy conventions are non-obvious.** A general data-viz background isn't sufficient; spend time on actual GAO, CBO, OMB outputs to internalize what reads as credible vs. what reads as suspect.
- The output of this topic feeds directly into the README and demo. Format the recommendations with implementation in mind — concrete enough to execute, not just principles to admire.
