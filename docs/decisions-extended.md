# Decisions Log — Extended (Full ADR Bodies)

**Status:** LIVING DOCUMENT
**Last updated:** 2026-05-04

Each entry: context → decision → rationale → alternatives considered.
ADR-style: append-only. Supersede with new entries; don't edit history.

The concise master index lives in [`03-decisions.md`](03-decisions.md). Detailed
bodies for D-010..D-012 live in [`research/S2-output.md`](research/S2-output.md);
D-013..D-016 in [`research/S3-output.md`](research/S3-output.md); D-017..D-020 in
[`ARCHITECTURE.md` §15](ARCHITECTURE.md#15-architecture-decision-records-d-017-through-d-020).

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

---

## D-022 — Front the HF Spaces public URL with `ttb.aaroncarney.me`

**Status:** Superseded by [D-DEPLOY-001](#d-deploy-001--default-hfspace-url-no-custom-domain)
**Date:** 2026-05-04
**Superseded:** 2026-05-04 (same day, after provisioning attempt revealed HF custom domains are Pro-tier-only at $9/mo)

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

**Why superseded.** Provisioning the HF Space on 2026-05-04 surfaced that custom-domain registration on HF Spaces is gated behind the **Pro plan** ($9/mo). The cost-vs-benefit for a one-shot take-home flips against vanity URLs at any non-zero cost. See [D-DEPLOY-001](#d-deploy-001--default-hfspace-url-no-custom-domain) for the replacement decision.

---

## D-DEPLOY-001 — Default `*.hf.space` URL; no custom domain

**Status:** Accepted (supersedes [D-022](#d-022--front-the-hf-spaces-public-url-with-ttbaaroncarneyme))
**Date:** 2026-05-04

**Context.** D-022 (same day) named `https://ttb.aaroncarney.me` as the canonical reviewer URL via a Cloudflare DNS-only CNAME plus an HF custom-domain registration. Provisioning revealed that HF Spaces custom-domain registration is gated behind the **Pro plan** ($9/mo). The candidate's HF account is on the free tier; upgrading is the only path.

**Decision.** Demo runs at `https://context31415-ttb-label.hf.space`. No vanity URL, no Cloudflare proxy in the request path.

**Rejected alternative.** `ttb.aaroncarney.me` via HF custom domain (i.e., D-022 as originally written).

**Rationale.**
- HF custom domains require Pro ($9/mo). Take-home reviewers care about the application, not URL branding. Cost > benefit for a one-shot demo.
- If the project moves to pilot, revisit — the seams are unchanged; flipping back is a one-CNAME, one-HF-setting operation.

**Consequences.**
- Cloudflare CNAME `ttb` → `context31415-ttb-label.hf.space` is currently dangling (live but not wired through HF). Harmless — resolver hits the Space, HF returns 404 for unrecognized Host header. Can be removed with one click in CF UI.
- Reviewer-facing URL string in README, PRD §10.4, ARCHITECTURE §7/§9.2, and the E8 deploy plan must read `https://context31415-ttb-label.hf.space`.
- The `tests/test_deploy_healthz.py` smoke gate (gated by `TTB_DEPLOY_URL`) targets the bare HF URL.

**Alternatives considered.**
- **Pay for HF Pro and keep D-022.** Rejected — $9/mo recurring vs. one-shot reviewer value.
- **Front via Vercel instead.** Rejected for the same architecture-fit reasons D-022 already documented (asyncio batch worker + SSE state vs. Fluid Compute best-effort instance reuse).
- **Deploy elsewhere entirely (fly.io / Railway / Modal).** Rejected — out-of-scope rework for what is now a domain-cosmetic question.

---

## D-DEPLOY-002 — HF account: `Context31415` (not `aaroncarney`)

**Status:** Accepted
**Date:** 2026-05-04

**Context.** Drafts of D-022 and the E8 deploy plan referenced an `aaroncarney`-prefixed Space (e.g., `aaroncarney-ttb-label.hf.space`). The candidate's only active HF identity is `Context31415`; provisioning a separate `aaroncarney` HF account adds an identity and an SSH-key surface for no operational benefit.

**Decision.** Space owned by the `Context31415` HF account. URLs and `git push hf` target reflect this.

**Rationale.** Account in active use; no operational reason to provision a separate `aaroncarney` HF identity. Aligns the deployed-Space URL with where the candidate already operates HF tooling.

**Consequences.**
- Canonical URL string is `https://context31415-ttb-label.hf.space` (cf. D-DEPLOY-001).
- Anywhere the architecture or plan documents read `aaroncarney-ttb-label.hf.space`, the correct string is `context31415-ttb-label.hf.space`.
- HF secrets/variables are managed under the `Context31415` account.

---

## D-DEPLOY-003 — `VISION_MODE=cloud` on the deployed Space

**Status:** Accepted
**Date:** 2026-05-04

**Context.** `.env.example` defaults `VISION_MODE=auto`, which probes `nvidia-smi` at process start and falls back to `cloud` when no GPU is present (D-015). HF Spaces `cpu-basic` has no GPU, so `auto` always falls back — the probe is wasted work and leaves a stack-trace-style log line on every cold start.

**Decision.** HF Space environment variable `VISION_MODE=cloud` (overrides `.env.example` default of `auto`).

**Rationale.**
- Skips the GPU probe entirely; faster cold start.
- No transient log noise on the deployed Space; the deploy log stays signal-only.
- Local profiles (B and C in the README) still default to `auto` via `.env.example`, so reviewer setup is unaffected.

**Consequences.**
- Documented in the HF Space settings (UI + spaces metadata where exposed).
- Reviewer-facing docs do not need to be edited — the override is environment-local.

**Provisioned state at decision time (2026-05-04).**
- HF Space: `Context31415/ttb-label` — public, Docker SDK, cpu-basic
- HF variables: `ORCHESTRATOR_BACKEND=openai`, `LLM_MODEL_SNAPSHOT=gpt-4o-2024-08-06`, `LOOKAHEAD_K=3`, `PROMPT_VERSION=v1`, `VISION_MODE=cloud`
- HF secrets: `OPENAI_API_KEY` (set via UI)
- Cloudflare CNAME: `ttb` → `context31415-ttb-label.hf.space` (DNS-only, dangling per D-DEPLOY-001)
- Custom domain registration on HF Space: **not done** (Pro-gated)

**Deferred work (post-E8).**
1. Decide whether to remove the dangling Cloudflare CNAME or leave it for future pilot reactivation.
2. If E8 ships and the project graduates, port D-DEPLOY-001..003 follow-ups into a new ADR with a "revisit at pilot" trigger.

---

## D-DEPLOY-004 — Public-readable URL; no auth on the deployed demo

**Status:** Accepted (formalizes PRD OQ-2 closure)
**Date:** 2026-05-04 (resolution dated to ARCH §3 commit; ADR formalized post-E8 audit)

**Context.** PRD OQ-2 ("What auth posture should the deployed-URL demo carry — open URL, basic auth, or a shared link with rotating token?") was resolved inline in ARCHITECTURE §3 ("the reviewer arrives via a public-readable URL (PRD OQ-2 prototype-tier resolution)") and PRD §10.1 without a corresponding ADR. The audit on 2026-05-04 flagged this as a non-formalized resolution worth pinning.

**Decision.** The deployed URL is public-readable with no authentication, no basic-auth wall, no token-gated link. The demo serves cached fixtures only by default; reviewer ad-hoc uploads go through the live cloud-vision path with reviewer-supplied test labels (no PII).

**Rationale.**
- **Reviewer friction.** Any auth gymnastics costs the reviewer time and risks demo failure on auth-config mistakes; the take-home is graded on the application, not on deploy hygiene.
- **No real PII.** The fixture corpus and the synthetic labels in `eval/` contain no regulated data; there is nothing to gate.
- **Production-tier different.** Marcus / FedRAMP / ATO conversations require PIV-SAML or equivalent (T7, ARCH §9.4). That posture is documented as production-trajectory; the prototype tier explicitly does not implement it. NFR-SEC-001 (TLS) holds; NFR-SEC-002 (env-var-driven secrets) holds.

**Alternatives considered.**
- **HTTP basic auth.** Rejected — adds friction with zero security benefit (basic auth over HTTPS has no MFA, secret-rotation story, or audit trail).
- **Per-reviewer rotating-link tokens.** Rejected — operational overhead for a one-shot demo; the secret-distribution channel is the same email that already contains the URL.
- **Cloudflare Access (Zero Trust).** Rejected — adds a vendor in the request path (D-DEPLOY-001 explicitly removes Cloudflare from the path); free tier limits and login-flow ergonomics break the click-through reviewer experience.

**Consequences.**
- The deployed URL has no `WWW-Authenticate` requirement; `curl https://context31415-ttb-label.hf.space/healthz` returns 200 anonymously.
- ARCH §3 inline note ("public-readable URL") is now ADR-backed.
- Production-trajectory auth (PIV-SAML or equivalent) remains documented in §9.4 / T7 as informational, not committed.

---

## D-023 — Eval corpus right-sized to prototype tier (closes OQ-PRD-5)

**Status:** Accepted (formalizes PRD v0.6 changelog scope decision); **superseded in part by D-025** on the synthetic-image realism standard and the real-first sourcing ordering. Numeric corpus targets stand; the sourcing-mix half of the "synthetic share ≤30%" line is reframed by D-025 / PRD §9.1.1.
**Date:** 2026-05-03 (PRD v0.6 publication; ADR formalized post-E8 audit on 2026-05-04; partial supersession 2026-05-05).

**Context.** PRD v0.5 specified an eval corpus of ≥250 labels with ≥97 happy-path, ≥20 borderline, and ≥1 case per rule (43+ rules) plus an intra-rater Krippendorff α ≥ 0.7 reliability gate. PRD v0.6 reduced these targets across the board. This was applied via a PRD changelog line and an L1 epoch-8 plan revision, but never written up as an ADR, so the rationale is not durable.

**Decision.** The MVP eval corpus is right-sized to **prototype tier**:
- Full corpus ~50 labels (was ≥250)
- Happy-path ≥10 labels (was ≥97)
- Borderline ≥10 labels (was ≥20)
- Per-rule positive coverage ≥1 (was ≥43; closes OQ-PRD-5)
- Class balance: spirits 30–40%, wine 30–40%, malt 20–30%; synthetic share ≤30% (per D-025: synthetic *supplement*, not substitute; real-image floor ≥70%)
- Krippendorff α ≥ 0.7 intra-rater reliability gate **deferred to pilot phase**
- Macro-F1 ≥ 0.70 MVP gate **held** (not relaxed)

**Rationale.**
- **Calendar.** A 250-label, dual-pass-with-reliability corpus is a multi-week effort by itself; MVP scope is a 7-day take-home.
- **Signal preserved.** macro-F1 ≥ 0.70 against ~50 labels (~25 happy + ~10 borderline + per-rule cases) is enough signal to demonstrate the prototype performs above chance on the rules it claims to implement. The borderline slice exercises the AI-orchestration path specifically.
- **Clean pilot story.** Deferring the Krippendorff gate to pilot phase signals literacy ("we know what production reliability requires") without overcommitting to it ("we won't fake a reliability number on a small corpus").
- **Reviewer cognitive load.** A small, well-curated corpus with a documented datasheet outclasses a large auto-collected corpus with no labeling protocol.

**Alternatives considered.**
- **Hold the v0.5 numbers.** Rejected — calendar-infeasible without producing a labeling-quality compromise that would itself need ADR justification.
- **Drop the eval harness entirely; demo-only scoring.** Rejected — the eval harness is the take-home's headline accuracy claim; removing it forfeits BO-2.
- **Keep the Krippendorff gate at pilot-quality threshold (0.7) on the small corpus.** Rejected — α on a 50-item corpus has wide CIs; a passing α here is not load-bearing.

**Consequences.**
- PRD §9 reflects the new numbers; the eval/datasheet.md captures the labeling protocol.
- E8 plan T-1, T-2, T-3 acceptance criteria align with the right-sized targets.
- Pilot follow-up: re-do Krippendorff α once corpus reaches ≥150 labels with two labelers.

**Post-deadline retrospective (2026-05-05).** D-023's sourcing-mix language was read in execution as "any synthetic-share ≤30% is fine" rather than "real first, then synthetic." What actually shipped: **0 sourced images, 56 PIL-rasterized text-on-white PNGs**, 100% synthetic, with the L2 eval-pipeline manifest carrying 14 placeholder `cola-*` rows whose images were never sourced (the harness silently skips them). The macro-F1 numbers in the README §Trade-offs are computed against the 6 FIX fixtures only. This is a real gap with the BRD §A-1 / OQ-5 framing ("the public COLA Registry is a reasonable test corpus") and with PRD §9.1's listed sources. **D-025 reframes the sourcing ordering so this cannot recur** — real-first is now an ADR-level requirement, the synthetic realism bar is explicit, and PRD §9.1.1 ships a mandatory sourcing checklist that any future iteration must satisfy or explicitly waive in its decisions log.

---

## D-024 — Anthropic backend never run live; skeleton stays as substitutability proof only

**Status:** Accepted
**Date:** 2026-05-04

**Context.** D-021 trimmed orchestrator scope to two implementations: `OpenAIStrictOrchestrator` (validated default) and `AnthropicStrictOrchestrator` (swap-path skeleton). The Anthropic skeleton was retained to demonstrate the `Orchestrator` ABC is provider-agnostic — evidence the seam holds without shipping a second validated backend. ARCH §4.2.6, §11.5, §12.2, §14.1, and `.env.example` all carry copy that implies `ORCHESTRATOR_BACKEND=anthropic` is a real runtime option (just unvalidated). It is not.

**Decision.** This project will never run the Anthropic backend with live credentials. The candidate has no Anthropic API budget and will not acquire one for this take-home. `ORCHESTRATOR_BACKEND=openai` is the only valid runtime setting; `ANTHROPIC_API_KEY` is never set in any environment (local `.env`, HF Space secrets, CI). The `AnthropicStrictOrchestrator` module stays in the repo as **structural** substitutability evidence — its existence + its respx-mocked unit tests (E4) prove the seam is provider-agnostic, with no claim of live operability.

**Rationale.**
- **Honest budget signaling.** Documenting "no Anthropic credits, ever" prevents future planning waves from proposing live-Anthropic verification tasks, eval-corpus runs against Anthropic, dual-backend latency comparisons, or A/B demo paths — none of which can be funded.
- **Seam claim is unaffected.** D-004 / NFR-PORT-001 / NFR-PORT-002 only require that the seam is provably substitutable. Two distinct implementations against the same ABC, plus mocked unit tests for both, satisfy that. Live execution against Anthropic is not part of the evidence chain.
- **Reduces review surface.** Plan reviewers, code reviewers, and demo runbooks should not waste cycles considering the Anthropic path; making "never live" explicit in the decisions log is the cheapest way to retire that consideration permanently.

**Alternatives considered.**
- **Delete the Anthropic skeleton entirely** → Rejected. The skeleton is the cheapest evidence the orchestrator ABC is not OpenAI-coupled; deleting it weakens the substitutability claim that motivated D-021's retention of two impls. Cost-of-keeping is near zero (one module + mocked tests, no runtime dependency).
- **Add a different second backend (e.g., a local llama.cpp orchestrator)** → Rejected. Out of scope for prototype tier; the local-vision path already demonstrates federal on-prem trajectory per ARCH §9.4.
- **Leave the docs ambiguous** → Rejected. Ambiguity here is what causes future planning sessions to repeatedly re-evaluate Anthropic; an explicit "never" is the durable fix.

**Consequences.**
- `.env.example` and ARCH §12.2 env-var inventory annotate `ANTHROPIC_API_KEY` as "never set in this project per D-024"; the row stays in the table because the env var is a real Pydantic Settings field, but the prose changes from "required when …" to "never set; D-024".
- ARCH §4.2.6 + §11.5 keep their existing language about the swap-path skeleton; D-024 adds one sentence reinforcing "skeleton tests stay mocked; no live calls in any environment."
- E5 audit log fields that record `provider: "openai" | "anthropic" | "local.paddleocr"` keep the `anthropic` enum value — it is reachable in unit tests via the mocked skeleton and stays in the wire schema for forward compatibility.
- E8 demo runbook, eval harness, and deployment secrets are OpenAI-only; no plan task may require Anthropic credits as a precondition.
- Future plans that propose any Anthropic-live work must first supersede this decision with a new ADR; planning sessions that surface such proposals should reject them on sight.

---

## D-025 — Real-first sourcing + synthetic-realism standard for the eval corpus and fixture set

**Status:** Accepted (partial supersession of D-023's sourcing-mix language)
**Date:** 2026-05-05

**Context.** D-023 right-sized the eval corpus and capped synthetic share at ≤30%, but did not specify a *sourcing ordering* and did not define *what "synthetic" means visually*. In execution, the gap was filled by inertia: the E3 PIL-text-on-white test stimuli (`scripts/build_synthetic_fixture*.py`) were carried forward through E5 → E7 → E8 as the canonical fixture set, the L2 eval-pipeline manifest's 14 `cola-*` rows were never sourced from the TTB Public COLA Registry, and the eval harness silently skipped those rows via `run_subset()`. The shipped state: **0 sourced images, 56 synthetic PIL-rasterized text-on-white PNGs (6 FIX fixtures + 50 batch-of-50)**, README §Trade-offs macro-F1 numbers computed against 6 FIX fixtures only, no demo image visually distinguishable from raw HTML text.

**Decision.** The sourcing contract is now ordered and the synthetic-realism bar is explicit.

1. **Real-first is mandatory.** The TTB Public COLA Registry (T9 §3, T13 §0.1, §1.0) is the canonical primary source for every tier of this project. Real-image floor is **≥70% of the full eval corpus** with `provenance.source` matching `^cola-` or a litigation-exhibit identifier. Iterations that fall below the floor must explicitly waive the gap in their decisions log, naming which sources were attempted and why they fell short.
2. **Synthetics are supplements, not substitutes.** The ≤30% synthetic share from D-023 stands, but every synthetic asset must clear the realism bar in PRD §9.1.4. Plain text on white using PIL's default bitmap font is **explicitly disallowed** — the v0.1–v0.6 fixture style is a defect, not a fixture (PRD §9.1.5 anti-pattern).
3. **Synthetic provenance is reproducible.** Every synthetic asset carries `provenance.source = synthetic-{slug}@{build-script-sha}`. The build script must produce byte-identical output on re-run (deterministic font hinting, fixed RNG seed). Synthetics derived from a Registry source carry `synthetic-derived-from-cola-{ttbid}@{script-sha}` — preserving CC0 lineage and verifiable ground truth.
4. **Sourcing checklist is mandatory** (PRD §9.1.1). Every iteration that ships an eval corpus or fixture set must record evidence of the five-step ordering: Registry → litigation → degradation-from-Registry → pure-synthetic-supplement → gap-documentation. Skipping any step requires an ADR.

**Rationale.**
- **Honest evaluation.** Macro-F1 against 6 PIL text rasterizations is not evidence the system performs against real labels. Real-first sourcing forces the eval to actually evaluate what the BRD §A-1 / OQ-5 reasoning assumes — that the Registry is the reasonable test corpus.
- **No licensing risk.** The Registry is CC0 (T9 §3). Real-first costs curator hours, not legal review.
- **Reviewer experience.** A reviewer looking at a fixture page should see *a label*. PIL text on white renders as a paragraph, not a label, and it makes the entire UI read as broken. The realism bar in §9.1.4 is the cheapest fix that prevents this from recurring.
- **Auditability.** `synthetic-derived-from-cola-{ttbid}@{sha}` is auditable; `synthetic-acme-distilling` (a hand-named slug pointing nowhere) is not.

**Alternatives considered.**
- **Keep the v0.1–v0.6 synthetic-only mix; document it.** Rejected — documenting "we skipped the primary source" as an accepted state normalizes a defect. The decisions log records *why* gaps exist, but the contract has to require real-first or the next iteration will repeat the failure.
- **Forbid synthetics entirely.** Rejected — the borderline-confidence slice (PRD §9.1) genuinely benefits from controlled degradation that you can't reliably get from natural Registry images. The right answer is degradation-of-Registry-source, not pure-synthetic, but the controlled-degradation path needs to remain available.
- **Set the real-image floor at 100%.** Rejected — same reason. Borderline degradation is a real corpus need; the ≥70% floor leaves room for it without legitimizing pure synthetics.

**Consequences.**
- PRD §9.1 reframed: real-first ordering, ≥70% floor, mandatory sourcing checklist (§9.1.1), synthetic realism standard (§9.1.4), explicit anti-pattern (§9.1.5).
- T13 promoted from "PRODUCTION-APP REFERENCE" to canonical sourcing reference for every tier; new §0 prescribes ordering; new §1.0 dedicates a section to the TTB Public COLA Registry.
- L2 eval-pipeline plan (`docs/plans/ttb-label-verification-epoch-8-l2-eval-pipeline.md`) authoring sequence updates to require Registry pulls before synthetic generation.
- Existing `scripts/build_synthetic_fixture*.py` outputs are flagged in PRD §9.1.5 as the canonical anti-pattern. They remain in the repo for now (the existing tests depend on them) but no future fixture work may use them as a template.
- Future iterations that ship without a Registry-sourced count must explicitly waive the gap in a new ADR. "Calendar pressure" is not a sufficient waiver — the BRD already authorizes the Registry as the test corpus, the license is CC0, the per-record URL pattern is documented in T9 §3, and the curation effort for a defensible 30–50 entry corpus is 4–6 hours.
