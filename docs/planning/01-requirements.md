# Requirements — TTB Label Verification Prototype

**Status:** DRAFT — living document
**Last updated:** 2026-04-28

## Tier system

| Tier | Meaning |
|---|---|
| **Hard** | Non-negotiable. Failure = project failure. |
| **Strong bias** | ~90% likely expected even if not stated as hard. |
| **Medium bias** | Probably valued, not deal-breakers. |
| **Stretch** | Impressive if done, fine if skipped. |
| **Open** | Needs clarification before we can tier. |

## Type tags
`[FUNC]` functional · `[PERF]` performance · `[UX]` usability · `[INFRA]` infrastructure · `[DATA]` data handling · `[SCOPE]` scope boundary · `[REG]` regulatory

---

## Hard

- `[FUNC]` Verify brand name, ABV, net contents, and government warning against application form data.
- `[FUNC]` Government warning checked against exact text from 27 CFR § 16.21.
- `[FUNC]` Detect "GOVERNMENT WARNING" rendered in capital letters and bold (per 27 CFR § 16.22).
- `[FUNC]` **Reasoning required for every rejection.** Every negative or "needs review" disposition must include human-readable explanation tied to a specific field and rule.
- `[PERF]` ~5-second response time per single-label review.
- `[SCOPE]` Standalone prototype. No COLA system integration.
- **Deliverables:** source repo, README with setup/run, deployed URL.

## Strong bias

- `[FUNC]` Batch upload with smart processing order (see Architecture doc — first label prioritized, subsequent grouping sized to keep agents fed).
- `[UX]` Senior-friendly interface. "73-year-old benchmark." No hunting for buttons.
- `[FUNC]` Three-state output per label: pass / fail / needs-review, with field-level evidence.
- `[REG]` Handle wine, spirits, and malt beverage classes (27 CFR Parts 4, 5, 7) at the common-fields level.
- `[FUNC]` Fuzzy/judgment-based matching for brand name (Dave's STONE'S THROW vs Stone's Throw).
- `[DATA]` No persistent storage of submitted artwork beyond session.
- `[UX]` Manual review path always available. Agent can override or do full manual review at any point.

## Medium bias

- `[FUNC]` ABV check uses tolerance per regulation (±0.3 percentage points for distilled spirits per T.D. TTB-158).
- `[FUNC]` Detect bottler/producer name and address; country of origin for imports.
- `[UX]` Per-field confidence score so agents can triage.
- `[INFRA]` Deployment reachable without auth gymnastics for the reviewer.
- `[UX]` Mixed-mode interaction: AI orchestrates deterministic checks; agent always sees what was checked and can drill in.

## Stretch

- `[REG]` Beverage-class-specific validation (vintage for wine, age statements for spirits, etc.).
- `[FUNC]` Image-quality robustness: angles, glare, low light.
- `[REG]` Font-size compliance per container size (1mm / 2mm / 3mm minimums per 27 CFR § 16.22(b)).
- `[REG]` Contrasting-background and "readily legible" heuristics for the warning.
- `[FUNC]` Audit trail / exportable verification report.
- `[UX]` Bulk-results dashboard with sortable disposition.

---

## Resolved clarifications

| # | Question | Resolution |
|---|---|---|
| 1 | Application input format | **Partially resolved.** Real submissions go through COLAs Online or paper TTB Form 5100.31 (current rev 04/2023). For the prototype, exact format still TBD pending stakeholder inquiry. Form fields are publicly documented; Public COLA Registry has real images. |
| 2 | Batch SLA | Architecture decision, not a requirement. Process first label individually under the 5s SLA; size subsequent groupings based on agent review time. See Architecture doc. |
| 3 | Rejection reasoning | **Required.** Promoted to Hard tier. |
| 4 | AI vs deterministic | AI orchestrates; deterministic processes do the actual checking. Manual override always available. |
| 5 | Beverage class rules | **Stretch.** Confirm general system works first. |

## Still-open clarifications

- Exact format of the prototype's "application data" input — JSON payload? PDF of Form 5100.31? Mocked structured object? Need to ask the take-home reviewer or assume.
- Should rejected labels carry a structured reason code (for downstream filtering) in addition to the human-readable reasoning?
- Is the deployed URL expected to be public, or password-protected acceptable?
