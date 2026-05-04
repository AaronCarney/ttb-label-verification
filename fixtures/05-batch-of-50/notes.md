# Fixture 05 — Batch of 50

**PRD §6.3 / §8.1 reference.** 50-label batch envelope — exercises `POST /batches`, lookahead SSE streaming, M-of-N anomaly advisory, and the three-keystroke override path (FR-803).

**Distribution (forces anomaly + override).**
- 30 clean spirits → `pass` (synthesized from 01-spirits-clean)
- 10 ABV out-of-tolerance → `fail` / `FR-400-abv-tolerance` (synthesized from 06-abv-out-of-tolerance; same-reason cluster forces M-of-N anomaly advisory)
- 5 warning title-case → `fail` / `FR-200-government-warning` (synthesized from 03-warning-title-case)
- 5 borderline confidence → `needs_review` (mild blur on warning block, synthesized from 07-borderline-confidence)

**Variant strategy.** 5-brand rotation (`ACME BOURBON`, `STILLHOUSE BOURBON`, `FRANKFORT SELECT`, `BLUE RIDGE RYE`, `RIVER MILL`) over 50 labels keeps OCR signal stable while giving the brand-match path non-trivial input. ABV cluster carries `abv_actual_pct=42.5` vs `abv_labeled_pct=40.0` (delta = 2.5% > 1% threshold).

**Provenance.** synthetic — built by `scripts/build_fixture_05.py` from PIL primitives. Idempotent: re-running is a no-op once labels exist.

**Class balance tag.** spirits.
