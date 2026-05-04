# Decisions Log — TTB Label Verification Prototype

**Status:** LIVING DOCUMENT
**Last updated:** 2026-04-28

Each entry: context → decision → rationale → alternatives considered.
ADR-style: append-only. Supersede with new entries; don't edit history.

---

## D-001 — Stakeholder priority is phase-dependent

**Status:** Accepted
**Date:** 2026-04-28

**Context.** The brief gives us four named stakeholders: Sarah (Deputy Director, sponsor), Marcus (IT admin), Dave (28-year senior agent), Jenny (junior agent). Standard Power/Interest framing puts Sarah on top but undersells Dave's adoption-credibility role and Marcus's gatekeeper role at production stage.

**Decision.** Use phase-dependent priority:

*At prototype/take-home stage:*
1. Sarah — 100% (owns eval, set hard constraints)
2. Dave — 90% (adoption credibility test; his nuance examples are our best test cases)
3. Jenny — 80% (cheap to please, supplies edge cases)
4. Marcus — 70% (explicitly said "for a prototype, just don't do anything crazy")

*At production-procurement stage, order flips:* Marcus and the CIO above him become gatekeepers; FedRAMP, ATO, and PII review dominate; Dave's informal influence matters less.

**Rationale.** The take-home is graded by Sarah's team, so Sarah's stated requirements dominate scoring. Dave's nuance points are the highest-leverage attention-to-detail signals we can demonstrate. Marcus's constraints don't bind the prototype but bind any production conversation.

**Alternatives considered.**
- Treat all stakeholders equally → loses signal about what's actually graded.
- Pure Power/Interest → underweights Dave's legitimacy (28 years of domain authority) and overweights Marcus at the wrong phase.

---

## D-002 — Deterministic-first with AI as orchestrator, not decider

**Status:** Accepted
**Date:** 2026-04-28

**Context.** Most label verification is rule-matching against fixed regulations (27 CFR Parts 4, 5, 7, 16). Some parts require judgment (fuzzy brand match, OCR ambiguity). A naive "let the LLM do everything" design would be slow, non-deterministic, and untrustworthy in a regulatory context.

**Decision.** Deterministic rule core does all rule evaluation. AI orchestrates: routes to the right validators, resolves OCR/judgment ambiguity, formats reasoning. AI does not decide pass/fail.

**Rationale.**
- Determinism is auditable. Regulators need to be able to point to exactly why something was rejected.
- Speed: deterministic checks are fast; the 5s SLA leaves little budget for multi-step LLM reasoning.
- Maintainability: rule changes in CFR translate to validator changes, not prompt rewrites.
- Honesty about what AI is good at vs. what it's not.

**Alternatives considered.**
- Full LLM pipeline → fails on speed, auditability, and trust.
- Pure deterministic with no AI → fails on fuzzy matching and OCR cleanup.

---

## D-003 — Beverage-class-specific rules deferred to stretch

**Status:** Accepted
**Date:** 2026-04-28

**Context.** TTB rules vary substantially by beverage class (vintage statements for wine, age statements for spirits, etc.). Fully implementing all three classes' rule sets is large.

**Decision.** Implement common-fields verification across all three classes. Class-specific validation (vintage, age statements, appellations, etc.) is stretch.

**Rationale.** "Confirm the general system works first." Brand name, ABV, net contents, and government warning are the high-value common cases that cover most of the actual matching workload Sarah described.

**Alternatives considered.**
- Pick one class (spirits) and go deep → narrower, but less defensible against the brief's regulatory scope.
- Full coverage of all three → too large for time-boxed prototype.

---

## D-004 — Production parity is in design scope

**Status:** Accepted
**Date:** 2026-04-28

**Context.** User raised that the federal context will not permit much cloud inference at production. The prior vendor pilot reportedly broke against the agency firewall. Even though the brief calls this a prototype, design choices made now constrain what production looks like.

**Decision.** Design as if cloud inference is allowed for the prototype but architecturally substitutable. Wrap OCR/vision behind an interface. Avoid hard dependencies on cloud-only patterns. Document this constraint in the README.

**Rationale.** Cheap now, expensive later. Refactoring an embedded vendor SDK out of a production codebase is a major undertaking; designing the seam now costs almost nothing. Future research (see Research doc) will identify on-prem inference options.

**Alternatives considered.**
- Build for cloud only, refactor later → commits us to a path the agency may not accept.
- Build for on-prem now → slows prototype, may not even be feasible in take-home time.

---

## D-005 — Per-field matcher policies

**Status:** Accepted
**Date:** 2026-04-28

**Context.** Different fields require different match strictness. The government warning must be exact; brand names must allow case/punctuation variants; ABV must allow regulatory tolerance.

**Decision.** Each validator declares its own match policy: `exact`, `fuzzy`, `tolerance`, etc. Policies are explicit in the rule definition, not buried in code.

**Rationale.** Makes the rule set legible to non-engineers. Allows rule changes without code changes (eventually). Honors Dave's nuance point (STONE'S THROW) and Jenny's strictness point (warning exact match) as separate field configurations rather than as a global setting.

**Alternatives considered.**
- Global similarity threshold → fails the strictness-vs-tolerance split.
- Hard-coded per-field logic → not maintainable.

---

## D-006 — ABV check uses regulatory tolerance, not strict equality

**Status:** Accepted
**Date:** 2026-04-28

**Context.** The 2020 modernization rule (T.D. TTB-158) implemented a ±0.3 percentage-point tolerance on distilled spirits ABV statements. Wine and malt have different tolerances. A naive `==` check would produce false rejections that any agent would override.

**Decision.** ABV validator is tolerance-aware and class-specific. Tolerance values come from the rule set, not constants in code.

**Rationale.** Demonstrates regulatory literacy. Reduces false-positive rejections. Builds trust with senior agents (Dave) who will spot regulatory ignorance instantly.

**Open.** Need exact tolerance values for wine and malt (research item).

---

## D-007 — Rejection reasoning is required for every negative disposition

**Status:** Accepted
**Date:** 2026-04-28

**Context.** Stakeholder feedback clarified that the human is in the loop on every decision. A rejection without reasoning forces the agent to redo the work; it provides no value.

**Decision.** Every fail or needs-review disposition must include:
- Field name(s) that triggered the disposition
- The specific rule check that failed
- Evidence (extracted text, image region, expected value)
- Citation to the underlying regulation where applicable

**Rationale.** Makes the tool genuinely augmentative rather than another thing to fight with (Dave's concern). Aligns with the regulatory audit trail any production version would require.

**Alternatives considered.**
- Binary pass/fail only → low-value, won't be adopted.
- Reasoning only on fail, not on needs-review → loses the triage utility for agents.

---

## D-008 — Architecture options must carry both economic and policy stories

**Status:** Accepted
**Date:** 2026-04-28

**Context.** Earlier framing (D-002, D-004) treated architectural options primarily as engineering trade-offs with production-parity as a separate concern. User feedback clarified that every architectural option must additionally carry: (a) a defensible economic story (TCO at scale, labor savings model, sensitivity analysis) and (b) a defensible federal-policy story (what tier of authorization it requires, what compliance overhead it imposes). These aren't decoration on the engineering choice — they're constraints that can flip a recommendation.

**Decision.** Every architectural option evaluated downstream (T4 OCR/vision options, T5 LLM options, hybrid configurations) must be cross-referenced against:
- A staged, range-based economic model with explicit drivers and sensitivity analysis (T11)
- A policy-gradation map showing allowability tier, authorization timeline, and compliance overhead (T7)

The headline recommendation in the README's trade-off section combines both (synthesis question X-7).

**Rationale.** Federal IT investments fail more often on policy and cost grounds than on technical grounds. A technically clean architecture that requires a 24-month FedRAMP path or a vendor-locked subscription with double-digit annual price increases is not actually deployable. Surfacing both dimensions early forces the architecture choice to be defensible holistically.

**Alternatives considered.**
- Treat economic and policy as downstream review concerns after architecture is locked → standard pattern, fails because by then the architecture has assumed away constraints it doesn't know about.
- Treat them as two separate analyses presented in parallel → loses the cross-cutting insight that recommendations flip at specific cost-policy interaction points.

**Consequences.**
- Adds T11 and T12 to the research plan; adds X-7 to the cross-topic synthesis registry.
- Pushes T7 to refocus from compliance checklist to policy gradation.
- Creates the requirement that T11 produces ranges and sensitivity analyses, not point estimates.

---

## D-021 — Trim local vision and orchestrator scope to prototype tier

**Status:** Accepted
**Date:** 2026-05-03

**Context.** ARCH §4.2.3 originally specified a four-model local vision pipeline (PaddleOCR + Florence-2-large + GPT-4o-on-crop tiebreaker + Qwen2.5-VL-7B-AWQ fallback) and §4.2.6 specified three orchestrator implementations (`OpenAIStrictOrchestrator` validated default, `AnthropicStrictOrchestrator` skeleton, `VllmXgrammarOrchestrator` skeleton). A spec-vs-L1 review flagged this as over-engineered for prototype tier: the cloud path is the only validated default, the local path exists to prove D-004 substitutability holds, and the seam is provably substitutable with one local impl + one alternate-provider skeleton.

**Decision.** Reduce shipped impls to:
- **Vision (local mode):** PaddleOCR PP-OCRv5 (GPU) + GPT-4o-on-crop tiebreaker only. Florence-2-large and Qwen2.5-VL-7B-AWQ are dropped from MVP.
- **Orchestrator:** `OpenAIStrictOrchestrator` (validated default) + `AnthropicStrictOrchestrator` (swap-path skeleton) only. `VllmXgrammarOrchestrator` is dropped from MVP.

The federal on-prem trajectory (BR-015 / BR-016 / NFR-PORT-001/002) is preserved by the existing seams: `VisionExtractor` Protocol and `Orchestrator` ABC stay, the local vision impl still proves the seam, and a future vLLM swap-in is a new module against the same ABC — no rework. The Anthropic skeleton is sufficient evidence the orchestrator seam is provider-agnostic.

**Rationale.**
- **Calendar.** Florence-2 + Qwen2.5-VL together require ~9 GB GPU resident set, HuggingFace Transformers + accelerate + bitsandbytes, ~2–3 min `uv sync --extra gpu` time. They contribute no validated behavior to the prototype demo (cloud is the validated default per ARCH §4.2.6); the local path's value is **proving the seam holds**, which one local impl does.
- **Reviewer cognitive load.** A skeleton orchestrator the reviewer never sees executed is decoration; one is sufficient to prove the seam.
- **Substitutability proof unchanged.** D-004 is satisfied by ≥1 cloud impl + ≥1 local impl behind the same Protocol. vLLM's value is "production-trajectory federal on-prem" which is already documented in ARCH §9.4 as informational, not committed.
- **No FR/NFR regression.** No PRD FR or NFR cites Florence-2, Qwen, or vLLM by name; all are ARCH-tier choices.

**Alternatives considered.**
- **Keep all three orchestrator impls and four-model vision stack.** Rejected — ARCH §4.2.6 already concedes Anthropic and vLLM are skeletons; shipping two skeletons is no more substitutable than shipping one.
- **Drop the local vision path entirely; cloud-only.** Rejected — would forfeit the on-prem-trajectory proof that BR-015 / NFR-PORT-001 demands.
- **Cut Anthropic instead of vLLM.** Rejected — Anthropic's `tool_use` strict mode is a closer analogue to OpenAI Structured Outputs and is the more legible swap-path for a take-home reviewer; vLLM's value is federal-trajectory-only.

**Consequences.**
- ARCH §4.2.3, §4.2.6, §6.9 (CallRecord stage enum), §7 (tech-stack table), §8.1, §8.2, §9.1, §9.4, §11.5, §14.1, §19.3 update to reflect the trimmed surface.
- L1 epoch-3 / epoch-4 sub-files update; coverage matrix in L1 §11 unchanged.
- `pyproject.toml` `[gpu]` extra drops `transformers`, `accelerate`, `bitsandbytes`; `[vllm]` extra is removed.
- Future re-introduction of any dropped backend is a new ADR, a new module against the existing seam, and a new validation pass — no architectural change.

---

## D-009 — Adopt federal cost-analysis conventions for the economic analysis

**Status:** Accepted
**Date:** 2026-04-28

**Context.** Federal audiences read cost analyses against specific established conventions: OMB Circular A-94 (Nov 2023 revision) for benefit-cost methodology, GAO-20-195G (Mar 2020) for cost-estimate quality criteria, and OMB Circular A-11 / Exhibit 300 for IT-investment business case format. These aren't optional norms; A-94 is mandatory for analyses submitted to OMB, and GAO-20-195G is the audit standard. Producing economic analysis in our own ad-hoc format risks reading as amateur to anyone who knows the standards.

**Decision.** T11's economic analysis will follow federal conventions:
- Cost-effectiveness analysis (CEA) framing per A-94 — chosen over BCA because benefits are partly mandated and alternatives differ mainly in cost
- Discount rate from current A-94 Appendix C (do not invent rates)
- GAO-20-195G's four pillars (comprehensive, well-documented, accurate, credible) used as section/assessment language
- Work breakdown structure (WBS) per GAO step 4 organizing per-option costing
- Ground rules and assumptions (GR&A) section explicitly labeled
- Sensitivity analysis (GAO step 8) and risk/uncertainty analysis (GAO step 9) as separate, distinguishable components
- Cost figures presented as ranges with confidence percentiles, not point estimates
- Real (constant-dollar) figures by default
- Performance measures outcome-quantified per Exhibit 300 expectations
- Citations to A-94 sections and GAO-20-195G where conventions are being followed

The conventions are captured in `R0-federal-cost-conventions.md` as a reference doc shared by T7, T11, and T12.

**Rationale.** Three reasons. First, credibility — federal audiences recognize the conventions and read deviation as either ignorance or willfulness, neither helpful. Second, defensibility — analyses structured to A-94 / GAO standards withstand later scrutiny better than ad-hoc ones. Third, downstream optionality — if the prototype advances to real procurement, the analysis can be lifted into Exhibit 300 with minimal restructuring rather than rewritten.

**Alternatives considered.**
- General TCO analysis using business conventions → cheaper to produce; reads weaker to federal audiences.
- Full Exhibit 300 mock-up → overkill for a take-home; signals over-engineering.
- Adopt selected pieces (discount rate, sensitivity) without structural alignment → inconsistent; reads as someone who half-knows the conventions, which is worse than not knowing them.

**Consequences.**
- T11 structurally maps to A-94 sections and GAO steps without losing its existing five-stage organization.
- T12's visualization choices anchor on federal convention (tornado diagrams, range-bars, density-tables-over-dashboards).
- README and any deliverables to the take-home reviewer cite A-94 and GAO-20-195G where they ground methodology choices.
- The discount-rate question is settled, not researchable — saves T11 effort.

## D-022 — Front the HF Spaces public URL with `ttb.aaroncarney.me`

**Status:** Accepted
**Date:** 2026-05-04

**Context.** D-015 named Hugging Face Spaces (Docker SDK, `cpu-basic`) as the public-URL host because the architecture is a long-running FastAPI process with stateful in-memory components (asyncio batch worker per FR-400, ring-buffer `CallRecord`, session-scoped `app.state.batches`) — a poor fit for Vercel Fluid Compute's best-effort instance reuse. D-015 left the reviewer-facing URL as the bare HF subdomain (`<owner>-<space>.hf.space`). The candidate maintains a personal portfolio at `aaroncarney.me` (Cloudflare DNS, separate Vercel-hosted Next.js site); a hostname under that domain is preferable for reviewer optics without changing the runtime.

**Decision.** The canonical public URL for the take-home prototype is `https://ttb.aaroncarney.me`. It is implemented as:

- **Cloudflare DNS:** `CNAME ttb → aaroncarney-ttb-label.hf.space`, proxy status **DNS only** (grey cloud). DNS-only is required so HF can provision its own Let's Encrypt cert at the HF edge; orange-cloud would interpose a Cloudflare cert and break HF's challenge.
- **HF Space → Settings → Custom Domain:** `ttb.aaroncarney.me`. HF auto-issues + auto-renews the Let's Encrypt cert.
- **Fallback:** the HF subdomain `aaroncarney-ttb-label.hf.space` remains reachable for diagnostics.

Cloudflare performs no TLS termination, no caching, no WAF — it is a dumb DNS pointer. TLS is end-to-end HF (NFR-SEC-001).

**Rationale.**
- **Optics.** A take-home URL on the candidate's own domain reads as a deliberate deliverable; the bare HF subdomain reads as scratch infrastructure.
- **No runtime change.** The seam is DNS, not the host. Architecture posture (D-015), env vars, secrets, container image, and reviewer profiles are all unchanged.
- **No new vendors.** Cloudflare and the apex domain already exist for the candidate's portfolio; this is one CNAME row, not a new account.
- **TLS owner is unchanged.** HF still owns the cert; the prototype process still runs HTTP behind the HF edge per ARCH §13. NFR-SEC-001 unaffected.

**Alternatives considered.**
- **Deploy on Vercel under `aaroncarney.me`** (or its subdomain, replacing HF entirely) → Rejected. Vercel Fluid Compute supports Python, but instance reuse across requests is best-effort, not guaranteed. The FR-400 batch worker holds asyncio queue + per-batch state across multiple requests in a single user's session; losing that state mid-batch is a contract violation, not a perf regression. Also forfeits the A10G-small GPU upgrade escape hatch (ARCH §9.3).
- **Cloudflare proxy (orange cloud) instead of DNS-only** → Rejected. Would require origin-cert provisioning between Cloudflare and HF (HF doesn't accept arbitrary client certs at its edge), or full-strict TLS with Cloudflare-issued cert. Adds a moving part, breaks HF's automatic Let's Encrypt renewal, and Cloudflare caching/WAF in front of an SSE batch stream is a known footgun (long-lived connections, response buffering).
- **Bare HF subdomain only** → Rejected per Decision rationale above.

**Consequences.**
- ARCH §8 stack-table deployment row, ARCH §9.2, PRD §10.1, README Profile A, and the E8 deploy plan §2.6 + T-30 runbook step name `ttb.aaroncarney.me` as canonical.
- The candidate must perform the one-time DNS + HF custom-domain setup before the E8 deployment-smoke step (`tests/test_deploy_healthz.py`) is meaningful against the canonical URL. The smoke test stays gated by the `TTB_DEPLOY_URL` env var so local runs are unaffected.
- If the HF Space is ever recreated under a different subdomain, the Cloudflare CNAME target updates; the canonical URL does not. This is the durability win of the indirection.
- No change to `.env.example`, no change to ARCH §12 env-var inventory, no change to reviewer profiles B/C boot commands.

