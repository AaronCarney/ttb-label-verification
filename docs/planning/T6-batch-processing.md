# T6 — Batch Processing Architecture

**Phase:** 3 (Composed Architecture)
**Status:** DEFERRED — questions cannot be fully formulated until T2 (review times, batch sizes), T3, T4 (per-label processing time) are done; partial questions below
**Prerequisites:** T2, T3, T4
**Blocks:** —

## Synopsis

Per stakeholder feedback, batches of 200–300 labels arrive from large importers in peak season. Per the architecture doc, the design intent is a priority queue with adaptive lookahead: first label processed individually under the 5s SLA, subsequent group sizes adapted based on agent review time so the next label is ready when the agent finishes the current one.

The deep questions here — optimal lookahead size, queue depth, throttling — depend on numbers we don't have yet (T2 supplies real review times and batch distributions; T3 and T4 supply per-label processing times). Architecture-pattern questions can be researched now.

## Required reading

- All five core artifacts
- `T2-output.md` (required) — operational metrics, review times, batch size distributions
- `T3-output.md` (required) — rule engine performance budget
- `T4-output.md` (required) — vision layer performance budget
- Background: queue theory primer, work-stealing patterns, backpressure, autoscaling primitives

## Output expected

A `T6-output.md` covering:

1. **Queue architecture pattern recommendation.**
2. **Adaptive lookahead algorithm specification.**
3. **Concurrency and worker model.**
4. **Backpressure and overload handling.**
5. **Mid-batch override semantics** (what happens when the agent rejects a label).
6. **Storage and state model** for in-flight batches.

## In-topic questions

### Questions that can be formulated now (architecture-level)

#### Q6.1 — Queue architecture patterns for variable-time work
What patterns exist for queues where (a) downstream consumers (agents) work at variable speeds, and (b) upstream producers (the batch upload) deliver work in bursts? Compare:
- Simple FIFO with worker pool
- Priority queue with explicit head item
- Pull-based vs. push-based delivery
- Reactive / backpressured streams (Reactive Streams, Kafka consumer-style)
- Work-stealing patterns

Evaluate against our specific shape: one agent, one work source, variable consumer speed.

#### Q6.2 — Lookahead sizing as a control problem
The lookahead size *k* is a control variable: too small and the agent waits; too large and we burn compute on labels that may be canceled or reordered. What's the right control-theory framing?
- Open-loop (estimate review time, schedule accordingly)
- Closed-loop (measure actual review time, adapt)
- Predictive (model agent behavior)

Recommend a starting algorithm with parameters, and a path to adaptation.

#### Q6.3 — Concurrency and worker model
For the prototype, what concurrency model is appropriate?
- Single-process with async (Python asyncio, Node.js)
- Multi-process worker pool
- Distributed (Celery, RQ, etc.)
- Cloud-native (Lambda, Cloud Run)

Decision should respect D-004 (production parity / on-prem feasibility).

#### Q6.4 — Backpressure when lookahead saturates
What if the agent slows or stops mid-batch (lunch, escalation, etc.)? The lookahead can't grow unbounded.
- Maximum lookahead cap
- Idle-worker behavior (do we keep processing or pause?)
- Resumption when the agent returns
- Cost implications (compute spent on labels the agent may never get to)

#### Q6.5 — Mid-batch override semantics
*Gated by Q6.1.* When the agent rejects label N, what happens to lookahead labels N+1 through N+k?
- Continue processing them (assume rejection is independent)
- Pause and wait for the agent to confirm direction (rejection of N may indicate an issue with the whole batch — same submitter, similar labels)
- Surface a pattern-detection prompt to the agent

This is a UX question as much as an architecture one.

#### Q6.6 — In-flight state model
What state needs to be tracked for an in-progress batch?
- Per-label disposition (queued / processing / ready / reviewed / disposed)
- Order of processing vs. order of presentation to the agent
- Batch-level metadata (submitter, submission time, total count, current position)
- Recovery on crash mid-batch

This intersects with D-001 about no-persistent-storage — what's session-scoped vs. needs durability for mid-batch crash recovery?

#### Q6.7 — Multi-agent shared queue (future-state)
For prototype: one agent. For production: 47 agents, possibly batches assigned across them. Architecturally, should the prototype design accommodate this, or is it explicitly out of scope?
- Cost of designing in multi-agent now
- Refactor cost if added later
- Recommendation

### Questions that must wait for T2, T3, T4

#### Q6.8 — Lookahead sizing math [DEFERRED — needs T2 Q2.7, T3 Q3.9, T4 Q4.5]
*Cannot be answered without measured review times and per-label processing times.* Stub:

Given measured agent review time *R* (median, p50, p90) and measured per-label processing time *P* (similarly), compute the optimal initial lookahead size and adaptation rule. Assume one agent, one batch.

#### Q6.9 — Realistic peak-season batch shape [DEFERRED — needs T2 Q2.7]
*Cannot be answered without batch-distribution data.* Stub:

Given the empirical distribution of batch sizes from peak-season imports, what stress profile must the system handle? What's the longest realistic batch, and what's the worst-case time-to-completion under our queue design?

#### Q6.10 — Resource sizing recommendation [DEFERRED — needs Q6.8, Q6.9]
*Concrete resource sizing (workers, memory, etc.) requires the volumetric data above. Hold.*

## Cross-topic synthesis questions
*(Held for later.)*

- **X-1 (T3+T4+T5+T6):** End-to-end time budget. Hold.
- **(T2+T6):** Specific lookahead sizing math given measured numbers. This is essentially Q6.8 above.

## Notes for the researcher

- The architecture-level questions (Q6.1–Q6.7) are genuinely useful to research now. They define the option space.
- Resist the temptation to specify *k* without numbers. Pick the algorithm; let the parameters wait for T2.
- This is a well-studied area (queue theory, adaptive control). Don't reinvent. Cite established patterns.
- Q6.5 (mid-batch override) is the most underspecified area. Lean into the UX implications even though that's T8's territory — flag for cross-topic synthesis with T8.
