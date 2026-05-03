# T5 — AI / LLM Orchestration Architecture

**Phase:** 3 (Composed Architecture)
**Status:** DEFERRED — questions cannot be fully formulated until T3 and T4 are done; partial questions below
**Prerequisites:** T3, T4
**Blocks:** T6 (partially), T7 (partially)

## Synopsis

Per decision D-002, AI orchestrates and resolves ambiguity but does not decide pass/fail. Its actual job is decided by what's *left over* after the deterministic engine (T3) and OCR/vision layer (T4) have done their work. So most of the deep questions in this topic genuinely cannot be formulated well until those topics are complete — anything we ask now is at risk of being malformed.

This brief contains the questions we can formulate now plus stubs for the deferred ones.

## Required reading

- All five core artifacts
- `T3-output.md` (required) — defines what the rule engine handles, leaving the residual for orchestration
- `T4-output.md` (required) — defines what the vision layer hands off, including ambiguous cases
- Background: prompt-orchestration patterns, function calling/tool use, structured output, retrieval-augmented patterns

## Output expected

A `T5-output.md` covering:

1. **Concrete task list for the AI orchestration layer.** Specific cases where the LLM is invoked, what input it gets, what output is required.
2. **Model selection.** Size, hosted vs. self-hosted, prompt vs. fine-tuned.
3. **Prompt and structured-output design** for each task.
4. **Failure-mode handling.** What happens when the model is wrong or uncertain.
5. **Latency and cost budget** within the 5s SLA.
6. **Production-parity story** for self-hosting.

## In-topic questions

### Questions that can be formulated now (architecture-level)

#### Q5.1 — Patterns for LLM-as-orchestrator vs. LLM-as-decider
What architectural patterns exist for using an LLM as a tool-routing / disambiguation layer (not a decision-maker)?
- Function-calling / tool-use frameworks
- Structured output (JSON schema enforcement)
- Constrained generation
- Retrieval-augmented patterns
- Multi-step agent patterns vs. single-shot routing

For each, evaluate: latency, determinism, auditability, ease of replacement.

#### Q5.2 — Model selection criteria for orchestration role
What criteria should drive model selection for an orchestrator that does not make terminal decisions?
- Capability requirements (small models can route; large models are wasteful)
- Latency budget
- Cost
- Self-hosting feasibility (per D-004 production-parity)
- Determinism / reproducibility
- Trust posture for federal context

Land on a recommendation framework, not a specific model — the model choice depends on Q5.3+.

#### Q5.3 — Self-hostable model survey
What's the current state-of-the-art in self-hostable models suitable for this role?
- Open-weight LLMs at small/mid sizes (8B–70B parameter ranges)
- Quantization options
- Inference framework choices (vLLM, llama.cpp, TGI, etc.)
- Hardware requirements per option
- FedRAMP / federal deployment posture of each

#### Q5.4 — Prompt determinism and replay
For a federal use case where audit trails matter: how do we ensure that LLM behavior is replayable and auditable?
- Versioned prompts
- Versioned models
- Logging of inputs and outputs with rule version
- Temperature and sampling decisions
- Test harness for prompt regression

### Questions that must wait for T3 and T4 outputs

#### Q5.5 — Concrete orchestration task inventory [DEFERRED — needs T3, T4]
*Cannot be formulated until we know what the rule engine handles deterministically and what the vision layer cleanly extracts. Stub:*

Once T3 and T4 are complete, list the specific tasks the LLM is invoked for. Candidates we expect:
- Resolving fuzzy brand-name match when the deterministic similarity threshold is borderline
- Generating natural-language reasoning text from structured rejection codes
- Disambiguating OCR output where multiple interpretations are plausible
- Detecting beverage class from label content when application data is missing or contradicts label

Each task gets: input contract, output contract, prompt design, fallback if model fails.

#### Q5.6 — Per-task prompt and output design [DEFERRED — needs Q5.5]
*For each task identified in Q5.5, design the prompt, structured output schema, and validation. Also: what happens if the structured output is malformed.*

#### Q5.7 — Confidence calibration with the rule engine [DEFERRED — needs T3 Q3.5]
*Gated by T3's confidence model.* How does the LLM's confidence (where it has one) compose with the rule engine's confidence? What thresholds drive disposition decisions?

#### Q5.8 — Latency budget for orchestration tasks [DEFERRED — needs T3 Q3.9, T4 Q4.5]
*Gated by T3 and T4 time budgets.* Given how much of the 5s SLA is consumed by OCR (T4) and rule evaluation (T3), what's left for orchestration? Per-task latency targets.

#### Q5.9 — Failure-mode handling [DEFERRED — needs Q5.5]
*Per orchestration task, what does the system do when the LLM:*
- Returns an answer with low self-reported confidence
- Returns malformed structured output
- Times out
- Returns a refusal or non-answer

#### Q5.10 — Cross-application consistency [DEFERRED — needs Q5.5]
LLMs can produce inconsistent outputs on near-identical inputs. For applications that are slight variants of each other (e.g., same brand, different vintage), how do we ensure consistent treatment?

## Cross-topic synthesis questions
*(Held for later.)*

- **X-1 (T3+T4+T5+T6):** End-to-end time budget. Hold.
- **X-2 (T3+T4+T5):** Decision tree across components. Hold.
- **X-3 (T3+T4+T5+T7):** Production-readiness gaps. Hold.

## Notes for the researcher

- This topic has more deferred than ready questions by design. Resist the urge to speculate on the deferred ones — speculation here leads to a malformed AI layer that does too much or the wrong things.
- The architecture-level questions (Q5.1–Q5.4) genuinely can be researched now and produce useful output. They establish the option space; the deferred questions narrow it.
- A common failure mode in this kind of work is letting the LLM accumulate responsibilities. Be skeptical of every task that gets added to Q5.5. Default position: if a deterministic alternative exists at acceptable cost, use it.
