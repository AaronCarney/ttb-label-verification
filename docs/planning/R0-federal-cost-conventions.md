# R0 — Federal Cost & Budget Analysis Conventions

**Status:** REFERENCE — not a research topic; settled context for T7, T11, T12
**Last updated:** 2026-04-28

## Purpose

This document captures what federal audiences expect when reading cost, benefit, and budget analyses for IT investments. Unlike the Tn briefs, this is not open research — these are mandatory or strongly normative standards with fixed, citable answers. T11 (economic analysis) and T12 (visualization) both pull from this rather than re-researching the primary sources independently. T7 (federal deployment) references this where compliance overhead enters the cost story.

Treat this as required reading for T7, T11, and T12 conversations.

## The three documents that matter

| Document | Role | Status |
|---|---|---|
| **OMB Circular A-94** *(Nov 2023 revision)* | Mandatory framework for benefit-cost and cost-effectiveness analyses of federal spending | Required for analyses submitted to OMB |
| **GAO Cost Estimating and Assessment Guide** *(GAO-20-195G, Mar 2020)* | Best-practice standard; GAO's audit criteria for cost estimates | Used as audit standard government-wide |
| **OMB Circular A-11 + Exhibit 300** *(annual)* | The actual budget-document format for major IT investments | Required deliverable for funded IT |

A fourth document, **OMB Circular A-4** (Nov 2023 revision), governs regulatory analysis specifically. It's not directly applicable to our internal-use tool but is referenced throughout A-94. Cite where relevant; don't structure to.

## What A-94 requires

A-94 is the framework. Every federal benefit-cost analysis of significant scope follows it. Key requirements relevant to our project:

**Scope trigger.** Applies to programs producing measurable benefits or costs extending **three or more years** into the future. Our system clears that bar.

**Analytic technique.** Two options:
- **Benefit-cost analysis (BCA)** — when benefits can be monetized. The "standard criterion for deciding whether a government project can be justified on economic principles is discounted net benefits."
- **Cost-effectiveness analysis (CEA)** — when benefits are equal across alternatives or have been mandated. Less comprehensive but easier when monetization is contested.

For our project, **CEA is the better fit** at prototype stage because the benefits (compliance throughput) are partly mandated and the alternatives differ mainly in cost. BCA becomes available later if labor savings can be cleanly monetized.

**Required components of any A-94-compliant analysis:**
1. Statement of objectives
2. Identification of alternatives (including a no-action baseline)
3. Analysis time horizon
4. Costs and benefits, monetized where feasible
5. Treatment of uncertainty
6. Sensitivity analysis
7. Distributional and equity considerations
8. Recommendation

**Discount rates.** A-94 Appendix C is updated annually with current rates. The most recent revision (November 2024, valid through end of 2025; expect a new version annually) gives specific real and nominal Treasury rates. **Do not invent a discount rate.** The current Appendix C value at time of analysis is what you cite.

For cost-effectiveness analysis (our likely framing), the rate to use is the **real Treasury borrowing rate on marketable securities of comparable maturity to the period of analysis**.

**Constant vs. nominal dollars.** A-94 prefers constant-dollar (real) values to avoid inflation distortion. If using nominal flows, use nominal discount rates; if real, use real rates. Don't mix.

**Treatment of uncertainty.** A-94 explicitly directs that analyses incorporate uncertainty treatment. Sensitivity analysis is not optional — it's a required component of the analysis, not a value-add.

**Risk premium.** A-94 (2023 revision) introduces a default risk adjustment for projects with net benefits correlated with aggregate consumption. For internal IT projects this is usually not material, but the concept exists and OMB approval is required for non-default treatments.

## What the GAO Cost Guide adds

GAO-20-195G is the operational counterpart to A-94's framework. Where A-94 says *what* an analysis must contain, GAO says *how* to produce a credible one. GAO uses this guide as audit criteria — meaning if our analysis is reviewed, it'll be checked against this standard.

**Four characteristics of a reliable estimate.** This is the headline framework. Every credible federal cost estimate must be:

- **Comprehensive** — life-cycle costs, all WBS elements, all assumptions documented
- **Well-documented** — methodology, sources, calculations all traceable
- **Accurate** — minimal mathematical mistakes, properly inflated/deflated, cross-checked
- **Credible** — sensitivity analysis done, risk and uncertainty addressed, independent review

These four words are conventions worth using directly in our analysis. Audiences who know the standard will recognize them.

**Twelve-step process.** GAO's required steps:

1. Define the estimate's purpose
2. Develop the estimating plan
3. Define program characteristics (technical baseline)
4. Determine the estimating structure (work breakdown structure / WBS)
5. Identify ground rules and assumptions
6. Obtain the data
7. Develop the point estimate and compare to an independent cost estimate
8. Conduct sensitivity analysis
9. Conduct risk and uncertainty analysis
10. Document the estimate
11. Present the estimate to management
12. Update the estimate to reflect actual costs and changes

For our project, steps 5, 7, 8, 9, and 10 are the most directly relevant. Step 4 (WBS) gives the cost breakdown structure that should organize T11's per-option costing.

**Work breakdown structure (WBS).** GAO calls this "the cornerstone of every program." The WBS decomposes the program into work elements; costs are estimated per element and rolled up. For a system like ours, a typical WBS would have:
- Hardware
- Software (licensed and developed)
- Personnel (development, ops, sustainment)
- Facilities and infrastructure
- Training
- Integration and testing
- Documentation
- Government program management
- Contingency

T11 should use a WBS to organize per-option costing rather than ad-hoc cost categories.

**Ground rules and assumptions (GR&A).** GAO requires a documented GR&A section. Every assumption that drives the estimate gets stated explicitly — labor rates used, escalation factors, technology refresh cycles, agent productivity assumptions. T11's Q11.1–Q11.8 already capture this; just make sure the output is structured as a GR&A document, not embedded narrative.

**Sensitivity vs. risk/uncertainty distinction.** GAO treats these as separate steps:
- **Sensitivity analysis** (step 8): "what if this single input changes" — single-variable analysis showing the impact of varying each input
- **Risk and uncertainty analysis** (step 9): "what's the probabilistic distribution of total cost given joint variation in inputs" — typically Monte Carlo

For T11, both are appropriate. Sensitivity (tornado diagrams) is the headline; uncertainty (joint variation, possibly with simulation) is the supporting depth.

**Cost-estimate confidence.** GAO recommends presenting cost as a **range with confidence levels**, not a point estimate. Common conventions: 50th-percentile estimate ("most likely"), 80th-percentile or "should-cost" estimate, and a 90th-percentile reserve. Federal audiences are accustomed to seeing these tiers.

## What Exhibit 300 / A-11 adds

Circular A-11 governs annual budget submissions. **Exhibit 300** is the form that funded major IT investments must complete. We are not producing an Exhibit 300, but **its structure tells us what the agency will eventually need** — which influences what our analysis should anticipate.

**Exhibit 300 expects:**
- Investment summary and mission justification
- Performance measures (outcome-oriented, quantified)
- Cost / schedule / performance baseline
- Earned-value management (EVM) data on execution
- Risk management plan
- Acquisition strategy
- Section 508 compliance statement
- Privacy impact assessment
- Security categorization
- IT architecture alignment

For our purposes, the takeaways are:
1. **Performance measures must be outcome-oriented and quantified.** "Improves agent productivity" is not Exhibit 300-grade. "Reduces median per-application processing time from X minutes to Y minutes" is.
2. **Cost baseline is presented over a multi-year horizon**, broken down by year, by phase (planning / acquisition / O&M).
3. **Earned-value management (EVM) thresholds matter at production.** Investments with cost or schedule variances above 10% trigger additional review.

T11 should produce numbers that could feed an Exhibit 300 if the project advances. T12 should produce visuals that wouldn't look out of place in one.

## Treasury / TTB-specific notes

TTB falls under Treasury. Treasury has its own Acquisition Procedures (Subpart 1007.70 referenced in IRS guidance — likely similar at TTB). Internal Treasury bureaus typically follow GAO's 12-step process directly, sometimes with internal supplements.

The **IRS Internal Revenue Manual section 1.33.9** (Cost Estimating Guidelines, August 2025 update) is a publicly-readable example of how a Treasury bureau implements GAO-20-195G. It explicitly cites the 12 steps and the four pillars. TTB's internal practice is likely similar; if specific TTB cost-estimating guidance is published, it should be located and used.

## Conventions audiences expect to see

Beyond the formal requirements, federal audiences read for specific signals of competence:

**Specific to cost analyses:**
- **Cite A-94 by section number** when grounding methodology choices
- **Cite GAO-20-195G** when justifying the estimating approach
- **Use "comprehensive, well-documented, accurate, credible"** as section headers or assessment criteria — auditors recognize these
- **Include a Ground Rules and Assumptions section** clearly labeled
- **Present a WBS** (or WBS-equivalent breakdown) as the structural backbone of cost figures
- **Show sensitivity tornado diagram** for top input drivers
- **Present cost as a range** with stated confidence percentile, not a single number
- **Compare against an independent cost estimate** where possible (or note that one wasn't produced and why)
- **Use real (constant-dollar) figures by default**, with nominal as supplementary
- **Cite OPM and Treasury salary tables** for labor cost loading (not generic figures)

**Anti-patterns specifically to avoid:**
- Single-point ROI without uncertainty bounds
- Cost-savings projections without realization-rate discussion
- Discount rates pulled from outside Appendix C
- "Industry-standard" assumptions without source
- Mixed real/nominal figures
- Visualizations that compress range to point
- Performance metrics that aren't outcome-quantified
- Lock-in and switching costs left out of the cost story

## How this maps to our existing T11 structure

T11's five stages map onto these conventions as follows:

| T11 Stage | Maps to |
|---|---|
| Stage 1 — Time saved per application | GR&A; primary input variables |
| Stage 2 — Aggregate annual savings | Benefits side of CEA |
| Stage 3 — Per-option cost at scale | WBS-organized cost element structure (GAO step 4 + 7) |
| Stage 4 — Net value | The headline analysis output |
| Stage 5 — Sensitivity | GAO step 8 (sensitivity) + step 9 (risk/uncertainty) |

T11 doesn't need restructuring; it just needs to be **labeled in federal-convention language** and to **cite the right sources** in the right places. The analysis substance is correct.

## What T12 should know

T12's visualization choices should reflect federal convention:
- **Tornado diagrams** are standard for sensitivity (Q12.6 — confirmed canonical)
- **Range bars or fan charts** are standard for cost-with-uncertainty (Q12.4)
- **Tables-and-text density** is preferred over dashboard chrome for policy audiences (Q12.3 — confirmed)
- **Cost figures should be presented with explicit confidence percentiles** (e.g., "50th percentile: $X; 80th percentile: $Y")
- **Cite A-94 / GAO-20-195G in chart footnotes** where conventions are being followed; this signals competence to expert readers

## Sources

Primary documents (download for reference):
- OMB Circular A-94 (Nov 2023): https://www.whitehouse.gov/wp-content/uploads/2023/11/CircularA-94.pdf
- OMB Circular A-94 Appendix C (annual; check whitehouse.gov for current year): https://www.whitehouse.gov/wp-content/uploads/2025/01/CircularA-94AppendixC.pdf (or current)
- GAO Cost Estimating and Assessment Guide (GAO-20-195G, Mar 2020): https://www.gao.gov/products/gao-20-195g
- OMB Circular A-11 (current annual): https://www.whitehouse.gov/omb/information-for-agencies/circulars/

Operational examples:
- IRS IRM 1.33.9 (Cost Estimating Guidelines): https://www.irs.gov/irm/part1/irm_01-033-009
- FEMA BCA policy implementing A-94 discount rate: https://www.fema.gov/sites/default/files/documents/fema_policy-206-23-001-bca-discount-rate-and-streamlined-approaches_april-24-2024.pdf

These are the citations T11 and T12 should use directly.
