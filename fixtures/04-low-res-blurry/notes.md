# Fixture 04 — Low-res / glare

**PRD §8.1 reference.** Image quality below threshold — Evaluator's legibility short-circuit fires before rules.

**Exercises.** `app.vision.quality.assess` returns `needs_better_photo`; Evaluator routes disposition to `needs_review` and propagates `quality.reason_code` — one of `WARNING.LEGIBILITY.{LOW_RESOLUTION, MOTION_BLUR, GLARE}` per `app/vision/quality.py` thresholds (low-res-variance < 50 or motion-blur high-frequency-energy < 0.30 fires for this canvas; the glare hotspot is decorative, not the trigger). See `app/services/evaluator.py:120-136` short-circuit branch.

**Existing assets.** `expected.json` (committed; empty array `[]` — no expected values since OCR is not expected to succeed). This task ADDS `label.png` (built by `scripts/build_fixture_04.py`) + `notes.md`.

**Provenance.** synthetic-blur-glare.

**Class balance tag.** spirits.
