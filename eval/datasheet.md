# Eval Corpus Datasheet (Gebru et al. 2021)

## §1 Motivation
Why was this corpus created? — To gate the macro-F1 ≥ 0.70 AC of the TTB Label
Verification prototype (PRD v0.6 §8.4) and to surface per-rule recall on
government-health-warning rules (FR-200 through FR-205).

## §2 Composition
**Specification (PRD §9.1, D-025).** ~50 labels: spirits 30–40%, wine 30–40%, malt 20–30%; ≥10 borderline-band labels; **real-image floor ≥70% (TTB Public COLA Registry CC0 + PACER/CourtListener exhibits)**, synthetic share ≤30% as supplement only. See `manifest.jsonl` for the full enumeration.

**Actual shipped state (2026-05-05 retrospective per D-023 supersession).** The shipped manifest carries 6 PIL-text-on-white synthetic fixtures (FIX-01..FIX-04, FIX-06, FIX-07) plus 14 placeholder `cola-*` rows whose images were never sourced from the Registry; `eval/harness.py:run_subset()` silently skips the 14 unfilled rows. The README §Trade-offs macro-F1 numbers (live = 0.19, replay = 0.41) are computed against the 6 FIX fixtures only. **The shipped corpus does not meet the §2 specification** — 0% real, 100% synthetic, with 100% of the synthetics failing the PRD §9.1.4 realism bar (PIL `ImageFont.load_default()` text on a pure-white canvas). This gap is acknowledged in D-023 retrospective and superseded by D-025; future iterations follow PRD §9.1.1's mandatory sourcing checklist.

## §3 Collection process
**Real-first ordering per D-025 / PRD §9.1.1.** TTB Public COLA Registry is the canonical primary source (T9 §3, T13 §1.0; CC0-licensed). Per-record retrieval uses the URL pattern `viewColaDetails.do?action=publicDisplaySearchBasic&ttbid={14-char-ttbid}`; images are stored under `fixtures/_corpus/cola-{ttbid}/`. Negative-class entries for brand and geographic-claim rules are sourced from PACER / CourtListener litigation exhibits (T13 §1.6). Borderline-band entries apply controlled degradation (mild blur, glare, JPEG compression, perspective transform) to Registry images and carry `provenance.source = synthetic-derived-from-cola-{ttbid}@{script-sha}` — preserving CC0 lineage and verifiable ground truth. Pure-synthetic supplements (capped at ≤30% per D-023; only after real-first sourcing has been attempted per D-025) must clear PRD §9.1.4 — label-shaped renders with paper/cream stock, type hierarchy, and a frame; never plain text on white. The v0.1–v0.6 `scripts/build_synthetic_fixture*.py` outputs are flagged as the canonical anti-pattern in PRD §9.1.5.

## §4 Preprocessing
None at corpus level — fixtures are stored at the resolution they are evaluated
against. Quality-degradation fixtures (04, 07) carry their degradation in the
committed PNG. **Note (2026-05-05):** the v0.1–v0.6 fixtures are 200×200 to 480×480 px — too small for either a reviewer to read or for `gpt-4o-2024-08-06` to OCR reliably (4/6 fixtures route to `ENGINE.EXTRACTION.UNAVAILABLE` and force `needs_review` on the live stack per README §Trade-offs). The PRD §9.1.4 realism bar specifies ≥600×900 px for new synthetic work; Registry images are typically 600+ DPI vector-derived and exceed this floor naturally.

## §5 Uses
Eval harness only. Not training data; the system has no learnable parameters
beyond rule-pack thresholds (which are tuned out-of-band per PRD §3.2 v0.3
stretch automated re-calibration).

## §6 Distribution
The corpus ships with the repository under `eval/manifest.jsonl` and the
`fixtures/` tree.

## §7 Maintenance
Owner: project team. Updates triggered by rule-pack version bumps or
LLM_MODEL_SNAPSHOT changes; see `scripts/regenerate_fixtures.py` (T8).
