# Gaps & Limitations — TTB Label Verification Prototype

**Status:** LIVING DOCUMENT
**Last updated:** 2026-04-28

This doc serves the brief's instruction to "document any trade-offs or limitations." It captures three things:

1. **Known limitations of the prototype** — accepted gaps we're shipping with.
2. **What we'd do without time constraints** — work that's out of scope for the take-home but would matter for production.
3. **Process gaps** — methodological things (like ongoing stakeholder analysis) that we'd do continuously, not as a one-shot.

This is distinct from the Decisions doc (what we chose and why) and the Research doc (what we still need to learn). This doc is honest disclosure.

---

## 1. Known limitations of the prototype

(Populate as decisions get made. Initial entries below; expect this list to grow.)

- **Single-class deep validation deferred.** Common fields covered across wine/spirits/malt. Class-specific rules (vintage, age statements, appellations) deferred to stretch.
- **Image-quality robustness is best-effort.** Labels with severe glare, extreme angles, or poor resolution may fail-out as "needs better photo" rather than be recovered.
- **Rule set is hard-coded for the prototype.** Rule changes require code changes. A production version would externalize rules as data.
- **Cloud inference is acceptable for the prototype.** Production deployment in a federal context likely requires on-prem inference; the architecture is designed to allow this swap, but it is not implemented.
- **No persistent storage or audit trail.** Session-only. A production version would require document-retention compliance.
- **Authentication is whatever the deployment platform provides.** Production would need PIV / SAML federation.

---

## 2. What we'd do without time constraints

### 2.1. Validate with real TTB agents
The single highest-leverage thing. Stakeholder interviews give us hypotheses; supervised use by actual agents on actual labels turns hypotheses into facts. We'd:
- Sit with Dave for an afternoon and watch him work, not interview him.
- Have Jenny run 50 labels through the tool and capture every moment of friction.
- Ask Sarah to define "good enough to deploy" in measurable terms before we build, not after.

### 2.2. Build a real test corpus
The Public COLA Registry has approved labels back to 1999 with images. We'd:
- Pull a stratified sample across beverage classes, container sizes, and time periods.
- Hand-annotate failure modes from rejected applications (need to find a source for these).
- Create synthetic adversarial cases (deliberately altered warnings, off-by-0.1 ABV, brand-name variants).
- Run the system against this corpus and report precision/recall per field.

### 2.3. Production architecture work
- On-prem inference benchmarking on representative hardware.
- FedRAMP / ATO posture assessment.
- Section 508 accessibility audit (federal requirement we haven't addressed).
- Integration design for COLA system, even if not implemented.

### 2.4. Full beverage-class rule coverage
Wine: vintage, appellation, estate-bottled, varietal claims. Spirits: age statements, multiple-distillation claims, geographic designations. Malt: type designations, alcohol-content disclosure rules. Each is a non-trivial body of rules.

### 2.5. Error-case taxonomy with real data
Right now our rejection-reason categories are derived from the brief and the regulations. Real-world data would let us validate that the taxonomy matches actual failure modes ALFD encounters.

---

## 3. Process gaps

### 3.1. Ongoing stakeholder analysis
Stakeholder analysis is not a one-time activity. We'd revisit it at every phase gate (kickoff → prototype demo → pilot → production decision) and any time scope or budget changes.

**Why re-running matters beyond verification:**

- **Drift in stated vs. revealed priorities.** People say one thing in interview and act differently when shown a working prototype. The second pass typically delivers truer requirements than the first.
- **New stakeholders emerge.** Once a prototype exists, lawyers, security reviewers, vendor management, the union, and adjacent teams (Field Operations, Trade Investigations) start surfacing. They were always there; nobody mentioned them in the abstract.
- **Power shifts by phase.** Marcus's veto power activates the moment we talk production. Dave's adoption power activates the moment we talk pilot. Sarah's power is constant but spends down with each ask.
- **Scope creep early-warning.** New stakeholders almost always bring new requirements. Logging them against the original tier list lets us say "yes — and here's what comes out of scope" instead of silently bloating.
- **Political instrument.** Showing Sarah a fresh stakeholder map at the pilot review legitimately surfaces "we now need to bring in the CIO" without it sounding like scope creep — it's just what the framework produced.

**Cadence we'd run:**
- Use the same framework each pass so snapshots can be diffed.
- Maintain a *stakeholder log* — running record of who said what when — separate from the matrix snapshot. Provides provenance for trade-offs later.
- Trigger re-analysis on phase gates *and* on signals: a new requirement appearing, a previously-quiet party going public, scope changing materially.

### 3.2. Requirements traceability
With more time, every requirement would map to: a stakeholder source, a test case, and a code module. We'd maintain this as a live matrix, not as documentation that drifts.

### 3.3. Pre-mortem before build
We'd run a structured pre-mortem before writing code: assume the project failed, ask why, address the top 3–5 risks deliberately. Cheap to run; catches things interviews miss.

### 3.4. Demo design
A take-home is graded partly on the demo. We'd design the demo path explicitly:
- What's the first thing Sarah sees?
- What test case best demonstrates Dave's nuance handling? (STONE'S THROW)
- What test case best demonstrates Jenny's strictness? (altered warning)
- What test case shows graceful failure on an unreadable image?
- What's the worst thing a reviewer might try, and how does the system handle it?

---

## How this doc is maintained

- Add items as they're identified, even mid-build. Don't wait until the end.
- When a limitation gets resolved, move it to Decisions doc (with reasoning) rather than just deleting it.
- This doc should be honest, not defensive. "We didn't have time" is fine; "we couldn't figure it out" is also fine.
