# Session 2 — MVP Scope & Demo Shape Commitments

**Project:** TTB AI-Powered Alcohol Label Verification — Take-Home
**Date:** 2026-04-30
**Status:** Decided. Append D-010 / D-011 / D-012 to `03-decisions.md`.

---

## Sources of authority

- Original take-home brief (interview notes: Sarah, Marcus, Dave, Jenny; technical requirements; deliverables).
- `01-requirements.md` — Hard / Strong / Medium / Stretch tiering.
- `T1-output.md` — TTB regulatory framework. Anchors: §1.1 field manifest, §3 §16.22 warning rules, §12.2 wine modernization risk, §12.12 AVA count (279), §12.13 allowable-revisions count (41).
- `T8-output.md` — UX design + Q8.8 7-stage demo path; DP1–DP7 principles; fixtures 01–07.
- `T10-output.md` — Q10.4–Q10.6 empathy maps; TL;DR ("STONE'S THROW must be in first 3 demo labels"); Q10.7 #1 (cold-start risk).

---

## Note on one candidate override

Question 1's default candidate proposed "rule-pack depth = wine." I'm committing to **rule-pack depth = spirits** instead. Three reasons:

- Brief's worked example is a spirits label (Old Tom Distillery, Kentucky Straight Bourbon, 45% Alc./Vol., 750 mL).
- Parts 5/7 are post-modernization stable (T1 §0 — T.D. TTB-176 eff. 2022, T.D. TTB-199 eff. 2025); Part 4 is pre-modernization and at risk of renumbering during 2026 if T.D. TTB-202 issues (T1 §12.2).
- D-006's ±0.3 pp ABV tolerance is already authored against spirits (T.D. TTB-158).

All other session-candidate defaults stand.

---

## PRD-ready feature table

| # | Feature | MVP / Stretch / Out | Rationale (persona / brief / T1) | Demo role |
|---|---|---|---|---|
| 1a | Three classes at common-fields level (wine ≥7%, spirits, malt) | **MVP** | `01-requirements.md` Strong bias. Brief: "exact requirements vary by beverage type … but common elements include…". T1 §1.1–§1.3 manifest. | Stage 1 + 5 use spirits; Stage 5 batch mixes classes. |
| 1b | Deep rule-pack = spirits (class/type vs. §5 SoI; age statement floor) | **MVP-light** | Brief example is spirits; D-006 already spirits-anchored; Parts 5/7 stable per T1 §0; overrides session candidate of "wine." | Stage 1 narrates "Kentucky Straight Bourbon" as a recognized class/type. |
| 1c | Wine depth (vintage, AVA, appellation, sulfite) | **Stretch** | D-003. Wine modernization unsettled (T1 §12.2). | Not in 5-min cut. |
| 1d | Malt depth (SoC, formula matching) | **Stretch** | D-003. T1 §11 (SoC matching = #1 spirits return reason; same logic for malt). | Not in 5-min cut. |
| 2 | 7 common fields: brand, class/type, ABV, net contents, bottler name+address, country of origin, government warning | **MVP** | Brief "Additional Context" lists exactly these. Sarah: "essentially data entry verification." Hard tier covers 4 of 7; the other 3 are Medium bias and cheap. | Stages 1–3 surface all 7 in field-card grid. |
| 2a | Conditional fields (sulfite ≥10 ppm, AVA, organic, allergen, cochineal/carmine) | **Out** | T1 §1.1 marks conditional; T1 §12.3 (Notice 237/238 not mandatory); T1 §12.14 (cochineal grandfathered). No persona signal. | None. |
| 3a | All-caps detection on "GOVERNMENT WARNING:" header | **MVP** | `01-requirements.md` Hard. T1 §3 / 27 CFR §16.22(a)(2). Jenny: "all caps and bold." | Stage 3 fail case. |
| 3b | Bold detection on "GOVERNMENT WARNING:" header | **MVP** | Same regulatory citation; Jenny named bold explicitly. Cheap with stroke-width heuristic on OCR'd glyphs. | Stage 3 — second reason on the same fail. |
| 3c | Font-size compliance per container size (1/2/3 mm CPI table) | **Stretch** | `01-requirements.md` Stretch. T1 §12.4 cardinal-not-continuous; non-trivial OCR work. | Not in 5-min cut. |
| 4 | Batch upload (drag-drop ZIP, smart processing order, k=2–3 lookahead) | **MVP** | Sarah: "200, 300 label applications at once… handle batch uploads, that would be huge." Janet from Seattle. T8 Stage 5. | Stage 5 (the Sarah moment). |
| 4a | Bulk-results sortable dashboard | **Stretch** | `01-requirements.md` Stretch. Not a primary persona signal. | Not in 5-min cut. |
| 5 | "Needs better photo" disposition (first-class outcome, applicant-message text shown) | **MVP** | Jenny: "if AI could handle some of that…" Buçinca et al. 2021 (calibrated "I don't know" > confident guess). T8 DP6. | Stage 4 (the Jenny edge case). |
| 5a | Auto-send templated message back to applicant | **Stretch** | T8 open question; agent-confirmed default. No COLA integration in prototype scope. | Show templated text; do not send. |
| 6 | Brand-name fuzzy match (STONE'S THROW vs. Stone's Throw — Jaro-Winkler, reviewable confidence) | **MVP ✓ confirmed** | Dave canonical case. T10 TL;DR: must be in first 3 demo labels. D-005 per-field policies. | Stage 2 (the Dave moment). |
| 7 | AVA whitelist enforcement (279 entries, T1 §12.12 / Part 9 Subpart C) | **Out (MVP); Stretch in wine pack** | Wine-only conditional appellation rule (T1 §1.1 row 9). D-003 puts class-specific in stretch. | Not in 5-min cut. |
| 8 | Allowable-revisions check (41 items, T1 §12.13 / IC 2021-1) | **Out of scope** | Different problem domain: post-approval change auditing, not label-vs-application verification. Brief scopes us to the latter. Mention in README. | None. |
| 9 | Demo length: 5-minute recorded primary; deployed URL self-serve for fuller paths | **MVP** | Brief: "time-constrained… working core preferred." Sarah's time scarcity. T10 TL;DR: Dave's first 30 seconds. | Recording = primary signal channel. |
| 10 | Live deployed URL with pre-warmed orchestrator + LLM responses cached for the 6 fixtures | **MVP (hybrid)** | T10 pre-mortem #1: cold-start past 5 s = trust killer. T8 §"Demo failure-recovery" items 1–2: pre-warm + cache. Narration discloses caching honestly. | All stages. |
| 11 | Deliverables: repo + README + deployed URL + 5-min recorded walkthrough | **MVP** | Brief deliverables = repo + URL. Recording added so persona signals fire in known order regardless of who reviews. ~1 hour cost. | Recording is primary; URL + repo support deeper inspection. |
| 12a | Demo Label 1: clean spirits happy path (Old Tom Distillery analogue) | **MVP** | Sarah signal: speed + simplicity. T8 fixture-01. Spirits matches brief example. | Opens demo, <2 s response visible. |
| 12b | Demo Label 2: STONE'S THROW Bourbon brand-name borderline | **MVP** | Dave canonical credibility test. T10 TL;DR explicit: must be in first 3. T8 fixture-02. | Establishes rule-vs-AI separation early. |
| 12c | Demo Label 3: Title-case "Government Warning" fail | **MVP** | Jenny stated case verbatim: "I caught one last month where they used 'Government Warning' in title case instead of all caps. Rejected." T8 fixture-03. | Establishes reason-code precision + CFR citation chain. |
| 13a | Failure-mode in 5-min cut: needs-better-photo (Stage 4) + 1 override moment (Stage 6, ABV out-of-tolerance) | **MVP** | DP6 honest failure modes. Dave override <3 keystrokes. T8 fixtures 04 + 06. | Stages 4 + 6. |
| 13b | Network-failure recovery / orchestrator outage demo | **Stretch** | T8 Stage 7 + pre-mortem A-1. Powerful but eats 45 s; trim to keep 5-min target. | Available on URL; mentioned in README. |
| 13c | Calibration / supervisor view (override → calibration data) | **Stretch** | T8 Stage 6 supervisor heat-map. Strong governance signal but production-stage. NIST AI RMF GOVERN-1.5. | Not in 5-min cut. |

---

## D-010 — MVP scope

**Status:** Accepted
**Date:** 2026-04-30
**Supersedes:** None. Refines D-003.

### Context

Time-boxed take-home with three persona signals to hit (Sarah / Dave / Jenny per D-001) and a brief that explicitly prefers "working core … over ambitious but incomplete." Need a single, defensible scope cut before code starts.

### Decision

MVP is defined by the table above. Summary:

- **In:** all three classes (wine ≥7%, spirits, malt) at the **7 common fields** (brand, class/type, ABV, net contents, bottler name+address, country of origin, government warning); caps + bold detection on the warning header; brand-name fuzzy match; ABV tolerance per D-006; needs-better-photo as first-class disposition; batch upload with k=2–3 lookahead.
- **Stretch (next cheapest first):** spirits depth (class/type vs. §5 SoI), font-size compliance, wine depth (vintage / AVA / sulfite), bulk-results dashboard, auto-send applicant message, network-failure recovery polish, supervisor calibration view.
- **Out:** conditional fields (sulfite, organic, allergen, cochineal); AVA whitelist enforcement at MVP (it's a wine-only conditional rule, lifts in with the wine stretch pack); allowable-revisions check (different problem domain — post-approval change auditing, not label-vs-application verification).

### Override of session candidate

Rule-pack depth pivot from wine to **spirits**. Brief example is spirits; Parts 5/7 are post-modernization stable (T1 §0); Part 4 is at renumbering risk if T.D. TTB-202 issues during 2026 (T1 §12.2); D-006 already authored against spirits.

### Rationale

- Every MVP feature corresponds to either a Hard requirement or a named persona signal in the brief or T10. Nothing speculative is in.
- The 7-field cut covers Sarah's "essentially data entry verification" workload and matches the brief's "Additional Context" verbatim list.
- Caps **and** bold are both MVP because Jenny named both in the same breath; T1 §3 grounds both in 27 CFR §16.22(a)(2).
- Needs-better-photo is MVP not stretch because Jenny explicitly described the gap ("if an agent can't read the label they just reject it"); a calibrated "I don't know" is also a stronger trust signal than a confident guess (Buçinca et al. CSCW 2021, cited in T8).
- Allowable-revisions is out — it's a TTB-internal post-approval audit, not what the brief is asking us to build.

### Alternatives considered

- Spirits-only deep dive → narrower; fails strong-bias requirement for three-class coverage.
- All three classes deep → blows the time budget; brief warns against this.
- Wine for depth (the original session candidate) → rejected per override above.

### Consequences

- T3 rule-pack ships with `policy: spirits.deep` flagged for one validator (class/type vs. SoI as MVP-light "name the class") and stubs only for `wine.deep` / `malt.deep`.
- T9 test corpus must cover all three classes at common-field level.

---

## D-011 — Demo shape

**Status:** Accepted
**Date:** 2026-04-30
**Supersedes:** None. Implements T8 Q8.8 with one cut for time.

### Context

Reviewer time is finite; T10 TL;DR identifies first-30-seconds as the leverage point; T10 pre-mortem #1 names cold-start past 5 s as the top trust risk; T8 designed a 7-stage path to ~7 minutes core + 2 buffer. Need to commit to length, delivery channel, and label order.

### Decision

**1. Length: 5 minutes** for the recorded walkthrough. Six T8 stages compressed by cutting Stage 7 (network-failure recovery) from the recording. Stages: clean spirits pass → STONE'S THROW → title-case warning → needs-better-photo → batch (50 labels) → ABV override.

**2. Delivery channels (all three):**

- Source repo + README (brief deliverable #1).
- Deployed URL, public-readable, no auth gymnastics — full 7-stage path including network-failure recovery is reachable here (brief deliverable #2; refines `01-requirements.md` Medium bias `[INFRA]`).
- 5-minute recorded walkthrough (Loom or equivalent), linked from README. Added because the reviewer may not personally be Sarah / Dave / Jenny; the recording guarantees signals fire in the right order.

**3. Live vs. cached: Hybrid.** Live deployed URL with (a) pre-warmed orchestrator (run fixture-01 once at T-5 minutes pre-recording, T8 §"Demo failure-recovery" item 1) and (b) **LLM responses cached for the six demo fixtures**, narrated transparently as "we cached the LLM call for the demo fixtures so the walkthrough is reproducible — the orchestration and rule engine run live." Mitigates T10 pre-mortem #1 without lying.

**4. First three labels (must-have ordering):**

- **L1 — Clean spirits pass** (T8 fixture-01). Hits Sarah's speed + simplicity in <2 s.
- **L2 — STONE'S THROW Bourbon borderline** (T8 fixture-02). Hits Dave's nuance + rule/AI separation + override <3 keystrokes. T10 TL;DR explicitly requires this in the first three.
- **L3 — Title-case "Government Warning" fail** (T8 fixture-03). Hits Jenny's stated case (verbatim from her transcript) + reason-code precision + CFR §16.22(a)(2) chain.

**5. Failure-mode demo:** Yes in the 5-min cut — needs-better-photo (Stage 4) **and** override moment (Stage 6 ABV out-of-tolerance, +0.7 pp delta). No to network-failure (cut to deployed-URL-only). **Not** happy paths only — three of six fixtures show non-pass dispositions.

### Rationale

- 5 minutes respects Sarah's stated time scarcity ("running late from my daughter's rehearsal") and the brief's "time-constrained" framing while preserving every persona signal.
- Recording + deployed URL + repo is strictly additive over the brief's stated deliverables — no deletions, one addition (~1 hour cost).
- Caching the LLM step but running everything else live is the honest hybrid: real OCR, real rule engine, real keyboard interaction; only the LLM paraphrase is cached. Disclosing this in narration aligns with D-007 (reasoning transparency) and DP2 (rule-first, LLM-secondary).
- L1 / L2 / L3 ordering is the smallest sequence that hits all three personas. STONE'S THROW lands at L2 because Dave's signal is the highest-leverage credibility test (T10 TL;DR).
- Including failure modes in the recording makes calibrated uncertainty (DP3, DP6) a visible feature, not a footnote. Bansal et al. CHI 2021 and Buçinca et al. CSCW 2021 (cited in T8) argue this directly.

### Alternatives considered

- 90-second demo → fits one persona signal at most; loses Jenny entirely; insufficient for take-home grading.
- 10-minute demo → exceeds Sarah's time scarcity; dilutes the first-30-seconds leverage point.
- Pre-cached / canned video only → fails the brief's deployed-URL deliverable.
- Repo + README only → submits 0% of the demo signal; T10 pre-mortem #1 + the prior vendor disaster context make a live URL essential.
- Happy-path-only demo → leaves Jenny's needs-better-photo signal on the floor; weakens DP6.

### Consequences

- Need 6 demo fixtures (T8 §"Test fixtures required").
- Need a 60-second pre-warm script.
- Need cached-LLM responses checked into a `demo/cached/` directory with explicit cache-key matching.
- README needs a "How to run the demo locally" section.

---

## D-012 — Brand-match policy

**Status:** Accepted
**Date:** 2026-04-30
**Refines:** D-005 (per-field matcher policies).

### Context

Brand-name match is the canonical Dave credibility test (STONE'S THROW vs. Stone's Throw, T10 Q10.5 + TL;DR) and the highest-leverage persona signal in the demo. D-005 already says each validator declares its own policy. This ADR pins the brand validator's policy concretely so the rule pack doesn't drift.

### Decision

Brand-name field uses a **two-stage policy**:

**1. Stage A — Normalized exact match.** Strip leading/trailing whitespace; collapse internal whitespace; Unicode NFKC; case-fold; strip ASCII apostrophe variants (`'`, `'`, `'`). If equal → **pass**.

**2. Stage B — Bounded fuzzy match.** Compute Jaro-Winkler similarity between application brand and OCR brand (raw, before Stage A normalization).

- **≥ 0.95 →** `BRAND_NAME.MATCH.NORMALIZED_DIFFERENCE` — pass with note explaining the normalization that fired (caps, punctuation, whitespace).
- **0.85–0.94 inclusive →** `BRAND_NAME.MISMATCH.NEEDS_REVIEW` — needs-review disposition, surfaced with both strings highlighted, similarity score visible to the agent, and `O` (override) one keystroke away (T8 IP-Override).
- **< 0.85 →** `BRAND_NAME.MISMATCH.FAIL` — fail with both strings shown.

**3. Reason-code grammar** follows D-007's `BIN.SUB.SPECIFIC[.QUALIFIER]` (T8 reference).

**4. The LLM's role is paraphrase only** — it generates a human-readable explanation of which Stage A normalization fired, never the disposition (D-002 / DP2). The numeric similarity, threshold, and disposition all come from the rule engine.

### Worked examples (canonical demo fixtures)

- `"STONE'S THROW"` vs. `"Stone's Throw"` → Stage A normalizes both to `stones throw` → exact match → **pass** with `NORMALIZED_DIFFERENCE` note ("differ only in capitalization"). This is the right demo outcome: Dave's case lands as **pass**, not needs-review.
- `"Old Tom Distillery"` vs. `"Old Tom"` → Stage A no match; Stage B Jaro-Winkler ≈ 0.88 → **needs-review** with both strings shown.
- `"Old Tom Distillery"` vs. `"Old Bull Distillery"` → Stage B ≈ 0.82 → **fail**.

### Threshold provenance

Jaro-Winkler 0.85 / 0.95 are starting points calibrated against Dave's STONE'S THROW case (which must pass cleanly via Stage A) and conservative public-corpus heuristics (TTB Public COLA Registry brand-name variants per T1 §11). Tunable in the rule pack; not constants in code (per D-005). T9 will exercise both thresholds against the test corpus.

### Rationale

- Two-stage matters: Stage A handles the **canonical** Dave case as a clean pass (which is the right answer — they really are the same brand). Stage B handles the genuinely uncertain cases without forcing Dave to override on something the system should recognize as obviously fine.
- Similarity thresholds in the rule pack (not code) means D-005 stays honored and a non-engineer can tune them.
- The LLM paraphrase being subordinate to the rule's verdict is the visible trust lever Dave will judge by (T8 DP2). Rule-first, LLM-secondary, throughout.
- Public COLA registry confirms brand-name capitalization variance is rampant, so Stage A's case+punctuation normalization is the right scope — nothing more aggressive (e.g., we do **not** ignore word-order differences or strip "Distillery" / "Winery" suffixes; those changes need agent judgment).

### Alternatives considered

- Single-threshold fuzzy (e.g., Jaro-Winkler ≥ 0.9 → pass) → fires `pass` on STONE'S THROW with low confidence instead of `pass` with high confidence + clear normalization explanation. Worse demo, worse audit trail.
- LLM-as-decider for borderline cases → violates D-002 / D-007; non-deterministic; not auditable.
- Strict equality only → forces Dave to override on every capitalization variant, which is exactly the friction his transcript warns against ("just don't make my life harder").
- Aggressive normalization (Levenshtein with stemming, suffix-stripping) → fails on real cases like `"Stone's Throw Vineyards"` vs. `"Stone's Throw Distillery"` which are distinct entities.

### Consequences

- T3 rule pack adds `brand_name.match` validator with `policy: two_stage_jw`, params `{stage_a_normalize: [whitespace, nfkc, case, apostrophes], stage_b_pass: 0.95, stage_b_review: 0.85}`.
- T9 test corpus includes at minimum: 3 Stage A pass cases, 3 Stage B pass cases (0.95–0.99), 3 needs-review cases (0.85–0.94), 3 fail cases (<0.85).
- Reason-code namespace `BRAND_NAME.*` is reserved for this validator.
- Demo fixture-02 (STONE'S THROW Bourbon) wires in with Stage A passing it cleanly; the demo narration becomes "the rule engine recognized this as a normalized match — capitalization difference only — and the LLM paraphrased the explanation. The agent didn't have to override anything." That's a stronger Dave-signal than "the rule said borderline but the AI thinks it's fine," which T8 Stage 2 currently shows. **Recommend updating T8 Stage 2 narration accordingly.**

---

*End of Session 2 commitment. No architecture or stack questions opened.*