# Fixture 06 — ABV out-of-tolerance

**PRD §8.1 reference.** ABV delta on label vs. application > 1% — exercises FR-400 ABV-tolerance fail; demoes the override path (AC-FR-803, owned by E7).

**Exercises.** ABV-tolerance rule with delta = 2.5% (labeled 40%, application 42.5%).

**Existing assets.** `expected.json` (committed; 7 ExpectedValue entries with the out-of-tolerance values). This task ADDS `label.png` (built by `scripts/build_fixture_06.py`) + `notes.md`.

**Provenance.** synthetic-acme-abv-mismatch.

**Class balance tag.** spirits.
