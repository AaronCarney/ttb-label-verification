# Decisions Log — TTB Label Verification Prototype

**Status:** LIVING DOCUMENT — concise master index
**Last updated:** 2026-05-04

This file is the master ADR index. Each entry is one line: identifier, date,
title, and a pointer to the location of the full ADR body. Detailed bodies live
in:

- [`decisions-extended.md`](decisions-extended.md) — D-001..D-009, D-021..D-023, D-DEPLOY-001..004
- [`research/S2-output.md`](research/S2-output.md) — D-010..D-012 (MVP scope, demo shape, brand-match policy)
- [`research/S3-output.md`](research/S3-output.md) — D-013..D-016 (stack choice, rule format, deployment mode, local model serving)
- [`ARCHITECTURE.md` §15](ARCHITECTURE.md#15-architecture-decision-records-d-017-through-d-020) — D-017..D-020 (confidence aggregation, audit/telemetry split, eval-route gating, demo-cache regen)

ADR-style: append-only. Supersede with new entries; don't edit history.

---

## Index

| ID | Date | Title | Status | Body |
|---|---|---|---|---|
| D-001 | 2026-04-28 | Stakeholder priority is phase-dependent | Accepted | [extended](decisions-extended.md#d-001--stakeholder-priority-is-phase-dependent) |
| D-002 | 2026-04-28 | Deterministic-first with AI as orchestrator, not decider | Accepted | [extended](decisions-extended.md#d-002--deterministic-first-with-ai-as-orchestrator-not-decider) |
| D-003 | 2026-04-28 | Beverage-class-specific rules deferred to stretch | Accepted | [extended](decisions-extended.md#d-003--beverage-class-specific-rules-deferred-to-stretch) |
| D-004 | 2026-04-28 | Production parity is in design scope | Accepted | [extended](decisions-extended.md#d-004--production-parity-is-in-design-scope) |
| D-005 | 2026-04-28 | Per-field matcher policies | Accepted | [extended](decisions-extended.md#d-005--per-field-matcher-policies) |
| D-006 | 2026-04-28 | ABV check uses regulatory tolerance, not strict equality | Accepted | [extended](decisions-extended.md#d-006--abv-check-uses-regulatory-tolerance-not-strict-equality) |
| D-007 | 2026-04-28 | Rejection reasoning required for every negative disposition | Accepted | [extended](decisions-extended.md#d-007--rejection-reasoning-is-required-for-every-negative-disposition) |
| D-008 | 2026-04-28 | Architecture options carry both economic and policy stories | Accepted | [extended](decisions-extended.md#d-008--architecture-options-must-carry-both-economic-and-policy-stories) |
| D-009 | 2026-04-28 | Adopt federal cost-analysis conventions (A-94 / GAO-20-195G) | Accepted | [extended](decisions-extended.md#d-009--adopt-federal-cost-analysis-conventions-for-the-economic-analysis) |
| D-010 | 2026-04-28 | MVP scope (input/output, fields, classes) | Accepted | [research/S2 §D-010](research/S2-output.md) |
| D-011 | 2026-04-28 | Demo shape (5-min recording, deployed URL, runbook) | Accepted | [research/S2 §D-011](research/S2-output.md) |
| D-012 | 2026-04-28 | Brand-match policy (Stage A normalized exact + Stage B fuzzy) | Accepted | [research/S2 §D-012](research/S2-output.md) |
| D-013 | 2026-04-28 | Application stack: FastAPI + Pydantic v2 + React island + USWDS tokens | Accepted | [research/S3 §D-013](research/S3-output.md) |
| D-014 | 2026-04-28 | Rule data format: real YAML + Pydantic v2 RuleSet + validator registry | Accepted | [research/S3 §D-014](research/S3-output.md) |
| D-015 | 2026-04-28 | Deployment mode: HF Spaces (Docker SDK, cpu-basic), `vision_mode` autodetect | Accepted | [research/S3 §D-015](research/S3-output.md) |
| D-016 | 2026-04-28 | Local model serving framework (Transformers in-process; vLLM as future swap) | Accepted | [research/S3 §D-016](research/S3-output.md) |
| D-017 | 2026-05-02 | Disposition-level confidence aggregation: min, not multiplication | Accepted | [ARCH §15 D-017](ARCHITECTURE.md#d-017--disposition-level-confidence-aggregation-min-not-multiplication) |
| D-018 | 2026-05-02 | Audit trail vs. telemetry split: per-rule duration moves out of audit envelope | Accepted | [ARCH §15 D-018](ARCHITECTURE.md#d-018--audit-trail-vs-telemetry-split-per-rule-duration-moves-out-of-the-audit-envelope) |
| D-019 | 2026-05-02 | Eval-harness gating: `DEV_MODE` env-flag pattern; eval routes compiled out of production | Accepted | [ARCH §15 D-019](ARCHITECTURE.md#d-019--eval-harness-gating-dev_mode-env-flag-pattern-eval-routes-compiled-out-of-production-builds) |
| D-020 | 2026-05-02 | Demo-cache regeneration: explicit, manual, on snapshot-pin drift | Accepted | [ARCH §15 D-020](ARCHITECTURE.md#d-020--demo-cache-regeneration-explicit-manual-on-snapshot-pin-drift) |
| D-021 | 2026-05-03 | Trim local vision and orchestrator scope to prototype tier | Accepted | [extended](decisions-extended.md#d-021--trim-local-vision-and-orchestrator-scope-to-prototype-tier) |
| D-022 | 2026-05-04 | Front the HF Spaces public URL with `ttb.aaroncarney.me` | **Superseded by D-DEPLOY-001** | [extended](decisions-extended.md#d-022--front-the-hf-spaces-public-url-with-ttbaaroncarneyme) |
| D-023 | 2026-05-03 | Eval corpus right-sized to prototype tier (closes OQ-PRD-5) | Accepted | [extended](decisions-extended.md#d-023--eval-corpus-right-sized-to-prototype-tier-closes-oq-prd-5) |
| D-DEPLOY-001 | 2026-05-04 | Default `*.hf.space` URL; no custom domain (supersedes D-022) | Accepted | [extended](decisions-extended.md#d-deploy-001--default-hfspace-url-no-custom-domain) |
| D-DEPLOY-002 | 2026-05-04 | HF account: `Context31415` (not `aaroncarney`) | Accepted | [extended](decisions-extended.md#d-deploy-002--hf-account-context31415-not-aaroncarney) |
| D-DEPLOY-003 | 2026-05-04 | `VISION_MODE=cloud` on the deployed Space | Accepted | [extended](decisions-extended.md#d-deploy-003--vision_modecloud-on-the-deployed-space) |
| D-DEPLOY-004 | 2026-05-04 | Public-readable URL; no auth on the deployed demo (closes OQ-2) | Accepted | [extended](decisions-extended.md#d-deploy-004--public-readable-url-no-auth-on-the-deployed-demo) |

---

## Audit notes (2026-05-04 post-E8 sweep)

- **D-010..D-020** were authored in their respective design docs (S2-output, S3-output, ARCHITECTURE §15) and were never lifted into this index until now. Indexing them here, not duplicating the bodies.
- **D-022 → D-DEPLOY-001 supersession.** Captured same-day; D-022 stays in the log per append-only convention with a `Superseded` status.
- **D-DEPLOY-001..003** ported verbatim from the post-provisioning notes in the E8 L2 draft; rationale is fact-of-the-matter (HF Pro is $9/mo, account is `Context31415`, GPU probe is wasted on cpu-basic).
- **D-DEPLOY-004** formalizes PRD OQ-2 (auth posture). The resolution was inline in ARCH §3 / PRD §10.1 but never ADR-backed.
- **D-023** formalizes the PRD v0.5 → v0.6 eval-corpus right-sizing (full ~50, per-rule ≥1, Krippendorff deferred). The decision was applied via PRD changelog and E8 plan but never written up as an ADR.

### Flagged as ambiguous; not added

These are observable scope decisions that *might* warrant ADRs, but the audit didn't have a clear signal that they're load-bearing enough to formalize. Listed here for the next pass:

1. **Brand-match thresholds (D-012 follow-on).** D-012 names Stage A (normalized exact) and Stage B (Jaro-Winkler 0.85/0.95) but the threshold values themselves drift between ARCH §6.11, the rule pack, and the test fixtures. If they change again, an ADR pinning the values would help.
2. **Audit-record retention boundary (OQ-ARCH-4).** Explicitly preserved as a future-pluggable seam in ARCH §16; the *decision to defer* is captured but the swap-contract semantics (in-memory ring buffer → durable store) isn't ADR-pinned.
3. **`OverrideEntry.reviewer_id` is a stringified UUID, no real identity.** Captured in the E6 plan's risk table as accepted; arguably an ADR-worthy production-trajectory tradeoff but the E6 risk-table line may be sufficient.
4. **Tornado / range-bar visualization choices for the economic analysis (T12).** D-009 mandates federal-convention framing; the specific viz choices are documented in T12 but not ADR-pinned. Probably sub-ADR scope.
5. **Frontend bbox-overlay accessibility decision (SVG over Canvas).** Captured as a tech-stack-table line in ARCH §7 with reasoning; could be lifted into an ADR if the Canvas/Konva alternatives ever come back into view.
6. **Per-rule timeout 250ms vs. whole-eval timeout.** Documented in ARCH §11.1 / S5 §13 / R-1 risk register as the SLA backstop; not ADR-pinned. The number itself is the load-bearing piece if it ever changes.

The audit did not surface any closed PRD `OQ-*` items beyond OQ-2 and OQ-PRD-5 that lacked formalization. OQ-PRD-1 (reviewer identity), OQ-PRD-2 (auto-retry), OQ-PRD-4 (multi-image aggregation), OQ-ARCH-1..4, and OQ-T5-1..10 are all either explicitly deferred-to-stretch (with the deferral itself documented) or research-tier open questions that don't gate MVP behavior.
