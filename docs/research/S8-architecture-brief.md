# S8 — Architecture Document

**Phase:** Synthesis (post-research, post-PRD)
**Status:** READY TO AUTHOR
**Prerequisites:** `BRD.md` (S6 output) and `PRD.md` v0.2 (S7 output) are complete and approved. `PRD-deferred-content.md` (companion to PRD v0.2) captures implementation specifics already settled. All Tn-output and Sn-output files. `01-requirements.md`, `02-architecture.md` (skeleton), `03-decisions.md` (esp. D-001 through D-016).
**Blocks:** No downstream session in the BRD/PRD/Arch sequence; the README and rule pack are authored downstream of this doc but are deliverables, not synthesis sessions.

---

## Synopsis

This session produces `ARCHITECTURE.md` — the technical specification for the TTB AI-Powered Alcohol Label Verification prototype. The Architecture Document answers **how** the system is built. It does **not** explain why (BRD) or what (PRD).

The seam:

- **BRD** owns business problem, stakeholders, value, scope, compliance posture, BR-### business requirements.
- **PRD** owns user roles, user journeys, FR-###, externally observable behavior, system-boundary data contracts, acceptance criteria.
- **Arch Doc** owns components, interfaces between components, internal data models, technology choices, deployment topology, substitutability seams, failure-recovery design, ADRs.

**The PRD wins ties.** When research outputs disagree with the PRD, follow the PRD and log the conflict. When the PRD disagrees with the take-home, that's a PRD bug — flag it back to S7, don't paper over it in the Arch Doc.

**Dual audience.** Stated audience: take-home reviewer evaluating whether the candidate translated functional requirements into a buildable design. Simulated audience: a senior engineer joining the team and reading this to understand the codebase before opening the repo. Write for the simulated audience.

**Critical scope discipline.** Architecture describes internal structure. "The system shall expose a `/healthz` GET endpoint that loads models and returns 200 within 2 seconds" is architecture (Arch Doc). "The system shall support a pre-warm path so that the first demonstrated label is not penalized by cold-start latency" is functional (PRD). Test: would two competing implementations of the same architecture make the same component-level choices? If yes, it's architecture. If the choice is purely about externally observable behavior, it belongs in the PRD.

**Already-settled decisions.** S3 produced D-013 (stack-shape: FastAPI + Jinja2 + React island), D-014 (rule data format: real YAML under `rules/`), D-015 (dual deployment mode: `VISION_MODE={local,cloud,auto}`), D-016 (local model serving: HuggingFace Transformers in-process). Lift these as committed; do not re-litigate. New decisions surfaced during authoring become D-017+.

## Required reading

- **Primary (treat as ground truth):**
  - `Take-Home_Project__AI-Powered_Alcohol_Label_Verification_App.docx` — interview notes, technical requirements, deliverables, evaluation criteria
- **Synthesis upstream (this doc must align with):**
  - `PRD.md` v0.2 (S7 output) — every component must serve at least one FR-###; every interface must materialize at least one §6 data contract
  - `PRD-deferred-content.md` — implementation specifics extracted from the PRD self-review; head-start material for §1 (Architecture sections), §6 (eval-harness), §3 (demo runbook)
  - `BRD.md` (S6 output) — business constraints (firewall, prototype-tier compliance, no PII) bound the design space
- **Core artifacts:**
  - `01-requirements.md` — Hard / Strong / Medium / Stretch tiers; Hard requirements drive design priorities
  - `02-architecture.md` — existing skeleton with four guiding principles and high-level data flow; this doc supersedes and expands it
  - `03-decisions.md` — esp. **D-002** (deterministic core, AI orchestrates), **D-004** (production-parity / substitutability), **D-005** (per-field match policies in YAML), **D-013** (FastAPI + Jinja2 + React island; SVG bbox overlay; shadcn/ui), **D-014** (real YAML under `rules/` with Pydantic v2 RuleSet model + Python validator registry), **D-015** (dual deployment mode; HF Spaces Docker SDK), **D-016** (HuggingFace Transformers in-process for local model serving)
  - `04-research-topics.md` — open questions the architecture should answer or explicitly defer
  - `05-gaps-and-limitations.md` — accepted prototype gaps that constrain design honestly
- **Research outputs (architecture-spec material — the in-scope T-outputs for this session):**
  - `T3-output.md` — validator interface (`FieldObservation` + `ExpectedValue` → `ValidationResult`), match-policy implementations, RuleSet versioning, per-rule timeout budget, performance budget within 5s SLA, engine failure-mode taxonomy. **Primary source for §4 component design (rule engine), §6 internal data models, and §10 failure-recovery design.**
  - `T4-output.md` — vision/OCR layer architecture, per-field extraction-property requirements, multi-model cross-check pattern (PaddleOCR + Florence-2 + Qwen2.5-VL), needs-better-photo decision logic, image preprocessing pipeline. **Primary source for §4 vision-extractor component and §11 performance design.**
  - `T5-output.md` — orchestrator task list (brand-borderline, reasoning enrichment, OCR reconciliation), structured-output contract pattern, single-shot tool-call posture, prompt-versioning, fallback behavior. **Primary source for §4 orchestrator component and §10 model-unavailable handling.**
  - `T6-output.md` — batch processing primitives (asyncio.Queue, EWMA-smoothed lookahead), pull-based reactive-streams pattern with `request(n)` semantics, mid-batch override under independence assumption, soft-anomaly detector, in-flight state model. **Primary source for §4 batch-processor component and §6 batch state model.**
  - `T8-output.md` — UX component inventory (17 components), keyboard model implementation, ARIA patterns per component, evidence-panel construction, override-drawer focus management. **Primary source for §4 frontend component design.**
  - `S1-output.md` — vision/OCR/VLM stack survey (PaddleOCR-GPU, Florence-2-large, Qwen2.5-VL-7B-AWQ); rationale for the local-vision stack on a 24 GB GPU. **Primary source for §7 technology stack rationale.**
  - `S3-output.md` — D-013 (stack-shape: FastAPI + Jinja2 + React island; SVG bbox overlay; shadcn/ui themed with USWDS tokens), D-014 (real YAML under `rules/` with Pydantic v2 + validator registry), D-015 (dual deployment mode `VISION_MODE={local,cloud,auto}`; HF Spaces Docker SDK), D-016 (HuggingFace Transformers in-process). **Lift directly into §7 and §9.**
  - `S5-output.md` — RuleSet Pydantic v2 contracts, `reason_codes.yaml` registry, RuleLoader fail-closed schema validation, rule-id → CFR → S4 fixture mapping. **Primary source for §6 rule-pack data model and §4 rule-loader component.**
- **Excluded as primary sources for this session** (those are BRD, PRD, or out-of-scope material): T1, T2, T7, T9, T10, T11, T12, S2, S4, S6, S7, R0.
  - T1's regulatory framework is *referenced* in §6 reason-code registry, not redrawn — the PRD §5.3 owns the rule manifest.
  - T2's form schema is *referenced* in §3 external interfaces (the PRD §6.1 owns the wire contract) — the Arch Doc only documents how it is parsed and validated internally.
  - T7's compliance posture is *referenced* in §12 security design as a constraint, not redrawn.
  - T9 / S4 evaluation methodology is owned by the PRD §9; the Arch Doc only documents the eval-harness's component shape.
  - S2 / S6 / S7 are upstream (scope, BRD, PRD).

## Output expected

A single `ARCHITECTURE.md` document, ~25–35 pages, with these sections in order:

1. Document control and purpose
2. Architecture principles
3. System context and external interfaces
4. Component decomposition
5. Data flow
6. Internal data models
7. Technology stack and rationale
8. Substitutability seams (D-004)
9. Deployment topology
10. Failure modes and recovery
11. Performance and scaling design
12. Security and privacy design
13. Observability design
14. Local development setup
15. Architecture Decision Records (ADRs)
16. Open questions and decisions deferred
17. Traceability matrix (FR → Component)
18. Glossary delta
19. Appendices (cross-references, change log)

## In-topic questions

### Section 1 — Document control and purpose

- State the purpose, audience (stated and simulated), and reading order. Name the seam: BRD = why, PRD = what, Arch Doc = how.
- State out-of-scope for this doc: not the BRD's business case; not the PRD's user-facing behavior or wire contracts; not the README; not the rule pack itself (which is a delivered artifact under `rules/`); not vendor evaluation beyond what's already settled in D-013–D-016.
- Note that PRD-deferred-content.md is the head-start input; consume it explicitly and mark each item as it is absorbed.

### Section 2 — Architecture principles

Lift the four guiding principles from `02-architecture.md`:

1. **Deterministic core, AI orchestrates** (D-002).
2. **Substitutability at the inference seam** (D-004).
3. **Rules as data** (D-014).
4. **Honest failure modes** (D-007; T3 §Q3.10).

Add a fifth if needed for completeness. Each principle: one sentence stating it, one sentence on what it forbids, citation to the source decision.

### Section 3 — System context and external interfaces

- A C4-level-1 context diagram (textual or Mermaid) showing the system boundary, the reviewer (browser), the optional external LLM/vision API (cloud mode), and the optional on-prem model store (local mode).
- External interfaces: HTTP endpoints exposed (single-label POST, batch POST, healthz, eval dashboard, static assets, server-sent events or WebSocket for batch streaming if used). For each: method, path, request shape (point to PRD §6), response shape, error contract.
- Note what the system does *not* expose: no public write API, no admin API, no rule-pack-edit API.

### Section 4 — Component decomposition

A C4-level-2 component diagram and a one-paragraph description per component. Components to include (lift from `02-architecture.md` and S3):

1. **Web layer** (FastAPI + Jinja2 page shells + React island) — handles HTTP, renders shells, serves the bbox/evidence island as a static asset.
2. **Application service** — orchestrates a single evaluation: takes the wire-format input, invokes Vision Extractor, invokes Rule Engine, invokes Orchestrator (when needed), assembles the disposition envelope.
3. **Vision Extractor** (D-004 substitutable interface; `LocalVisionExtractor` and `CloudVisionExtractor` concrete implementations per D-015).
4. **Rule Engine** — loads RuleSet from YAML at startup (D-014), evaluates rules against `FieldObservation` + `ExpectedValue` per T3, emits `ValidationResult` with reason codes per S5.
5. **Validator Registry** — Python registry of named validator functions referenced from YAML (D-014); maps validator names to callables.
6. **AI Orchestrator** — performs the three tasks from T5 (brand-borderline disambiguation, reasoning enrichment, OCR reconciliation); never decides pass/fail (D-002); fails to `needs_review` (FR-304).
7. **Batch Processor** — implements pull-based lookahead per T6 (asyncio.Queue, EWMA k-sizing, mid-batch independence, soft-anomaly detector).
8. **Audit Recorder** — assembles the audit-trail object per FR-703 / §6.2; in-memory-per-session per NFR-DATA-002.
9. **Eval Harness** — separate process / module per S4; consumes the same Application Service contract; runs against `eval/manifest.jsonl`.

For each component: responsibility, dependencies (which other components it calls), substitutability (does it sit behind an interface; if so, which one), failure mode (what happens when it fails per FR-900 series).

### Section 5 — Data flow

- **Single-label flow** (sequence diagram or numbered steps): browser POSTs → Web layer → Application Service → Vision Extractor → Rule Engine → (Orchestrator if needs_review surfaces) → Audit Recorder → Application Service assembles disposition → Web layer returns to browser.
- **Batch flow:** browser POSTs zip/multi → Web layer streams items into Batch Processor → Batch Processor calls Application Service per item with k=2–3 lookahead per T6 → results stream to browser via SSE or WebSocket.
- **Pre-warm flow:** `/healthz` GET → loads models → exercises full pipeline against fixture-01 sentinel → returns 200 (per PRD-deferred-content.md §3.1).
- Annotate each step with the PRD FR it serves and the time-budget allocation (per T3 §Q3.9 5s SLA breakdown).

### Section 6 — Internal data models

Pydantic v2 models (or equivalent) at the component-boundary level. Keep wire-format models out (those are PRD §6); document only internal types.

- `FieldObservation` (T3 §Q3.2 input contract): what the Vision Extractor produces.
- `ExpectedValue` (T3 §Q3.2): what comes from the application JSON.
- `ValidationResult` (T3 §Q3.2 output contract): what each validator returns.
- `RejectionReason` (T3 §Q3.6 hierarchical reason-code model): how reason codes are constructed.
- `RuleSet` and `Rule` (S5 §c Pydantic contracts): the in-memory shape after YAML load.
- `BatchItem`, `BatchInFlightState` (T6 §Q6.6): the batch processor's state model.
- `AuditRecord` and per-rule-trace entry: the in-memory representation of FR-703.
- Reason-code registry (`reason_codes.yaml` shape per S5 §e).

For each model: field list with types, validation rules, lifecycle (when created, when discarded), and the FR it supports.

### Section 7 — Technology stack and rationale

Lift from S3 D-013 through D-016 and S1. Organize as a table:

| Layer | Choice | Decision | Rejected alternatives | Notes |
|---|---|---|---|---|
| Backend framework | FastAPI | D-013 | Flask, Django, FastHTML | ASGI, Pydantic v2 native |
| Frontend shell | Jinja2 | D-013 | Pure SPA, Next.js | Single-process |
| Frontend island | React + Vite + shadcn/ui | D-013 | Streamlit, Gradio, Mantine | shipped pre-built |
| Bbox overlay | SVG over `<img>` | D-013 | Canvas, Konva | DOM-accessible |
| Rule data | YAML under `rules/` + Pydantic v2 RuleSet | D-014 | Pure Pydantic, Drools, OPA | Validator registry pattern |
| Vision (cloud mode) | GPT-4o-vision (substitutable) | D-015 | Claude, Gemini | Default for deployed URL |
| Vision (local mode) | PaddleOCR + Florence-2 + Qwen2.5-VL-7B | S1, D-016 | vLLM, Ollama, llama.cpp | HF Transformers in-process |
| Deployment (public URL) | HF Spaces, Docker SDK, cpu-basic default | D-015 | Vercel, fly.io, Railway | Cached fixtures for demo |
| Package management | uv | (note D-013) | pip, poetry | Fast resolver |

Add prose only where the table needs it. Do not relitigate decisions.

### Section 8 — Substitutability seams (D-004)

For each substitutable interface, document:

- The abstract interface (Python ABC or Protocol).
- The concrete implementations shipped (e.g., `LocalVisionExtractor`, `CloudVisionExtractor`).
- The selection mechanism (e.g., `VISION_MODE` env var with `auto` probing for CUDA).
- The non-default implementations preserved for production substitution (e.g., `app/orchestrator/vllm_xgrammar.py` per D-016).
- The contract guarantees the interface preserves (e.g., `VisionExtractor.extract(image_bytes) → FieldObservation` regardless of backend).

Seams to cover: VisionExtractor (D-015), Orchestrator (T5), RuleLoader (D-014). Note explicitly which seams are *not* substitutable in MVP and why (e.g., Rule Engine itself is not substitutable; OPA / Drools is rejected per D-014 alternatives).

### Section 9 — Deployment topology

- **Local development:** Profile A (Windows + WSL2 + NVIDIA GPU per S3), Profile B (macOS without GPU), Profile C (Linux without GPU). For each: setup steps, dependencies, expected first-run time.
- **Public URL deployment:** HF Spaces Docker SDK, cpu-basic hardware default, environment variables required (`OPENAI_API_KEY` or equivalent, `VISION_MODE=cloud`).
- **Optional GPU upgrade:** A10G-small for live local-vision demos; cost note ($1/hr per HF pricing); when to use.
- **Production-trajectory deployment** (informational, not committed): how the same architecture maps to on-prem deployment behind a federal firewall — `VISION_MODE=local` selects local extractor, no outbound calls, models served from a local registry. Reference T7 staging map; do not redraw.

### Section 10 — Failure modes and recovery

Lift the 13-row T3 §Q3.10 engine failure-mode taxonomy. For each row, add:

- **Detection:** how the system detects this failure (timeout, exception class, missing field, etc.).
- **Recovery:** what happens (per the PRD FR-900 series) — typically `needs_review` with a structured reason code; never silent `pass`.
- **Operator visibility:** what gets logged (per NFR-OBS-001) and what surface the operator sees.

Add cross-cutting failure modes:

- **Cold start:** model load on first request; mitigation = `/healthz` pre-warm.
- **LLM endpoint unreachable:** fallback to deterministic-only path; AI-orchestration tasks return `needs_review` per FR-304.
- **Browser network loss mid-batch:** reviewer keeps queue position locally; resume on reconnect.
- **OOM under batch pressure:** lookahead k decremented; soft-anomaly advisory fires if pressure persists.

### Section 11 — Performance and scaling design

- **Time-budget breakdown** for the 5s SLA per T3 §Q3.9.3 (engine slice 100–300 ms; vision 1.5–2.5 s; orchestrator 0.5–1.5 s; web overhead 100–300 ms; tail buffer).
- **Concurrency model** per T6 §Q6.3 (asyncio single-process; one CUDA context for local vision; per-request bounded concurrency).
- **Lookahead sizing** per T6 §Q6.8 (default k=3 per `PRD-deferred-content.md` §1.4; EWMA-adapted around reviewer cadence).
- **Tail-latency strategy** per T3 §Q3.9.4 (per-rule timeouts; whole-evaluation timeout returns partial results with `ENGINE.SLA.TIMEOUT`).
- **Resource sizing recommendation** per T6 §Q6.10 (single 24 GB GPU sufficient for local mode; cpu-basic sufficient for cloud-mode public URL with cached fixtures).
- **What we are not optimizing for:** multi-tenancy (single agent assumption per T6 §Q6.7), high QPS (one user, batch at human pace), GPU utilization (one user, model resident).

### Section 12 — Security and privacy design

Operationalize PRD NFR-SEC-001 through NFR-SEC-004:

- **TLS** at the deployment edge (HF Spaces handles by default; document for on-prem).
- **Secret management:** environment-variable load at process start; no secrets in source; document the env-var inventory.
- **Input validation:** Pydantic v2 strict-mode parsing on the JSON envelope; image format allowlist (JPEG/PNG only per FR-101); size limits.
- **Logging discipline:** operationalize NFR-SEC-004 — what fields the structured logger redacts (extracted text, application JSON, image bytes) and what it preserves (evaluation_id, reason codes, durations, error class).
- **No persistence:** how NFR-DATA-001/002 are enforced (in-memory data structures with explicit lifecycle; no DB; no file writes outside `eval/history/` which is eval-only).
- **Cloud mode outbound calls:** what destinations are allowed (the configured LLM endpoint only); how this is documented for federal-context review (the firewall whitelist).

### Section 13 — Observability design

Operationalize PRD NFR-OBS-001/002:

- **Structured logs** per T3 §Q3.10 schema; reproduce the per-failure-mode field schema as the canonical log-emission shape (per `PRD-deferred-content.md` §1.5).
- **Metrics:** P50/P95/P99 latency on single-label evaluations exposed via a `/metrics` endpoint or equivalent.
- **Tracing:** optional, OpenTelemetry-compatible if added; not MVP.
- **Eval dashboard:** `/eval` route gated by `DEV_MODE` env flag (per `PRD-deferred-content.md` §2.1); renders confusion matrix and per-rule precision/recall from `eval/history/`.
- **Audit trail vs. telemetry:** decide and document whether `audit_trail.per_rule_trace[].duration_ms` stays in the audit envelope or moves to a separate `metrics` block (per `PRD-deferred-content.md` §1.3 — recommendation was to split).

### Section 14 — Local development setup

- **Repo layout** per S3 §4 folder layout.
- **Dependency management:** uv with `pyproject.toml`; frontend `pnpm` only when changing the React island (the built island is committed to `app/ui/static/island/` per D-013 consequences).
- **First-run script:** `uv sync && uv run task demo` per D-013; document what it does and the expected first-run time per profile.
- **Demo runbook reference:** point at `DEMO-RUNBOOK.md` (per `PRD-deferred-content.md` §3.4) for the recorded-walkthrough setup.
- **Eval-harness commands:** `uv run task eval-smoke` (PR subset), `uv run task eval-full` (merge full run), `uv run task eval-dashboard` (local dashboard).

### Section 15 — Architecture Decision Records (ADRs)

Lift D-002, D-004, D-005, D-013, D-014, D-015, D-016 by reference (do not duplicate). Author **new** ADRs for any decision surfaced during writing. Likely candidates:

- **D-017** — Confidence aggregation: min vs. multiplication (lift from `PRD-deferred-content.md` §1.1; probably already implicit but should be a formal ADR).
- **D-018** — Audit trail vs. telemetry split: keep `duration_ms` in audit or move to separate `metrics` block (per `PRD-deferred-content.md` §1.3).
- **D-019** — Eval-harness gating: `DEV_MODE` env-flag pattern; whether eval routes are compiled out of production builds entirely.
- **D-020** — Demo-cache regeneration: when and how `scripts/regenerate_fixtures.py` runs (manually, per release, on cache-key drift).

Use the ADR-style format already in `03-decisions.md`: context → decision → rationale → alternatives → consequences. Append to `03-decisions.md`, do not bury in Arch Doc prose.

### Section 16 — Open questions and decisions deferred

Pull from `04-research-topics.md` and from `PRD-deferred-content.md` §4. Likely items:

- **OQ-ARCH-1** — Multi-image label aggregation algorithm (PRD OQ-PRD-4 deferred; arch design needs to know whether this is in MVP scope or stretch).
- **OQ-ARCH-2** — Cross-session determinism via persistent canonicalized cache (PRD NFR-DET-002 stretch; arch impact = persistence layer).
- **OQ-ARCH-3** — Production-trajectory ATO posture: documented but not designed (T7).
- **OQ-ARCH-4** — Audit-record retention policy for production: arch implication is "design the boundary so this can be added without rework" (D-004 substitutability extended to persistence).

### Section 17 — Traceability matrix (FR → Component)

For every FR series in the PRD §5, name the primary component that implements it:

| PRD FR series | Primary component | Supporting components |
|---|---|---|
| FR-001–008 (extraction) | Vision Extractor | Application Service |
| FR-100–106 (ingest) | Web layer | Application Service |
| FR-200–240 (rule evaluation) | Rule Engine | Validator Registry |
| FR-300–304 (orchestration) | AI Orchestrator | Rule Engine (calls into) |
| FR-400–406 (batch) | Batch Processor | Application Service |
| FR-500–511 (UX) | Web layer (Jinja2 + React island) | — |
| FR-600–604 (image) | Web layer | Vision Extractor |
| FR-700–704 (disposition) | Application Service | Audit Recorder |
| FR-800–804 (override) | Web layer | Audit Recorder |
| FR-900–912 (engine failures) | All | (cross-cutting) |

Goal: every PRD FR has a home component; every component justifies its existence by serving FRs.

### Section 18 — Glossary delta

Arch-Doc-only terms not in BRD or PRD glossaries: ASGI, Pydantic v2, Jinja2, React island, shadcn/ui, USWDS tokens, axe-core, vLLM, AWQ, asyncio, SSE, EWMA (full term, not just the PRD reference), ABC (abstract base class), Protocol (Python typing), uv, OpenTelemetry. One line each.

### Section 19 — Appendices

- **19.1 Cross-reference map** — this Arch Doc section ↔ companion artifacts (BRD section, PRD FR series, Tn-output reference, Sn-output reference).
- **19.2 Repo layout** — full tree from S3 §4.
- **19.3 Dependency inventory** — exact `pyproject.toml` dependency list with version pins; node dependencies if React island is regenerated.
- **19.4 Change log** — version 0.1 initial issue, with dated entries on each subsequent revision.

## Cross-topic synthesis questions consumed by this session

- **X-3** (how the deterministic core and AI orchestrator coexist at runtime — concurrency, timeouts, fallback): the Arch Doc is the natural home. §4 (orchestrator component) plus §10 (failure modes) plus §11 (performance budget) together resolve it.
- **X-5** (substitutability story for federal-context production deployment): §8 (substitutability seams) plus §9 (deployment topology) plus §12 (security) together resolve it.

## Notes for the author

- **The PRD wins ties.** Same rule as S7 (which had "the take-home wins"). If the Arch Doc design contradicts a PRD FR, that's an Arch Doc bug, not a PRD bug.
- **Implementation voice, not requirements voice.** "The Vision Extractor is a Python ABC with two concrete subclasses selected by `VISION_MODE`" (architecture) vs. "the system shall support a deployment mode in which inference runs on-prem" (requirement — PRD NFR-PORT-002). If you find yourself writing "shall," check whether you're paraphrasing a PRD requirement; if so, cite the FR/NFR and move on.
- **Lift, don't rewrite, the already-decided stack.** D-013–D-016 settled the stack. Reference them; do not re-evaluate alternatives in Arch-Doc prose. Section 7 is a *summary* table, not a fresh evaluation.
- **PRD-deferred-content.md is the head start.** Items in that doc are correct but were extracted from the PRD because they belong here. As you absorb each item, mark it consumed; the goal is for `PRD-deferred-content.md` to be fully absorbed by the time the Arch Doc is final.
- **Failure modes are first-class.** §10 is not a footnote; it is the operationalization of D-007 (honest failure modes). Reproduce the T3 §Q3.10 13-row table verbatim with detection/recovery/visibility columns added. Cross-reference into the FR-900 series.
- **Tier the design where it matters.** Hard FRs (e.g., NFR-PERF-001, FR-703 audit trail, FR-303 AI never flips fail) drive design priorities. Stretch items get a "design preserves option for" note.
- **One PRD FR may map to many components and vice versa.** §17 traceability shows fan-out explicitly. This is the primary value of the matrix.
- **Don't bleed into the BRD or PRD.** If you find yourself explaining business rationale at length, that's BRD prose. If you find yourself specifying user-facing behavior, that's PRD prose. Architecture is internal structure.
- **Length target: 25–35 pages.** Architecture docs are longer than PRDs because the component count and data-model count multiply. If it's growing past 35, check whether §7 is relitigating settled decisions or whether internal-data-model documentation is duplicating wire contracts (it shouldn't — wire is PRD §6).
- **New decisions surfaced during writing → ADRs.** Append D-017+ to `03-decisions.md`. Do not bury decisions in Arch-Doc prose. The likely candidates are pre-named in §15.
- **Section ordering is deliberate.** Principles before context before components before data. Reviewers read top-down; the structure should let an engineer joining the team stop reading after §9 and still have enough to get hands on the codebase.
- **Diagrams.** C4-level-1 (context) and C4-level-2 (component) at minimum. Mermaid is fine; ASCII is fine; avoid binary image dependencies. One sequence diagram for single-label flow, one for batch flow.

## What this session does *not* produce

- Business case, stakeholder analysis, cost-benefit material — all upstream in the BRD.
- User-facing behavior, wire-format contracts, acceptance criteria, evaluation targets — all upstream in the PRD.
- The README — that's a deliverable artifact, downstream of all three docs.
- The rule pack itself (`rules/*.yaml`) — that's a delivered artifact, referenced by Arch Doc §6 RuleSet model but not authored here.
- The demo runbook (`DEMO-RUNBOOK.md`) — referenced by Arch Doc §14, but its content is delivered separately per `PRD-deferred-content.md` §3.4.
- The eval-harness configuration files (`eval/manifest.jsonl`, `eval/datasheet.md`) — referenced by Arch Doc §13, but authored as eval-harness deliverables.
- A vendor evaluation. D-013 through D-016 settled the stack; do not reopen.
