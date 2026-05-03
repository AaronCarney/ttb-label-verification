# T10 — Stakeholder Frameworks Applied

**Phase:** Independent (run anytime; most useful early)
**Status:** READY TO RESEARCH
**Prerequisites:** None
**Blocks:** —

## Synopsis

Decision D-001 commits us to a phase-dependent stakeholder priority. The reasoning behind it draws on Power/Interest informally. We want to apply additional stakeholder analysis frameworks (Salience, RACI, empathy maps, Job-to-be-Done, pre-mortem, stakeholder onion) to the actual stakeholders we have, and identify additional stakeholders that the original analysis missed.

This topic is independent of the technical architecture work and can be run anytime. It's most useful early because its outputs shape demo design (T8), evaluation framing (T9), and the "production-stage stakeholders" picture we hand to whoever picks up this work next.

## Required reading

- All five core artifacts, especially:
  - 03-decisions.md (D-001 specifically)
  - 04-research-topics.md §A
  - 05-gaps-and-limitations.md §3.1
- The original take-home brief, especially the four interview transcripts
- Background on the named frameworks: Mitchell-Agle-Wood salience model, RACI, empathy mapping, Christensen JTBD, pre-mortem (Klein), stakeholder onion

## Output expected

A `T10-output.md` covering:

1. **Salience model applied** to our four named stakeholders, with prototype-stage and production-stage variants.
2. **RACI matrix** for the prototype build.
3. **Empathy maps** for at least Sarah and Dave (highest-leverage personas for the take-home).
4. **JTBD framing** for the primary stakeholder (Sarah).
5. **Pre-mortem output:** top 5 risk scenarios with mitigations.
6. **Stakeholder onion** including currently-known and likely-emergent stakeholders.
7. **Stakeholder log template** for ongoing tracking.

## In-topic questions

### Q10.1 — Salience model applied (prototype stage)
For each named stakeholder (Sarah, Dave, Jenny, Marcus), assess on the Mitchell-Agle-Wood salience model:
- **Power**: ability to affect project outcome
- **Legitimacy**: validity of their claim to influence
- **Urgency**: time-criticality of their concerns

Place each in the appropriate Venn region. Note especially Dave — high legitimacy (28 years), low formal power, mixed urgency. Power/Interest alone misses this nuance.

### Q10.2 — Salience model applied (production stage)
*Gated by Q10.1.* Re-run the same analysis assuming a production procurement context. Note the shifts:
- Marcus's power increases substantially
- CIO and contracting officers (currently invisible) become high-power
- Dave's legitimacy is unchanged but his power decreases relative to compliance roles
- Sarah's power may decrease as decision-making shifts upward

This produces the production-stage stakeholder map referenced in D-001.

### Q10.3 — RACI matrix for the prototype build
For each major activity in building the prototype, assign:
- **R**esponsible (does the work)
- **A**ccountable (final decision authority)
- **C**onsulted (provides input)
- **I**nformed (kept up to date)

Activities to cover at minimum:
- Requirements definition
- Architecture decisions
- Test corpus design
- Build / implementation
- Demo / submission
- Hand-off (if any)

Sarah is A on most. We're R on most. Dave/Jenny are C. Marcus is C with veto on production scope. Add others as identified.

### Q10.4 — Empathy map: Sarah Chen
Build an empathy map for Sarah:
- **Says**: explicit statements from interview
- **Thinks**: inferred internal model based on what she said and how
- **Does**: actions and behaviors implied by the interview
- **Feels**: emotional context (worried about adoption, frustrated by past failures, etc.)

Use this to surface what's not in the explicit requirements but is real (e.g., she's protective of her team's time and credibility — the demo should respect that).

### Q10.5 — Empathy map: Dave Morrison
*Gated by Q10.4 (same methodology).* Build an empathy map for Dave specifically. He's the highest-leverage persona for trust signals in the demo. What does he need to *feel* in the first 30 seconds of seeing the tool to lean in rather than fold his arms?

### Q10.6 — JTBD framing for Sarah
Sarah's surface request is "verify labels faster." The deeper job-to-be-done is something like "free my agents from data-entry verification so they can do judgment work." Articulate:
- The functional job (what she's trying to get done)
- The emotional job (how she wants to feel)
- The social job (how she wants to be seen by her team / leadership)

This reframing tends to surface stretch goals and demo-design choices the requirements miss.

### Q10.7 — Pre-mortem: top 5 failure scenarios
Imagine the project failed badly. List the top 5 reasons, ordered by likelihood × severity. Common candidates worth evaluating:
- Demo crashes or times out under load
- Dave finds three obvious misses in the first batch and loses trust
- Sarah's team isn't represented in the demo audience and the demo lands flat
- The take-home reviewer disagrees with our scope choices
- A regulatory citation in our reasoning is wrong
- The deployed URL is unreachable when reviewed
- We over-engineered and missed the headline requirements

For each: probability, severity, mitigation.

### Q10.8 — Stakeholder onion (current + emergent)
Build the concentric-rings stakeholder map:
- **Core**: the people directly using the tool (ALFD agents)
- **Sponsor**: who funds and authorizes (Sarah, her chain of command)
- **Enabler**: who lets it happen technically (Marcus, CIO, contracting)
- **Affected**: who experiences consequences (industry submitters, FDA on edge cases, downstream regulators)
- **Outsider but relevant**: legal, union, accessibility advocates, watchdog orgs

For each ring, list named individuals where known, role categories where not. Flag where someone in an outer ring could move inward (e.g., a labor union representative becoming central if the tool is perceived as a job threat).

### Q10.9 — Likely emergent stakeholders for production
*Gated by Q10.8.* Who will become a stakeholder once this conversation moves past prototype?
- TTB CIO and OCIO staff
- Treasury IT compliance officers
- FedRAMP review board (if applicable)
- Section 508 review
- NTEU (National Treasury Employees Union) — federal agents have one
- Industry stakeholders (DISCUS, Wine Institute, Beer Institute)
- Public-interest groups (CSPI has historically engaged TTB on labeling)
- Regulations & Rulings Division (rule interpretation)
- Field offices beyond Janet's

For each: their likely concerns, when they activate, what they'd ask for.

### Q10.10 — Stakeholder log template and cadence
Design a stakeholder log template (separate from the matrix snapshot) that captures:
- Who said what, when, in what channel
- What requirements derived from the conversation
- What was promised, deferred, or rejected
- What follow-ups are open

And a cadence recommendation: when to re-run analysis, what triggers an update, who maintains it.

## Cross-topic synthesis questions
*(Held for later.)*

- **X-6 (T8+T9+T10):** Demo path that hits stakeholder signals. Hold for synthesis.

## Notes for the researcher

- This topic is partly soft-skills work. Don't over-formalize. The output should read like a senior PM's working notebook, not a textbook chapter.
- Be honest about what's inferred vs. stated. The empathy maps will rely on inference — flag it.
- Pre-mortem is most valuable when it's specific. "The demo could fail" is useless. "The demo could fail because the deployed Vercel app cold-starts and exceeds Sarah's 5s expectation on her first click" is useful.
- The stakeholder onion typically reveals 2-3 stakeholders the original analysis missed. Look for them deliberately.
- This output is unusual in being primarily for *us* (it shapes how we work) rather than for the take-home reviewer. But a well-done version of this also signals to the reviewer that we think like operators, not just engineers.
