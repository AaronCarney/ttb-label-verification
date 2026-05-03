# T11 — Economic Analysis: Labor Savings, TCO, and Sensitivity

**Phase:** 3 (Composed Architecture)
**Status:** PARTIAL — framework questions ready now; per-option costing needs T4/T5 outputs; labor-savings model needs T2 output for empirical grounding
**Prerequisites:** T2 (volume and review-time data); T4 (per-option OCR costs); T5 (per-option LLM costs); T7 partial (policy cost overlay)
**Blocks:** T12 application questions; cross-topic synthesis X-7

## Synopsis

Every architectural option in this project carries a cost story and a savings story. Cloud APIs have per-call costs that grow linearly with volume; self-hosted has fixed hardware and ops costs that amortize across volume. Subscription pricing is subject to vendor change and lock-in risk. Against all of that sits the labor-savings side: ~150–200K applications/year, ~5–10 minutes each by Sarah's estimate, agents at federal GS labor rates.

The output of this topic is not "Option X is cheapest" — it's a **staged, range-based economic model** where each stage's assumptions are explicit and the propagation of uncertainty into the final recommendation is honest. Federal audiences in particular respond better to acknowledged uncertainty than to false precision; a sensitivity analysis that shows where the recommendation flips is more credible than a single-number answer.

This topic produces the numbers. T12 produces the way they're communicated.

## Required reading

- All five core artifacts
- `T2-output.md` — application volume, review-time distributions, batch patterns
- `T4-output.md` — OCR/vision options with per-option resource profiles
- `T5-output.md` — AI orchestration options with per-option resource profiles
- `T7-output.md` (partial acceptable) — for the policy-cost overlay (some options carry compliance costs others don't)
- Background reading: federal labor cost loading (OPM total compensation guidance), Treasury/TTB published budget figures, FedRAMP authorization cost benchmarks, federal IT TCO modeling conventions (GAO and OMB guidance), uncertainty propagation methods (Monte Carlo, scenario analysis, tornado analysis)

## Output expected

A `T11-output.md` covering:

1. **Staged analysis framework.** Five stages (defined below), each producing range outputs that feed the next stage.
2. **Labor-savings model** with explicit driver decomposition.
3. **Per-option TCO models** at three volume tiers and three time horizons.
4. **Net-value comparison** across architectural options.
5. **Sensitivity analysis** showing which inputs drive the recommendation and where it flips.
6. **Lock-in and vendor-risk overlay** for subscription-based options.

## Staged analysis framework

The five stages:

- **Stage 1.** Labor time saved per application (range, by scenario)
- **Stage 2.** Aggregate annual labor savings (range)
- **Stage 3.** Per-option cost at scale (range, per option, per time horizon)
- **Stage 4.** Net value per option (range)
- **Stage 5.** Sensitivity analysis and recommendation-flip points

Each stage's output is a range with stated drivers, not a point estimate. Stage N+1 takes Stage N's full range as input and propagates uncertainty forward.

## In-topic questions

### Stage 1: Labor time saved per application

#### Q11.1 — Decompose the time-saved estimate into driver components
For a single application review, what's the time saved by the system? Decompose into drivers:
- Time spent on routine matching (the system's primary target)
- Time spent on judgment/nuance (the system can't help here)
- Time spent on edge cases and rejections (system may slow this down on hard cases)
- Time spent on overhead (logging, navigation, switching tools)

For each driver, produce a low/expected/high range with stated assumption.

#### Q11.2 — Capability ramp scenarios
*Different agents will benefit differently and capability changes over time.* Build at least three scenarios:
- **Steady-state experienced agent** (Dave-like): low marginal benefit; system saves only routine-check time
- **Steady-state newer agent** (Jenny-like): higher marginal benefit; system handles checklist work she'd do manually
- **First-90-days-of-rollout**: net negative or zero — agents are learning the tool, not yet trusting it
- **Post-rollout transition**: increasing benefit as trust builds

Each scenario has its own time-saved range. Articulate when each scenario applies and at what mix.

#### Q11.3 — Unknown overhead factors
*We need to acknowledge what we don't know.* What overhead factors are we unable to estimate well from public sources, and how do we represent them in the model? Examples:
- Time spent on system errors or false rejections that need investigation
- Cognitive context-switching cost when the system flags something
- Supervisor review time on system-generated dispositions
- Training time amortized across the agent's tenure

Treat each as an explicit "uncertainty bucket" with a low/high range and explicit "we don't know" label rather than a point estimate.

#### Q11.4 — Net time-saved range, per scenario
*Synthesizes Q11.1–Q11.3.* Output: per-application time saved as a range, by scenario, with the underlying drivers traceable.

### Stage 2: Aggregate annual labor savings

#### Q11.5 — Application volume range
*Gated by T2 Q2.7.* What's the range of annual application volume?
- Current state (~150–200K from various sources)
- Year-over-year growth rate
- Peak vs. trough seasonal variance
- 3-year and 5-year projections

Produce ranges, not points.

#### Q11.6 — Federal labor cost loading
What's the fully-loaded labor cost for an ALFD compliance agent?
- Base GS-grade range (likely GS-9 to GS-13 for compliance specialists; verify)
- Locality pay (DC vs. Seattle, etc.)
- Benefits and overhead loading factor (OPM publishes this)
- Effective hourly rate range

This needs verification against current OPM and Treasury salary tables.

#### Q11.7 — Aggregate annual savings calculation
*Synthesizes Q11.4, Q11.5, Q11.6.* Compute the range of annual labor savings:
- Per-application time saved range × annual volume range × hourly rate range
- Output is a wide range, deliberately
- Show the math at low/expected/high points and explain which drivers dominate the spread

#### Q11.8 — Realized vs. theoretical savings
Theoretical labor savings rarely translate fully to budget savings. Why?
- Saved time often gets absorbed into deeper review of complex cases (not bad, but not budget-savings)
- Headcount reduction through attrition is slow and politically charged in federal context
- Reallocation to other work depends on whether other work exists
- "Labor savings" and "budget savings" may differ by 30–70%; estimate the realization-rate range

This is genuinely uncertain. Treat it as such.

### Stage 3: Per-option cost at scale

#### Q11.9 — Cost model template
*Architecture-level, can be researched now.* Define the cost model template that every option gets scored against:
- One-time costs (hardware, integration, ATO, security review)
- Recurring fixed costs (subscriptions, support contracts, hosting, ops labor)
- Variable costs (per-call API fees, compute hours)
- Hidden costs (vendor lock-in remediation, version migration, model deprecation)
- Time horizon (3-year and 5-year)
- Volume tier (current, expected growth, peak)

Output: a template that any option can be plugged into.

#### Q11.10 — Cloud OCR / vision option costing [needs T4]
*Once T4 specifies which cloud OCR options are credible, cost each one.* Per-page rates are public. Project against volume tiers. Include FedRAMP-authorized variants where they cost more than commercial.

#### Q11.11 — Self-hosted OCR option costing [needs T4]
Hardware (one-time + refresh cycle), ops labor, hosting (assume on-prem or Azure Government region), software licensing if any. Compare across self-hosted candidates.

#### Q11.12 — Cloud LLM option costing [needs T5]
*Once T5 specifies which cloud LLM options are credible.* Per-token costs at projected per-application token usage. Include cost-of-prompt-iteration during build. Include risk premium for vendor price changes.

#### Q11.13 — Self-hosted LLM option costing [needs T5]
GPU hardware costs (one-time + refresh), inference framework licensing, ops labor, electricity, cooling. Realistic cost on budget GPUs (consumer-grade) vs. datacenter-grade.

#### Q11.14 — Subscription lock-in and price-change risk
*This is the "what if the vendor doubles prices" question.* For each cloud-based option:
- Switching cost (time + integration work) to migrate to an alternative
- Historical price-change pattern of the vendor
- Risk premium to apply to the cost projection
- Negotiating leverage at federal scale

Treat lock-in as a real cost component, not a footnote.

#### Q11.15 — Hybrid option costing
Most architectures end up hybrid — some cloud, some local. Define 2–3 plausible hybrid configurations and cost each.

### Stage 4: Net value per option

#### Q11.16 — Net-value calculation per option
*Synthesizes Stage 2 and Stage 3.* For each architectural option:
- Total cost over time horizon (range from Stage 3)
- Realized labor savings over same horizon (range from Stage 2 + Q11.8)
- Net value = savings − cost (range)
- Break-even volume / break-even time-saved-per-application

#### Q11.17 — Non-monetizable factors
Cost-benefit isn't only dollars. What other factors matter?
- Risk reduction (better detection of compliance violations)
- Agent experience (less drudgery, harder to quantify but real)
- Public trust in the regulator
- Optionality (system that can adapt to rule changes vs. one that can't)

Articulate these explicitly without forcing a dollar value where one isn't credible.

### Stage 5: Sensitivity analysis

#### Q11.18 — Sensitivity to each input
Which inputs drive the recommendation most?
- Time-saved-per-application: how much does it move the answer?
- Realization rate: same question
- Volume growth: same
- Per-call cloud cost: same
- Hardware cost: same
- Ops labor: same

Produce a tornado-diagram-equivalent: ordered list of inputs by sensitivity.

#### Q11.19 — Recommendation flip points
Where do the recommendations between options actually change?
- At what cloud price point does cloud become clearly better than self-hosted?
- At what volume does self-hosted amortize past cloud?
- At what realization rate does the whole investment fail to clear?
- At what subscription price hike does lock-in become disqualifying?

This is the most useful output for decision-makers — it tells them what to watch.

#### Q11.20 — Headline framing
*Synthesizes everything.* How should the analysis be framed at the top? Examples:
- "The system pays for itself if it saves at least N minutes per application; here's what's plausible."
- "At current volume, cloud APIs cost less than $X/year — well below the labor savings range; lock-in risk dominates the choice."
- Or: "Cost is a wash; choose on policy and risk grounds."

The honest framing depends on what the numbers actually say. Don't force a frame; let the analysis pick it.

## Cross-topic synthesis questions

- **X-7 (T7+T11):** Map cost × policy × technical fit per option, producing the headline trade-off chart that goes in the README. Hold for synthesis after T7 and T11 are complete.

## Notes for the researcher

- **Ranges, not points.** Every input. Every intermediate. Every conclusion. Document the basis for the range bounds.
- **Cite labor-cost numbers** to OPM tables and Treasury salary disclosures, not generic figures. Federal audiences will check.
- **Don't smuggle in confidence.** "We don't know X" is a valid output. Saying we know X when we don't is worse than saying we don't.
- **The realization rate (Q11.8) is the single most consequential and most uncertain number.** Spend disproportionate effort on it. Wrong realization rates have killed real federal IT business cases.
- **Lock-in (Q11.14) is underweighted in most TCO analyses.** Federal context makes it worse — switching takes years, not months. Don't underweight it here.
- **The output here is the input to T12.** Format it with that downstream use in mind: every range needs explicit bounds, every stage needs traceable drivers, every conclusion needs an uncertainty statement that can be visualized.
