# Epoch 8 — Data + Infra Split (L2 v0.2)

> **Parent L1:** [`ttb-label-verification-epoch-8-demo-eval-deploy.md`](./ttb-label-verification-epoch-8-demo-eval-deploy.md)
> **Master L2 (full epoch):** [`ttb-label-verification-epoch-8-l2.md.draft`](./ttb-label-verification-epoch-8-l2.md.draft) — this file extracts the *fixtures + cache + Docker + README + RUNBOOK + per-fixture ACs + deploy smoke* tasks (T1, T4, T8, T9, T10, T11, T13) for parallel execution.
> **Tier:** L2 (file-level + bite-sized TDD steps).
> **For agentic workers:** REQUIRED SUB-SKILL: `parallel-plan-executor`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal.** Land the data + infrastructure half of E8 — fill gaps in the six existing single-label fixtures (with `notes.md` and missing `expected.json` / `label.png`), ship the envelope snapshotter (regression baselines), Dockerfiles + HF Space frontmatter, full README body, DEMO-RUNBOOK skeleton, the FR-704 borderline-band AC test, and the env-gated deploy smoke covering the E7 UI stack.

**Scope.** `fixtures/`, `scripts/`, `Dockerfile*`, `docker-compose*.yml`, `README.md`, `DEMO-RUNBOOK.md`, `demo/cached/`, and the corresponding test surface. Joint close-out tasks T14 (eval-full AC), T15 (fixture-05 batch), T17 (L1 hand-back) are **not** in this split. T16 (recording) is also out of this split (recording is a deliverable owned by post-merge close-out).

**Branch.** `feat/e8-backend` off current `main` (E5/E6 already shipped). The companion eval-pipeline split is on `feat/e8-eval-pipeline`. **Planning assumption (v0.2):** E7 (UI epoch) **also reaches `main` before this split merges** — Dockerfile, README, RUNBOOK, and deploy smoke all assume the E7 island bundle (`app/ui/static/island/`), templates (`app/ui/templates/`), and `app.api.ui` route are present.

**Architecture.** Pure additive layer on top of E5 (Application Service), E6 (batch + override), E7 (UI). Fixtures are file trees under `fixtures/<id>/`; this split **augments** the existing fixtures (which already carry `expected.json` in `ExpectedValue` schema), it does NOT overwrite them. Snapshotted envelopes live at `demo/cached/<id>/envelope.json` for regression baseline. Deployment is a Dockerfile + HF Space README YAML frontmatter. Per **D-DEPLOY-001**: vanity domain (`ttb.aaroncarney.me` via Cloudflare CNAME) is deferred to pilot phase; the demo runs on the default `context31415-ttb-label.hf.space` URL.

**Tech stack.** Python 3.12 / FastAPI / Pydantic v2 (existing) / Pillow (existing) / Docker (HF Spaces SDK).

---

## 1. Coordination with the eval-pipeline split

The eval-pipeline split (`feat/e8-eval-pipeline`) authors `eval/manifest.jsonl` whose lines reference fixture paths owned by this split (e.g. `fixtures/01-spirits-clean/application.json`). **The eval split does not block on this split** — its schema test only validates manifest lines against `ManifestEntry`, not file existence. The actual fixture-presence test (`test_demo_fixture_provenance.py`) is owned here.

Once both splits + E7 merge to `main`, the post-merge close-out runs T14 (live `eval-full` against the live pipeline + these fixtures), T15 (fixture-05 batch — modifies the eval split's `eval/manifest.jsonl` and this split's snapshotter script), T16 (recording — depends on E7 UI), and T17 (L1 hand-back).

**File-overlap audit (vs. eval-pipeline split):**

| File | This split | Eval-pipeline split | Conflict? |
|---|---|---|---|
| `fixtures/{01,02,03,04,06,07}-*/{notes.md,expected.json,label.png}` | augments existing | (none — manifest references paths as strings only) | no |
| `scripts/build_fixture_*.py`, `scripts/snapshot_demo_envelopes.py` | creates | (none) | no |
| `Dockerfile*`, `docker-compose*`, `.dockerignore` | creates | (none) | no |
| `README.md` | creates (frontmatter T4 + body T9) | (none) | no |
| `DEMO-RUNBOOK.md` | creates (T10) + modifies (T13) | (none) | no |
| `demo/cached/**` | creates | (none) | no |
| `tests/test_demo_*`, `test_borderline_band_fr704*`, `test_envelope_snapshot*`, `test_dockerfile_*`, `test_readme_*`, `test_deploy_*` | creates | (none) | no |
| `eval/**` | (none) | creates | no |
| `app/api/eval.py`, `app/main.py` | (none) | creates / modifies | no |
| `tests/test_eval_*` | (none) | creates | no |

✓ Disjoint.

**File-overlap audit (vs. existing `main`):**

| File | Existing on `main` | This split's action | Risk |
|---|---|---|---|
| `fixtures/01-spirits-clean/{label.png, expected.json}` | both present | leave untouched; ADD `notes.md` | none |
| `fixtures/02-bourbon-stones-throw/label.png` | present | leave untouched; ADD `expected.json` + `notes.md` | none |
| `fixtures/03-warning-title-case/expected.json` | present | leave untouched; ADD `label.png` (build script) + `notes.md` | none |
| `fixtures/04-low-res-blurry/expected.json` | present (empty array `[]`) | leave untouched; ADD `label.png` (build script) + `notes.md` | none |
| `fixtures/06-abv-out-of-tolerance/expected.json` | present | leave untouched; ADD `label.png` (build script) + `notes.md` | none |
| `fixtures/07-borderline-confidence/` | empty dir | ADD `expected.json` + `label.png` + `notes.md` | none |
| `tests/test_ac_fixture_coverage.py` | exists (parametrized over 4 fixtures) | T11 ADDS new parametrize cases (fixture-02, fixture-07) — append-only edit | xfail markers preserved |

The split does **not** invent a new `application.json` envelope — there's no consumer for it on `main`. `Application` objects are constructed in tests via `Application(application_id=..., evaluation_id=..., expected_values=_expected_from_fixture(fid))` per the existing `tests/test_ac_fixture_coverage.py` pattern.

---

## 2. File structure

### 2.1 New files

```
fixtures/
  01-spirits-clean/notes.md                                                  [T1]
  02-bourbon-stones-throw/{expected.json, notes.md}                          [T1]
  03-warning-title-case/{label.png, notes.md}                                [T1]
  04-low-res-blurry/{label.png, notes.md}                                    [T1]
  06-abv-out-of-tolerance/{label.png, notes.md}                              [T1]
  07-borderline-confidence/{label.png, expected.json, notes.md}              [T1]

scripts/
  build_fixture_03.py                                                        [T1]
  build_fixture_04.py                                                        [T1]
  build_fixture_06.py                                                        [T1]
  build_fixture_07.py                                                        [T1]
  snapshot_demo_envelopes.py                                                 [T8]

demo/
  cached/.gitkeep                                                            [T8]

Dockerfile              # CPU image, python:3.12-slim                       [T4]
Dockerfile.gpu          # CUDA 12.6 base, paddlepaddle-gpu                  [T4]
docker-compose.yml      # `demo` service (CPU)                              [T4]
docker-compose.gpu.yml  # `demo-gpu` service                                 [T4]
.dockerignore                                                                [T4]
README.md               # HF Space frontmatter + reviewer profiles          [T4, T9]
DEMO-RUNBOOK.md         # T-30/T-5/T-1/T-0 operator timeline                [T10, T13]

tests/
  test_demo_fixture_provenance.py     # presence + ExpectedValue parsing    [T1]
  test_dockerfile_lint.py             # docker artifacts + frontmatter      [T4]
  test_envelope_snapshot.py           # snapshot schema + idempotency       [T8]
  test_readme_content.py              # reviewer profiles + links           [T9]
  test_demo_runbook_present.py        # runbook structure                   [T10]
  test_borderline_band_fr704.py       # FR-704 disposition_confidence band  [T11]
  test_deploy_healthz.py              # deployed URL smoke (env-gated)      [T13]
```

### 2.2 Modified files

```
tests/test_ac_fixture_coverage.py    # T11 appends fixture-02 + fixture-07 parametrize cases
```

> **Why this list shrunk vs. v0.1:** the v0.1 plan invented an `application.json` envelope and a `Evaluator(demo_cache=...)` constructor that don't exist on `main`. v0.2 maps to the actual surface: `Application(application_id, evaluation_id, expected_values)` constructed at test time, `build_evaluator(settings)` from `app/deps.py`, async `evaluate(application, label) -> DispositionEnvelope` with `disposition_confidence: ConfidenceBand` and `fields[]`.

---

## 3. Tasks

### Wave 1 — Roots (4 parallel)

---
### Task 1 — Fixture completion (fill gaps; no overwrites)

**Files:**
- Create: `fixtures/01-spirits-clean/notes.md`
- Create: `fixtures/02-bourbon-stones-throw/expected.json`, `fixtures/02-bourbon-stones-throw/notes.md`
- Create: `fixtures/03-warning-title-case/label.png` (via `scripts/build_fixture_03.py`), `fixtures/03-warning-title-case/notes.md`
- Create: `fixtures/04-low-res-blurry/label.png` (via `scripts/build_fixture_04.py`), `fixtures/04-low-res-blurry/notes.md`
- Create: `fixtures/06-abv-out-of-tolerance/label.png` (via `scripts/build_fixture_06.py`), `fixtures/06-abv-out-of-tolerance/notes.md`
- Create: `fixtures/07-borderline-confidence/label.png` (via `scripts/build_fixture_07.py`), `fixtures/07-borderline-confidence/expected.json`, `fixtures/07-borderline-confidence/notes.md`
- Create: `scripts/build_fixture_03.py`, `scripts/build_fixture_04.py`, `scripts/build_fixture_06.py`, `scripts/build_fixture_07.py`
- Create: `tests/test_demo_fixture_provenance.py`

**Rule (CRITICAL):** Do NOT overwrite existing files (`fixtures/01/{label.png, expected.json}`, `fixtures/02/label.png`, `fixtures/03/expected.json`, `fixtures/04/expected.json`, `fixtures/06/expected.json`). Each build script MUST check the target path before writing — if it exists, skip with a log.

- [ ] **Step 1: Write the failing provenance + parsing test**

```python
# tests/test_demo_fixture_provenance.py
"""Each single-label fixture must have label, expected.json (parses as
ExpectedValue tuple), and notes.md."""
import json
from pathlib import Path

import pytest

from app.schemas.expected import ExpectedValue

SINGLE_LABEL_FIXTURES = ["01-spirits-clean", "02-bourbon-stones-throw",
                          "03-warning-title-case", "04-low-res-blurry",
                          "06-abv-out-of-tolerance", "07-borderline-confidence"]


@pytest.mark.parametrize("fid", SINGLE_LABEL_FIXTURES)
def test_fixture_has_required_files(fid):
    base = Path("fixtures") / fid
    assert (base / "notes.md").is_file(), f"{fid} missing notes.md"
    label = list(base.glob("label.*"))
    assert label, f"{fid} missing label.{{png,jpg}}"


@pytest.mark.parametrize("fid", SINGLE_LABEL_FIXTURES)
def test_expected_json_parses_as_expected_value_tuple(fid):
    """Every expected.json must be a list of dicts that parse as ExpectedValue."""
    sidecar = Path("fixtures") / fid / "expected.json"
    assert sidecar.is_file(), f"{fid} missing expected.json"
    raw = json.loads(sidecar.read_text())
    assert isinstance(raw, list), f"{fid}: expected.json must be a JSON array"
    for entry in raw:
        ExpectedValue(**entry)  # raises if shape is wrong


def test_borderline_fixture_07_has_borderline_band_marker():
    """Fixture-07 notes.md must document its FR-704 borderline-band purpose."""
    notes = (Path("fixtures") / "07-borderline-confidence" / "notes.md").read_text()
    assert "FR-704" in notes
    assert "borderline" in notes.lower()
```

- [ ] **Step 2: Run; expect FAIL**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_demo_fixture_provenance.py -v
```

- [ ] **Step 3: Author `fixtures/01-spirits-clean/notes.md`** (existing files untouched)

```markdown
<!-- fixtures/01-spirits-clean/notes.md -->
# Fixture 01 — Spirits clean

**PRD §8.1 reference.** Clean spirits label, all rules pass.

**Exercises.** Government warning, class/type, ABV tolerance, net contents — all pass.

**Persona signal.** Persona A (high-volume reviewer) — fast happy path; expected ≤ 5 s P99.

**Existing assets.** `label.png` (committed) + `expected.json` (committed; 7 ExpectedValue entries — brand_name through government_warning).

**Provenance.** synthetic-acme-distilling.

**Class balance tag.** spirits.
```

- [ ] **Step 4: Author `fixtures/02-bourbon-stones-throw/expected.json` + notes.md**

```json
[
  {"field_id": "brand_name", "value": "STONE'S THROW", "aliases": ["STONES THROW", "STONE THROW"]},
  {"field_id": "class_type", "value": "STRAIGHT BOURBON WHISKEY"},
  {"field_id": "alcohol_content", "abv_labeled_pct": "45.0", "abv_actual_pct": "45.0"},
  {"field_id": "net_contents", "container_volume_ml": "750"},
  {"field_id": "name_and_address", "value": "STONE'S THROW DISTILLERY LLC, FRANKFORT, KY"},
  {"field_id": "country_of_origin", "value": "USA"},
  {"field_id": "government_warning", "value": "GOVERNMENT WARNING: (1) ACCORDING ..."}
]
```

```markdown
<!-- fixtures/02-bourbon-stones-throw/notes.md -->
# Fixture 02 — STONE'S THROW Bourbon

**PRD §8.1 reference.** Apostrophe-bearing brand; tests Stage-A normalization (PRD-deferred §3.3).

**Exercises.** Brand-match policy with apostrophe-aware aliases; orchestrator's brand_disambig task fires when OCR returns variants.

**Existing assets.** `label.png` (committed). This task ADDS `expected.json` + `notes.md`.

**Provenance.** synthetic-stones-throw.

**Class balance tag.** spirits.
```

- [ ] **Step 5: Build fixture-03 missing label image** (existing `expected.json` untouched)

```python
# scripts/build_fixture_03.py
"""Title-case GOVERNMENT WARNING — exercises FR-200-style case-sensitivity rule.

Idempotent: skips if label.png already exists.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/03-warning-title-case/label.png")


def main() -> None:
    if OUT.is_file():
        print(f"[skip] {OUT} exists")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (480, 480), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME BOURBON", fill="black", font=font)
    draw.text((10, 30), "BOURBON WHISKEY", fill="black", font=font)
    draw.text((10, 50), "ALC. 40% BY VOL.", fill="black", font=font)
    draw.text((10, 70), "750 ML", fill="black", font=font)
    draw.text((10, 100), "ACME DISTILLERIES, FRANKFORT, KY", fill="black", font=font)
    draw.text((10, 120), "Product of USA", fill="black", font=font)
    # FR-200 violation: title-case (Government Warning), not ALL CAPS.
    draw.text((10, 160), "Government Warning: (1) According to the Surgeon", fill="black", font=font)
    draw.text((10, 180), "General, women should not drink alcoholic beverages", fill="black", font=font)
    draw.text((10, 200), "during pregnancy because of the risk of birth defects.", fill="black", font=font)
    img.save(OUT, dpi=(300, 300))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
```

```markdown
<!-- fixtures/03-warning-title-case/notes.md -->
# Fixture 03 — Title-case warning

**PRD §8.1 reference.** Government Warning rendered in title case rather than ALL CAPS — exercises the case-sensitivity check on FR-200.

**Exercises.** Government-warning rule on title-case input.

**Existing assets.** `expected.json` (committed; 7 ExpectedValue entries). This task ADDS `label.png` (built by `scripts/build_fixture_03.py`) + `notes.md`.

**Provenance.** synthetic-acme-titlecase.

**Class balance tag.** spirits.
```

- [ ] **Step 6: Build fixture-04 missing label image** (existing empty `expected.json` untouched)

```python
# scripts/build_fixture_04.py
"""Low-resolution / glare degradation — exercises legibility short-circuit
(Evaluator routes to needs_review when assess_quality returns
needs_better_photo). Idempotent.
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageFont

OUT = Path("fixtures/04-low-res-blurry/label.png")


def main() -> None:
    if OUT.is_file():
        print(f"[skip] {OUT} exists")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # Tiny canvas + blur + glare; quality assessor should flag.
    img = Image.new("RGB", (160, 160), color="white")
    draw = ImageDraw.Draw(img)
    f = ImageFont.load_default()
    draw.text((4, 4), "ACME", fill="black", font=f)
    blurred = img.filter(ImageFilter.GaussianBlur(radius=3.0))
    # Glare hotspot
    hotspot = Image.new("RGBA", blurred.size, (255, 255, 255, 0))
    d2 = ImageDraw.Draw(hotspot)
    d2.ellipse((20, 20, 80, 80), fill=(255, 255, 255, 140))
    composite = Image.alpha_composite(blurred.convert("RGBA"), hotspot).convert("RGB")
    composite.save(OUT, dpi=(72, 72))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
```

```markdown
<!-- fixtures/04-low-res-blurry/notes.md -->
# Fixture 04 — Low-res / glare

**PRD §8.1 reference.** Image quality below threshold — Evaluator's legibility short-circuit fires before rules.

**Exercises.** `app.vision.quality.assess` returns `needs_better_photo`; Evaluator routes disposition to `needs_review` with `ENGINE.EXTRACTION.UNAVAILABLE` reason code (per `app/services/evaluator.py` short-circuit branch).

**Existing assets.** `expected.json` (committed; empty array `[]` — no expected values since OCR is not expected to succeed). This task ADDS `label.png` (built by `scripts/build_fixture_04.py`) + `notes.md`.

**Provenance.** synthetic-blur-glare.

**Class balance tag.** spirits.
```

- [ ] **Step 7: Build fixture-06 missing label image** (existing `expected.json` untouched — note `abv_actual_pct: "42.5"` already encodes the out-of-tolerance application value)

```python
# scripts/build_fixture_06.py
"""ABV value on label conflicts with application by > 1% — exercises FR-400
ABV-tolerance fail. Existing fixtures/06/expected.json carries
abv_labeled_pct=40.0 (label) and abv_actual_pct=42.5 (application);
the rule engine flags the > 1% delta. Idempotent.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/06-abv-out-of-tolerance/label.png")


def main() -> None:
    if OUT.is_file():
        print(f"[skip] {OUT} exists")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (480, 480), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME BOURBON", fill="black", font=font)
    draw.text((10, 30), "BOURBON WHISKEY", fill="black", font=font)
    # Label says 40%, application says 42.5% — delta = 2.5% > 1% threshold.
    draw.text((10, 50), "ALC. 40% BY VOL.", fill="black", font=font)
    draw.text((10, 70), "750 ML", fill="black", font=font)
    draw.text((10, 100), "ACME DISTILLERIES, FRANKFORT, KY", fill="black", font=font)
    draw.text((10, 120), "Product of USA", fill="black", font=font)
    draw.text((10, 160), "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON", fill="black", font=font)
    draw.text((10, 180), "GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES", fill="black", font=font)
    draw.text((10, 200), "DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS.", fill="black", font=font)
    img.save(OUT, dpi=(300, 300))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
```

```markdown
<!-- fixtures/06-abv-out-of-tolerance/notes.md -->
# Fixture 06 — ABV out-of-tolerance

**PRD §8.1 reference.** ABV delta on label vs. application > 1% — exercises FR-400 ABV-tolerance fail; demoes the override path (AC-FR-803, owned by E7).

**Exercises.** ABV-tolerance rule with delta = 2.5% (labeled 40%, application 42.5%).

**Existing assets.** `expected.json` (committed; 7 ExpectedValue entries with the out-of-tolerance values). This task ADDS `label.png` (built by `scripts/build_fixture_06.py`) + `notes.md`.

**Provenance.** synthetic-acme-abv-mismatch.

**Class balance tag.** spirits.
```

- [ ] **Step 8: Build fixture-07 — new fixture (label + expected + notes)**

```python
# scripts/build_fixture_07.py
"""Borderline-confidence fixture — mid-confidence band on at least one field.
Pillow output is deterministic given pinned dependencies. Idempotent.
"""
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageFont

OUT = Path("fixtures/07-borderline-confidence/label.png")


def main() -> None:
    if OUT.is_file():
        print(f"[skip] {OUT} exists")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (480, 480), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME BOURBON", fill="black", font=font)
    draw.text((10, 30), "BOURBON WHISKEY", fill="black", font=font)
    draw.text((10, 50), "ALC. 40% BY VOL.", fill="black", font=font)
    draw.text((10, 70), "750 ML", fill="black", font=font)
    draw.text((10, 100), "ACME DISTILLERIES, FRANKFORT, KY", fill="black", font=font)
    # Light blur in the warning region — should land confidence in mid-band.
    warning_block = Image.new("RGB", (470, 80), color="white")
    wd = ImageDraw.Draw(warning_block)
    wd.text((0, 0), "GOVERNMENT WARNING: (1) ACCORDING TO THE SURGEON", fill="black", font=font)
    wd.text((0, 20), "GENERAL, WOMEN SHOULD NOT DRINK ALCOHOLIC BEVERAGES", fill="black", font=font)
    wd.text((0, 40), "DURING PREGNANCY BECAUSE OF THE RISK OF BIRTH DEFECTS.", fill="black", font=font)
    blurred = warning_block.filter(ImageFilter.GaussianBlur(radius=0.8))
    img.paste(blurred, (10, 160))
    img.save(OUT, dpi=(300, 300))
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()
```

```json
// fixtures/07-borderline-confidence/expected.json
[
  {"field_id": "brand_name", "value": "ACME BOURBON", "aliases": ["ACME"]},
  {"field_id": "class_type", "value": "BOURBON WHISKEY"},
  {"field_id": "alcohol_content", "abv_labeled_pct": "40.0", "abv_actual_pct": "40.0"},
  {"field_id": "net_contents", "container_volume_ml": "750"},
  {"field_id": "name_and_address", "value": "ACME DISTILLERIES, FRANKFORT, KY"},
  {"field_id": "country_of_origin", "value": "USA"},
  {"field_id": "government_warning", "value": "GOVERNMENT WARNING: (1) ACCORDING ..."}
]
```

```markdown
<!-- fixtures/07-borderline-confidence/notes.md -->
# Fixture 07 — Borderline confidence (FR-704)

**PRD §8.1 reference.** Mid-confidence band on the warning field — Evaluator's `disposition_confidence.band == "medium"` per ARCH §6 / D-017 (numeric is the **min** over per-field confidences).

**Exercises.** FR-704 confidence aggregation; reviewer-attention prompt.

**Existing assets.** None (this task creates `label.png`, `expected.json`, `notes.md`).

**Provenance.** synthetic-borderline-derived-from-01.

**Class balance tag.** spirits.

**Borderline-band:** YES (this fixture is the FR-704 AC anchor).
```

- [ ] **Step 9: Build images for fixtures 03/04/06/07**

```bash
cd /home/context/projects/takehome-e8backend
uv run --python 3.12 python scripts/build_fixture_03.py
uv run --python 3.12 python scripts/build_fixture_04.py
uv run --python 3.12 python scripts/build_fixture_06.py
uv run --python 3.12 python scripts/build_fixture_07.py
```

- [ ] **Step 10: Run provenance test; expect PASS**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_demo_fixture_provenance.py -v
```

- [ ] **Step 11: Commit**

```bash
cd /home/context/projects/takehome-e8backend
git add fixtures/01-spirits-clean/notes.md \
        fixtures/02-bourbon-stones-throw/expected.json fixtures/02-bourbon-stones-throw/notes.md \
        fixtures/03-warning-title-case/label.png fixtures/03-warning-title-case/notes.md \
        fixtures/04-low-res-blurry/label.png fixtures/04-low-res-blurry/notes.md \
        fixtures/06-abv-out-of-tolerance/label.png fixtures/06-abv-out-of-tolerance/notes.md \
        fixtures/07-borderline-confidence/ \
        scripts/build_fixture_03.py scripts/build_fixture_04.py \
        scripts/build_fixture_06.py scripts/build_fixture_07.py \
        tests/test_demo_fixture_provenance.py
git commit -m "feat(fixtures): fill gaps in single-label fixtures + provenance test (E8 T1)"
```

---
### Task 4 — Dockerfiles + compose + HF Space frontmatter

**Files:**
- Create: `Dockerfile`, `Dockerfile.gpu`, `docker-compose.yml`, `docker-compose.gpu.yml`, `.dockerignore`
- Create: `tests/test_dockerfile_lint.py`
- Modify: `README.md` (HF Space YAML frontmatter only — body rewrite is T9)

**E7 awareness:** the built island bundle lives at `app/ui/static/island/` (committed). Templates live at `app/ui/templates/`. `COPY app ./app` in the Dockerfile pulls both. `.dockerignore` excludes `frontend/` (Vite source — not needed at runtime).

- [ ] **Step 1: Write a Docker-build smoke test**

```python
# tests/test_dockerfile_lint.py
"""Smoke-lint the Dockerfile + frontmatter without invoking docker."""
from pathlib import Path


def test_cpu_dockerfile_uses_python_312_slim():
    content = Path("Dockerfile").read_text()
    assert "FROM python:3.12-slim" in content
    assert "uv sync" in content
    assert "CMD" in content and "uvicorn" in content
    assert "0.0.0.0" in content and "8000" in content
    # E7 island bundle ships with `COPY app ./app`
    assert "COPY app ./app" in content


def test_gpu_dockerfile_uses_cuda():
    content = Path("Dockerfile.gpu").read_text()
    assert "nvidia/cuda" in content
    assert "uv sync" in content and "--extra gpu" in content


def test_compose_files_exist_and_share_model_snapshot():
    cpu = Path("docker-compose.yml").read_text()
    gpu = Path("docker-compose.gpu.yml").read_text()
    assert "LLM_MODEL_SNAPSHOT" in cpu and "LLM_MODEL_SNAPSHOT" in gpu
    import re
    cpu_pin = re.search(r"LLM_MODEL_SNAPSHOT.*\$\{LLM_MODEL_SNAPSHOT:-([^}]+)\}", cpu)
    gpu_pin = re.search(r"LLM_MODEL_SNAPSHOT.*\$\{LLM_MODEL_SNAPSHOT:-([^}]+)\}", gpu)
    assert cpu_pin and gpu_pin and cpu_pin.group(1) == gpu_pin.group(1)


def test_dockerignore_excludes_frontend_source():
    content = Path(".dockerignore").read_text()
    lines = [ln.strip() for ln in content.split("\n")]
    assert "frontend/" in lines or "frontend" in lines
    assert any("node_modules" in ln for ln in lines)


def test_readme_has_hf_frontmatter():
    content = Path("README.md").read_text()
    assert content.startswith("---\n")
    assert "sdk: docker" in content
    assert "app_port: 8000" in content
    assert "hardware: cpu-basic" in content
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Author `Dockerfile` (CPU)**

```dockerfile
# Dockerfile — CPU image for HF Spaces (cpu-basic per D-015 / D-DEPLOY-003).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# E7 island bundle + templates ship under app/ui/. `COPY app ./app` is sufficient.
COPY app ./app
COPY rules ./rules
COPY assets ./assets
COPY fixtures ./fixtures
COPY demo ./demo

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Author `Dockerfile.gpu`**

```dockerfile
# Dockerfile.gpu — CUDA 12.6 base for the local-mode GPU profile (ARCH §19.3)
FROM nvidia/cuda:12.6.0-runtime-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3-pip build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra gpu

COPY app ./app
COPY rules ./rules
COPY assets ./assets
COPY fixtures ./fixtures
COPY demo ./demo

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Author compose files**

```yaml
# docker-compose.yml
services:
  demo:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LLM_MODEL_SNAPSHOT: ${LLM_MODEL_SNAPSHOT:-gpt-4o-2024-08-06}
      ORCHESTRATOR_BACKEND: ${ORCHESTRATOR_BACKEND:-openai}
      LOOKAHEAD_K: ${LOOKAHEAD_K:-3}
      VISION_MODE: ${VISION_MODE:-cloud}
      DEMO_CACHE: ${DEMO_CACHE:-1}
```

```yaml
# docker-compose.gpu.yml
services:
  demo-gpu:
    build:
      context: .
      dockerfile: Dockerfile.gpu
    ports:
      - "8000:8000"
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LLM_MODEL_SNAPSHOT: ${LLM_MODEL_SNAPSHOT:-gpt-4o-2024-08-06}
      ORCHESTRATOR_BACKEND: ${ORCHESTRATOR_BACKEND:-openai}
      LOOKAHEAD_K: ${LOOKAHEAD_K:-3}
      VISION_MODE: ${VISION_MODE:-auto}
      DEMO_CACHE: ${DEMO_CACHE:-1}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

> **Model-snapshot pin:** Both compose files default to `gpt-4o-2024-08-06`, matching D-DEPLOY-003 and the DEMO-RUNBOOK's HF Space variable. Override via env at deploy time.

- [ ] **Step 6: Author `.dockerignore`**

```
.git/
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
node_modules/
frontend/
docs/
tests/
*.md
!README.md
```

> **Why `frontend/`?** E7's React/Vite source. The built bundle is committed at `app/ui/static/island/` and gets shipped via `COPY app ./app`. Excluding the source dir keeps the Docker context small.

- [ ] **Step 7: Add HF Space frontmatter to `README.md`** (full body is T9)

```markdown
---
title: TTB Label Verification
emoji: 🍷
colorFrom: indigo
colorTo: red
sdk: docker
app_port: 8000
hardware: cpu-basic
pinned: false
---

# TTB Label Verification (prototype)

(Body content authored by T9.)
```

- [ ] **Step 8: Run lint; expect PASS**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_dockerfile_lint.py -v
```

- [ ] **Step 9: Commit**

```bash
cd /home/context/projects/takehome-e8backend
git add Dockerfile Dockerfile.gpu docker-compose.yml docker-compose.gpu.yml \
        .dockerignore README.md tests/test_dockerfile_lint.py
git commit -m "feat(deploy): Dockerfile + compose + HF Space frontmatter (E8 T4)"
```

---
### Task 8 — Demo envelope snapshotter (regression baseline)

**Files:**
- Create: `scripts/snapshot_demo_envelopes.py`
- Create: `demo/cached/.gitkeep`
- Create: `tests/test_envelope_snapshot.py`

> **Reframe vs. v0.1:** the v0.1 task referenced a fictional `audit_trail.calls` shape and `Evaluator(demo_cache=...)` flag that don't exist on `main`. The actual surface: `Evaluator` already supports a `cache: SessionCache | None = None` injection; demo-mode cache pre-population is a deferred follow-up (out of scope for this split). v0.2 ships the simpler **envelope snapshotter** — a regression-baseline tool that runs the live evaluator per fixture and writes the resulting `DispositionEnvelope` JSON to `demo/cached/<fid>/envelope.json`. Schema-validated on read; idempotent on canonicalization.

- [ ] **Step 1: Write the schema + idempotency test**

```python
# tests/test_envelope_snapshot.py
"""Envelope snapshots in demo/cached/<fid>/envelope.json must parse as
DispositionEnvelope; canonicalization is idempotent on unchanged inputs.
"""
import json
import subprocess
from pathlib import Path

import pytest

from app.schemas.wire.disposition import DispositionEnvelope


def test_committed_snapshots_parse_as_disposition_envelope():
    """Any envelope.json committed under demo/cached/ must validate."""
    root = Path("demo/cached")
    if not root.is_dir():
        pytest.skip("demo/cached not yet populated")
    for env_path in root.glob("*/envelope.json"):
        DispositionEnvelope.model_validate_json(env_path.read_text())


def test_canonicalization_idempotent_on_unchanged_snapshot(tmp_path):
    """Re-canonicalizing an existing snapshot produces byte-identical output."""
    target = tmp_path / "demo" / "cached" / "01-spirits-clean"
    target.mkdir(parents=True)
    # Seed a minimal valid envelope JSON for round-trip test.
    seed = {
        "evaluation_id": "EV-test",
        "label_ref": "01-spirits-clean",
        "disposition": "needs_review",
        "disposition_confidence": {"band": "low", "numeric": 0.5},
        "fields": [],
        "audit_trail": {
            "evaluation_id": "EV-test",
            "rule_set_version": "0.1.0",
            "input_hash": "abc",
            "output_hash": "def",
            "started_at": "2026-05-04T00:00:00+00:00",
            "completed_at": "2026-05-04T00:00:01+00:00",
            "per_rule_trace": [],
            "overrides": [],
        },
        "metrics": {"total_duration_ms": 1, "per_rule": []},
    }
    (target / "envelope.json").write_text(
        json.dumps(seed, indent=2, sort_keys=True) + "\n"
    )
    # Run snapshotter in --canonicalize-only mode against tmp_path.
    cmd = ["python", "scripts/snapshot_demo_envelopes.py",
           "--root", str(tmp_path / "demo" / "cached"),
           "--fixtures", "01-spirits-clean",
           "--canonicalize-only"]
    subprocess.run(cmd, check=True)
    first = (target / "envelope.json").read_bytes()
    subprocess.run(cmd, check=True)
    second = (target / "envelope.json").read_bytes()
    assert first == second
```

- [ ] **Step 2: Run; expect FAIL (script + .gitkeep missing)**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_envelope_snapshot.py -v
```

- [ ] **Step 3: Implement `scripts/snapshot_demo_envelopes.py`**

```python
#!/usr/bin/env python3
"""Demo envelope snapshotter — regression baseline for fixture dispositions.

Modes:
  default (no flags):       For each fixture with both label and expected.json,
                            run `build_evaluator(settings).evaluate(...)` and write
                            the resulting DispositionEnvelope JSON to
                            demo/cached/<fid>/envelope.json (canonicalized,
                            sort_keys=True, indent=2, trailing newline).
  --canonicalize-only:      Read each existing envelope.json, parse against
                            DispositionEnvelope, write back canonicalized.
                            Used in CI to verify byte-identical idempotency.
  --root <path>:            Override demo/cached root (testing only).

Notes:
  - Live evaluator path requires OPENAI_API_KEY (or a mock orchestrator). The
    DEMO_CACHE=1 env-var integration with running app is deferred (see L1
    deviations).
  - Fixtures with empty expected.json (e.g. fixture-04) still produce a valid
    envelope (legibility short-circuit branch). All fixtures are runnable.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.schemas.wire.disposition import DispositionEnvelope

DEFAULT_FIXTURES = (
    "01-spirits-clean", "02-bourbon-stones-throw", "03-warning-title-case",
    "04-low-res-blurry", "06-abv-out-of-tolerance", "07-borderline-confidence",
)


def _canonical(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


async def _live_envelope(fixture_id: str) -> DispositionEnvelope:
    """Run the live evaluator for one fixture and return its envelope."""
    import json as _json

    from app.config import Settings
    from app.deps import build_evaluator
    from app.schemas.application import Application
    from app.schemas.expected import ExpectedValue
    from app.schemas.label import Label

    settings = Settings()
    evaluator = build_evaluator(settings)

    sidecar = Path("fixtures") / fixture_id / "expected.json"
    raw = _json.loads(sidecar.read_text()) if sidecar.is_file() else []
    expected = tuple(ExpectedValue(**e) for e in raw)

    img_png = Path("fixtures") / fixture_id / "label.png"
    img_jpg = Path("fixtures") / fixture_id / "label.jpg"
    if img_png.is_file():
        img, content_type = img_png, "image/png"
    elif img_jpg.is_file():
        img, content_type = img_jpg, "image/jpeg"
    else:
        raise SystemExit(f"[err] {fixture_id}: no label.png or .jpg")

    app = Application(application_id=f"A-{fixture_id}",
                      evaluation_id=f"EV-{fixture_id}",
                      expected_values=expected)
    label = Label(label_id=fixture_id, batch_id="snapshot",
                  image_bytes=img.read_bytes(), content_type=content_type,
                  face_tag="front", dimensions=None)
    return await evaluator.evaluate(application=app, label=label)


def canonicalize_only(root: Path, fixture_id: str) -> None:
    target = root / fixture_id / "envelope.json"
    if not target.is_file():
        print(f"[skip] {fixture_id}: no envelope.json (run without --canonicalize-only first)")
        return
    parsed = DispositionEnvelope.model_validate_json(target.read_text())
    canonical = _canonical(json.loads(parsed.model_dump_json()))
    target.write_text(canonical)
    print(f"[ok] {fixture_id}: canonicalized")


def snapshot_live(root: Path, fixture_id: str) -> None:
    target_dir = root / fixture_id
    target_dir.mkdir(parents=True, exist_ok=True)
    envelope = asyncio.run(_live_envelope(fixture_id))
    target = target_dir / "envelope.json"
    canonical = _canonical(json.loads(envelope.model_dump_json()))
    target.write_text(canonical)
    print(f"[ok] {fixture_id}: snapshot written ({target})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", nargs="+", default=list(DEFAULT_FIXTURES))
    parser.add_argument("--root", type=Path, default=Path("demo/cached"))
    parser.add_argument("--canonicalize-only", action="store_true",
                        help="Skip live evaluator; just re-canonicalize existing JSON")
    args = parser.parse_args()
    for fid in args.fixtures:
        if args.canonicalize_only:
            canonicalize_only(args.root, fid)
        else:
            snapshot_live(args.root, fid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Create `demo/cached/.gitkeep`**

```bash
mkdir -p demo/cached && touch demo/cached/.gitkeep
```

- [ ] **Step 5: Run; expect PASS**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_envelope_snapshot.py -v
```

> **Note:** the test `test_committed_snapshots_parse_as_disposition_envelope` PASSES (skips, since `demo/cached/` only contains `.gitkeep` at this point). Live snapshots are produced post-merge by T14 with `OPENAI_API_KEY` set.

- [ ] **Step 6: Commit**

```bash
cd /home/context/projects/takehome-e8backend
git add scripts/snapshot_demo_envelopes.py demo/cached/.gitkeep \
        tests/test_envelope_snapshot.py
git commit -m "feat(scripts): demo envelope snapshotter + idempotency test (E8 T8)"
```

---
### Task 10 — DEMO-RUNBOOK skeleton

**Files:**
- Create: `DEMO-RUNBOOK.md`
- Create: `tests/test_demo_runbook_present.py`

**E7 awareness:** narration sections that previously carried `[E7]` placeholders (Stage 6 override demo, Stage 5 batch SSE) are now real — E7 lands in the same merge cycle.

- [ ] **Step 1: Write the structure test**

```python
# tests/test_demo_runbook_present.py
from pathlib import Path


def test_runbook_has_all_timing_sections():
    content = Path("DEMO-RUNBOOK.md").read_text()
    for marker in ("T-30", "T-5", "T-1", "T-0"):
        assert marker in content, f"DEMO-RUNBOOK missing {marker} section"


def test_runbook_documents_failure_recovery():
    content = Path("DEMO-RUNBOOK.md").read_text()
    assert "Failure recovery" in content or "failure recovery" in content


def test_runbook_documents_six_stage_path():
    content = Path("DEMO-RUNBOOK.md").read_text()
    for marker in ("Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5", "Stage 6"):
        assert marker in content, f"DEMO-RUNBOOK missing {marker}"
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Author `DEMO-RUNBOOK.md`**

```markdown
# Demo Runbook

Operator timeline for the 5-minute recorded walkthrough (PRD §10.2).

> **Status note.** This runbook assumes E5 (Application Service), E6 (batch + override), and E7 (UI) are all on `main`. The HF Space provisioning section and recording protocol live below.

---

## T-30 minutes — environment check

```bash
# 1. Deployment reachable with valid TLS
curl -I https://context31415-ttb-label.hf.space/healthz
# Expect: HTTP/2 200 with valid HF-issued cert (no --insecure flag)

# 2. UI shell renders
curl -fsSL https://context31415-ttb-label.hf.space/ | head -20
# Expect: HTML, includes the island bundle script tag

# 3. API credentials valid
curl https://context31415-ttb-label.hf.space/healthz | jq '.mode.orchestrator'
# Expect: "openai"

# 4. Repo clean
gh release list && git status
# Expect: working tree clean, latest release tagged

# 5. Envelope snapshots fresh (regression baseline)
uv run --python 3.12 python scripts/snapshot_demo_envelopes.py --canonicalize-only
git diff --quiet demo/cached/
# Expect: no diff
```

## T-5 minutes — pre-warm

```bash
# Sentinel pipeline against fixture-01
curl https://context31415-ttb-label.hf.space/healthz
# Expect: 200 within 2 s (vision model + LLM client warm)
```

## T-1 minute — dry run

Open https://context31415-ttb-label.hf.space in a fresh browser tab. Drop fixture-01 onto the upload area. Confirm a `pass` disposition appears within 5 s.

## T-0 — begin recording

Six-stage path per PRD §10.2:

1. **Stage 1 — Upload fixture-01** (clean spirits). Disposition: `pass`. Show the citation chips backing each rule.
2. **Stage 2 — Upload fixture-02** (STONE'S THROW Bourbon). Disposition: `pass`. Narrate the apostrophe-aware brand normalization (PRD-deferred §3.3) — orchestrator's brand_disambig task fires.
3. **Stage 3 — Upload fixture-03** (title-case warning). Disposition: `fail` on the case-sensitivity rule. Show the reason code surfaced in `audit_trail.per_rule_trace`.
4. **Stage 4 — Upload fixture-04** (low-res / glare). Disposition: `needs_review`. Show the legibility short-circuit prompting re-upload.
5. **Stage 5 — Upload fixture-05** (50-label batch, post-merge T15). Show the SSE stream, queue position, and lookahead progress. Trigger the M-of-N anomaly advisory by submitting same-reason fails.
6. **Stage 6 — Override on fixture-06** (ABV out-of-tolerance). Three-keystroke override demo (AC-FR-803). Show the audit-trail entry with reason code + reviewer ID + timestamp.

Bonus (deployed but cut from recording for time): fixture-07 borderline-band `needs_review` with the medium-confidence band surfaced in `disposition_confidence`.

## Failure recovery

| Scenario | Recovery |
|---|---|
| Network drops mid-batch | SSE auto-reconnect from `current_index`; reviewer continues |
| LLM timeout | The Evaluator's whole-eval timeout (5 s) routes to `needs_review` with `ENGINE.SLA.TIMEOUT` reason code. Cached envelope baselines under `demo/cached/` document expected dispositions if the live demo needs a fallback narrative. |
| OCR low-confidence on a demo image | Switch to fixture-01 as fallback; document image quality is a separate FR-700 demo |
| HF Space cold-start exceeds 5 s | T-5 pre-warm absorbs this; if it recurs mid-demo, point at the `/healthz` curl in T-30 as evidence the deploy is healthy |
| Cache stale relative to active LLM_MODEL_SNAPSHOT | `uv run --python 3.12 python scripts/snapshot_demo_envelopes.py` (requires OPENAI_API_KEY); commit the diff |

## Re-record protocol

If the recording goes long or the cursor lands on the wrong control, re-shoot following the same six-stage path. The narration script lives at `docs/demo-narration.md` (authored by post-merge T16 along with the recording itself).
```

- [ ] **Step 4: Run; expect PASS**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_demo_runbook_present.py -v
```

- [ ] **Step 5: Commit**

```bash
cd /home/context/projects/takehome-e8backend
git add DEMO-RUNBOOK.md tests/test_demo_runbook_present.py
git commit -m "docs(runbook): T-30/T-5/T-1/T-0 skeleton + six-stage path (E8 T10)"
```

---

### Wave 2 — Body docs + fixture ACs (2 parallel; depend on T4 + T1)

---
### Task 9 — README upgrade

**Files:**
- Modify: `README.md` (preserve T4's HF Space frontmatter; replace placeholder body)
- Create: `tests/test_readme_content.py`

**E7 awareness:** the React island bundle is committed under `app/ui/static/island/` so reviewer profiles B/C don't need a `pnpm build` step — the deployed app serves the pre-built bundle.

- [ ] **Step 1: Write the README content test**

```python
# tests/test_readme_content.py
from pathlib import Path


def test_readme_preserves_hf_frontmatter():
    """T4's frontmatter must survive T9's body edit."""
    content = Path("README.md").read_text()
    assert content.startswith("---\n")
    for marker in ("sdk: docker", "app_port: 8000", "hardware: cpu-basic"):
        assert marker in content


def test_readme_has_reviewer_profiles():
    content = Path("README.md").read_text()
    assert "Profile A" in content and "Profile B" in content and "Profile C" in content
    assert "WSL2" in content


def test_readme_links_decisions_and_runbook():
    content = Path("README.md").read_text()
    for ref in ("docs/PRD.md", "docs/ARCHITECTURE.md", "docs/03-decisions.md", "DEMO-RUNBOOK.md"):
        assert ref in content, f"README missing link to {ref}"


def test_readme_has_loom_placeholder():
    content = Path("README.md").read_text()
    # Placeholder until post-merge T16 records and replaces with the real URL.
    assert "loom.com" in content.lower() or "TODO-LOOM" in content
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Author the README body**

```markdown
---
title: TTB Label Verification
emoji: 🍷
colorFrom: indigo
colorTo: red
sdk: docker
app_port: 8000
hardware: cpu-basic
pinned: false
---

# TTB Label Verification (prototype)

AI-powered alcohol label verification against TTB regulations. Returns a draft
disposition (`pass` / `fail` / `needs_review`) for a COLA label in ≤5 s with
citation-grounded reasoning.

> **Live demo:** https://context31415-ttb-label.hf.space · **Recording:** `TODO-LOOM` (5 min)

## One-command setup (reviewer profiles)

The React island bundle is pre-built and committed under `app/ui/static/island/`, so reviewer profiles B/C do **not** need a frontend toolchain.

### Profile A — WSL2 + GPU (full local-mode path, includes frontend rebuild)
```bash
git clone https://github.com/aaroncarney/ttb-label-verification && cd ttb-label-verification
uv sync --extra gpu
# Optional — only needed if you want to rebuild the UI bundle:
# (cd frontend && pnpm install && pnpm build)
uv run task demo
# Open http://localhost:8000
```

### Profile B — macOS, no GPU (cloud-mode only)
```bash
git clone https://github.com/aaroncarney/ttb-label-verification && cd ttb-label-verification
uv sync
export OPENAI_API_KEY=sk-...
uv run task demo
# Open http://localhost:8000
```

### Profile C — Linux, no GPU (cloud-mode only)
Same as Profile B.

## Headline trade-off

This prototype optimizes for **citation-grounded transparency** over **end-to-end automation**. The deterministic rule core (`rules/`) makes pass/fail decisions; the AI surface (Vision + Orchestrator) extracts evidence and proposes explanations but never decides.

The economic case (`docs/research/T11-output.md`) and policy case (`docs/research/T7-output.md`) settle the trade-off range.

## Documentation

- [Business requirements](docs/BRD.md)
- [Product requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Decisions log](docs/03-decisions.md)
- [Demo runbook](DEMO-RUNBOOK.md) — for the recorded walkthrough

## Eval

```bash
uv run task eval-smoke   # ~20 labels, < 60 s
uv run task eval-full    # ~50 labels, several minutes (merge-to-main gate)
```

The `/eval` route is `DEV_MODE`-gated.

## License

Prototype; not for production use.
```

- [ ] **Step 4: Run; expect PASS**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_readme_content.py -v
```

- [ ] **Step 5: Commit**

```bash
cd /home/context/projects/takehome-e8backend
git add README.md tests/test_readme_content.py
git commit -m "docs(readme): reviewer profiles + headline tradeoff (E8 T9)"
```

---
### Task 11 — Borderline-band FR-704 test + fixture-02/07 AC cases

**Files:**
- Create: `tests/test_borderline_band_fr704.py`
- Modify: `tests/test_ac_fixture_coverage.py` (append fixture-02 + fixture-07 parametrize cases)

> **Reframe vs. v0.1:** the v0.1 task duplicated the existing `test_ac_fixture_coverage.py` against a fictional `Evaluator` API. v0.2 extends the existing test (the canonical pattern) and adds a dedicated FR-704 borderline-band test. xfail markers preserve the OCR-replay gap pattern.

- [ ] **Step 1: Write the FR-704 borderline-band test**

```python
# tests/test_borderline_band_fr704.py
"""FR-704 / D-017: fixture-07 must produce disposition_confidence.band == "medium"
when OCR returns mid-confidence on the warning field."""
import json
from pathlib import Path

import pytest

from app.config import Settings
from app.deps import build_evaluator
from app.schemas.application import Application
from app.schemas.expected import ExpectedValue
from app.schemas.label import Label


_OCR_REPLAY_GAP = pytest.mark.xfail(
    reason="upstream gap: CloudVisionExtractor has no test-replay seam (E3 owns); "
           "remove when OCR replay lands. The borderline-band assertion is the AC "
           "contract — passes once OCR resolves mid-confidence values.",
    strict=False,
)


@pytest.mark.asyncio
@_OCR_REPLAY_GAP
async def test_fixture_07_borderline_band():
    settings = Settings()
    evaluator = build_evaluator(settings)
    expected_raw = json.loads(
        (Path("fixtures") / "07-borderline-confidence" / "expected.json").read_text()
    )
    application = Application(
        application_id="A-fr704",
        evaluation_id="EV-07-borderline",
        expected_values=tuple(ExpectedValue(**e) for e in expected_raw),
    )
    img = Path("fixtures") / "07-borderline-confidence" / "label.png"
    label = Label(label_id="07-borderline", batch_id="fr704",
                  image_bytes=img.read_bytes(), content_type="image/png",
                  face_tag="front", dimensions=None)
    envelope = await evaluator.evaluate(application=application, label=label)
    # FR-704: medium band — numeric is min over per-field confidences (D-017)
    assert envelope.disposition_confidence.band == "medium", (
        f"expected medium band, got {envelope.disposition_confidence.band} "
        f"(numeric={envelope.disposition_confidence.numeric})"
    )
    assert 0.55 <= envelope.disposition_confidence.numeric <= 0.75
    # FR-704: lowest-confidence field surfaced — verify at least one field is
    # in the medium-or-low band (i.e., the borderline driver).
    has_borderline_field = any(
        f.field_confidence.band in ("medium", "low") for f in envelope.fields
    )
    assert has_borderline_field, (
        "expected at least one field with medium/low confidence (the FR-704 driver)"
    )
```

- [ ] **Step 2: Append fixture-02 + fixture-07 parametrize cases to existing AC test**

Edit `tests/test_ac_fixture_coverage.py`. The current file parametrizes over fixtures 01/03/04/06 (line 60-65). Append two new rows to the parametrize list:

```python
# In tests/test_ac_fixture_coverage.py, replace the existing @pytest.mark.parametrize
# block at line 60-65 with:

@pytest.mark.asyncio
@pytest.mark.parametrize("fixture_id, expected_disposition, expected_field_count", [
    pytest.param("01-spirits-clean",        "pass",         7, marks=_UPSTREAM_VISION_REPLAY),
    pytest.param("02-bourbon-stones-throw", "pass",         7, marks=_UPSTREAM_VISION_REPLAY),
    pytest.param("03-warning-title-case",   "fail",         7, marks=_UPSTREAM_VISION_REPLAY),
    pytest.param("04-low-res-blurry",       "needs_review", 0),
    pytest.param("06-abv-out-of-tolerance", "fail",         7, marks=_UPSTREAM_VISION_REPLAY),
    pytest.param("07-borderline-confidence", "needs_review", 7, marks=_UPSTREAM_VISION_REPLAY),
])
async def test_ac_fixture_disposition(fixture_id, expected_disposition, expected_field_count):
    # body unchanged
```

> **Why xfail on fixture-02 and fixture-07?** Same reason as the existing 01/03/06: `CloudVisionExtractor` has no deterministic test-replay seam (E3 gap noted in the existing comment block at line 44-56). Once OCR replay lands, the xfails go strict and the AC contract holds.

- [ ] **Step 3: Run; expect xfail (06 already xfail) + new tests xfail**

```bash
cd /home/context/projects/takehome-e8backend && uv run --python 3.12 pytest tests/test_borderline_band_fr704.py tests/test_ac_fixture_coverage.py -v
```

Expected: existing 4 fixtures + 2 new fixtures all xfail (or pass for fixture-04 short-circuit); FR-704 test xfails until OCR replay lands.

- [ ] **Step 4: Commit**

```bash
cd /home/context/projects/takehome-e8backend
git add tests/test_borderline_band_fr704.py tests/test_ac_fixture_coverage.py
git commit -m "test(fixtures): FR-704 borderline-band + fixture-02/07 AC cases (E8 T11)"
```

---

### Wave 3 — Deploy smoke (1 task; depends on T4 + T10)

---
### Task 13 — HF Space deploy + UI smoke

**Files:**
- Modify: `DEMO-RUNBOOK.md` (append HF Space provisioning section)
- Create: `tests/test_deploy_healthz.py`

**E7 awareness:** smoke now verifies `/` (UI shell) and `/static/island/single.js` (asset serving) in addition to `/healthz`. Confirms the full stack — backend + UI bundle — is reachable post-deploy.

- [ ] **Step 1: Write the smoke test**

```python
# tests/test_deploy_healthz.py
"""Hits the deployed URL. Skipped unless TTB_DEPLOY_URL is set."""
import os

import httpx
import pytest


@pytest.fixture
def deploy_url() -> str:
    url = os.environ.get("TTB_DEPLOY_URL")
    if not url:
        pytest.skip("TTB_DEPLOY_URL env var not set; skipping live deploy smoke")
    return url.rstrip("/")


def test_deployed_healthz_200(deploy_url):
    r = httpx.get(f"{deploy_url}/healthz", timeout=10.0)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_deployed_ui_shell_200(deploy_url):
    """E7 single-label UI shell route returns HTML."""
    r = httpx.get(f"{deploy_url}/", timeout=10.0)
    assert r.status_code == 200
    # The shell is rendered Jinja2 + island bundle reference.
    assert "<html" in r.text.lower() or "<!doctype" in r.text.lower()


def test_deployed_static_island_bundle_200(deploy_url):
    """E7 island bundle is served from /static/island/."""
    r = httpx.get(f"{deploy_url}/static/island/single.js", timeout=10.0)
    assert r.status_code == 200
    # JS content-type or any reasonable text/JS detection
    ct = r.headers.get("content-type", "").lower()
    assert "javascript" in ct or "text" in ct, f"unexpected content-type {ct!r}"


def test_deployed_tls_chain_valid(deploy_url):
    """HF-issued cert; no insecure flag."""
    r = httpx.get(f"{deploy_url}/healthz", verify=True, timeout=10.0)
    assert r.status_code == 200
```

- [ ] **Step 2: Append HF Space setup section to `DEMO-RUNBOOK.md`** (no Cloudflare; per D-DEPLOY-001)

Append to `DEMO-RUNBOOK.md`:

```markdown

---

## Initial deployment setup (one-time, executed 2026-05-04)

1. **HF Space create** — `hf repos create Context31415/ttb-label --type space --space-sdk docker --public`
2. **Push** — `git remote add hf https://huggingface.co/spaces/Context31415/ttb-label && git push hf main`
3. **Variables** (set via API at provisioning time; verify in HF Space → Settings → Variables and secrets):
   - `ORCHESTRATOR_BACKEND` = `openai`
   - `LLM_MODEL_SNAPSHOT` = `gpt-4o-2024-08-06`
   - `LOOKAHEAD_K` = `3`
   - `PROMPT_VERSION` = `v1`
   - `VISION_MODE` = `cloud` (cpu-basic has no GPU; `auto` would degrade)
   - `DEMO_CACHE` = `1`
   - `DEV_MODE` — leave unset for the public URL
4. **Secrets** (UI-only — Space → Settings → Variables and secrets → New secret):
   - `OPENAI_API_KEY`
5. **Custom domain** — **NOT USED.** HF custom domains require Pro ($9/mo). Per **D-DEPLOY-001** (decisions log), the demo uses the default `https://context31415-ttb-label.hf.space` URL; vanity `ttb.aaroncarney.me` is deferred to pilot phase. Cloudflare CNAME stays dangling — harmless.
6. **Verify** — three smoke calls:
   - `curl -I https://context31415-ttb-label.hf.space/healthz` → 200 with valid HF-issued cert
   - `curl -I https://context31415-ttb-label.hf.space/` → 200 (UI shell)
   - `curl -I https://context31415-ttb-label.hf.space/static/island/single.js` → 200 (asset serving)
```

- [ ] **Step 3: Manual deploy steps** (operator runs the steps above; CI just ships the smoke test)

- [ ] **Step 4: Run smoke against the deployed URL**

```bash
TTB_DEPLOY_URL=https://context31415-ttb-label.hf.space uv run --python 3.12 pytest tests/test_deploy_healthz.py -v
```

- [ ] **Step 5: Commit**

```bash
cd /home/context/projects/takehome-e8backend
git add tests/test_deploy_healthz.py DEMO-RUNBOOK.md
git commit -m "feat(deploy): HF Space setup + UI-stack smoke test (E8 T13)"
```

---

## 4. Self-review

**Spec coverage (vs L1 §2 components delivered):**

| L1 §2.x | This split's task |
|---|---|
| 2.1 Demo fixtures (01–04, 06, 07 single-label) | T1 (gap-fill, no overwrites) |
| 2.2 Demo cache | T8 (envelope snapshotter; LLM-call replay deferred — see §5) |
| 2.3 Cache regeneration | T8 (snapshotter + canonicalize idempotency) |
| 2.6 Deployment (Dockerfile, compose, HF config) | T4, T13 |
| 2.7 Demo runbook | T10, T13 (deploy section) |
| 2.9 README upgrade | T9 |
| 2.10 Test surface (fixture portion + FR-704) | T1, T11 |

**Out of scope for this split:**

| L1 §2.x | Owner |
|---|---|
| 2.4 Eval harness | eval-pipeline split (T2, T3, T5) |
| 2.5 `/eval` route | eval-pipeline split (T7) |
| 2.6 Eval dashboard | eval-pipeline split (T6) |
| 2.10 Eval test surface | eval-pipeline split (T12) |
| 2.1 Demo fixture-05 (batch) | post-merge T15 |
| 2.8 Recorded walkthrough | post-merge T16 (depends on E7 UI being on `main`) |
| AC-§8.4 macro-F1 ≥ 0.70 | post-merge T14 |
| LLM-call cache replay (D-020 fully) | deferred follow-up — ships in pilot if needed |

**E5/E6/E7 surface this split assumes (verified against `main` / `feat/e7-ui` 2026-05-04):**

- `app.deps.build_evaluator(settings: Settings) -> Evaluator` — DI factory.
- `Evaluator.evaluate(application: Application, label: Label) -> DispositionEnvelope` — async, takes domain objects.
- `app.schemas.application.Application(application_id, evaluation_id, expected_values)`.
- `app.schemas.expected.ExpectedValue(field_id, value | None, aliases, abv_labeled_pct, abv_actual_pct, container_volume_ml, parameters, source_cola)`.
- `app.schemas.label.Label(label_id, batch_id, image_bytes, content_type, face_tag, dimensions)`.
- `DispositionEnvelope(evaluation_id, label_ref, disposition, disposition_confidence: ConfidenceBand, fields[], audit_trail: AuditRecord, metrics)`.
- `ConfidenceBand(band: "high"|"medium"|"low", numeric: float)`.
- `app.api.ui.router` registered in `app.main` (E7); `/static/island/` mount under `app.main`.

If any of these drift before merge, the affected test files (`test_borderline_band_fr704.py`, the appended `test_ac_fixture_coverage.py` rows, `scripts/snapshot_demo_envelopes.py`) need touching at green-time.

---

## 5. Out of scope for this L2

- Eval harness, metrics, dashboard, `/eval` route, manifest schema — owned by the eval-pipeline split.
- T14 (live `eval-full` AC), T15 (fixture-05 batch), T16 (recording — depends on E7 UI), T17 (L1 hand-back) — joint close-out.
- **D-020 LLM-call replay (full)** — would require respx-style HTTP-level recording at the OpenAI client seam. T8 ships the envelope-level snapshotter (regression baseline) but stops short of LLM-call replay. The post-merge demo runs OpenAI live; cached envelopes serve as fallback narration if a live call fails.
- Full COLA Registry corpus authoring beyond ~50 entries — pilot-phase per OQ-PRD-5.
- Krippendorff α inter-rater gate — pilot-phase.
- `hadolint` / actual `docker build` in CI — T4 ships content-string lint; full build verification is operator-side.

---

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `Evaluator` / `DispositionEnvelope` surface changes between this split's authoring and merge | Low | Medium | T11 uses xfail markers (matching existing `test_ac_fixture_coverage.py` pattern); T8 imports from `app.schemas.wire.disposition` and would fail at TDD-red if symbol moves — caught immediately |
| Pillow defaults render fixture images differently across platforms — provenance test passes locally but image quality drifts | Low | Low | Fixture builders pin `dpi=(300, 300)` explicitly; `uv.lock` pins Pillow version |
| HF Space cold-start at deploy time exceeds reasonable bound | Medium | Low | T13 manual step verifies via `curl`; if fails, fall back to `cpu-upgrade` tier (paid) per L1 risk register |
| Docker build OOMs on cpu-basic during HF Spaces autobuild | Low | Medium | `.dockerignore` excludes `frontend/` source (~170MB pnpm modules); CPU image base is `python:3.12-slim` |
| `demo/cached/` directory has no envelopes at this split's close (live snapshots are post-merge) | High | None | T8 ships the script + idempotency gate; live snapshots happen in T14 with `OPENAI_API_KEY` |
| E7 doesn't actually merge before this split's T13 → deploy smoke fails on `/` and `/static/island/single.js` | Low | Medium | T13 tests are env-gated by `TTB_DEPLOY_URL`; if E7 hasn't shipped, T13 commits the test but the operator doesn't run the smoke until E7 is on `main`. The plan version log notes the v0.2 E7-on-main assumption |
| Fixture-02 brand_disambig orchestrator path is more sensitive to LLM than other fixtures (apostrophe handling) | Medium | Low | xfail markers preserve the AC contract; if the brand_disambig path mis-handles apostrophes, the test result documents it without breaking CI |
| Fixture-04 image is too aggressively degraded → vision OCR doesn't even fire, short-circuit doesn't catch the right reason code | Low | Low | The 160×160 + radius-3 blur + glare hotspot is calibrated against `app.vision.quality.assess` thresholds; fixture-04 expected.json is `[]` (no expected fields) so any OCR result + short-circuit lands in the AC envelope correctly |

---

## 7. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-04 | Project team | Initial split — extracted T1/T4/T8/T9/T10/T11/T13 from master `.draft` for parallel execution. |
| 0.2 | 2026-05-04 | Project team | Plan-review revision: T1 reframed as gap-fill (don't overwrite existing fixtures); T8 reframed as envelope snapshotter (real surface — `Evaluator.evaluate(application, label) -> DispositionEnvelope`); T11 stops duplicating `test_ac_fixture_coverage.py` and instead extends it + adds dedicated FR-704 borderline-band test; T13 verifies E7 UI shell + island asset serving in addition to `/healthz`; planning assumption documents E7-on-main; consistent `LLM_MODEL_SNAPSHOT=gpt-4o-2024-08-06` across compose + runbook. |

---

## 8. Dependency Graph

### Task Dependencies

| Task | Depends On | Blocks | Files Owned |
|------|-----------|--------|-------------|
| T1 fixture completion | — | T11, T8 (logical: snapshotter targets fixtures) | `fixtures/{01,02,03,04,06,07}-*/{notes.md,expected.json,label.png}`, `scripts/build_fixture_{03,04,06,07}.py`, `tests/test_demo_fixture_provenance.py` |
| T4 Dockerfiles + HF frontmatter | — | T9 (shared `README.md`), T13 | `Dockerfile`, `Dockerfile.gpu`, `docker-compose*.yml`, `.dockerignore`, `README.md` (creates frontmatter), `tests/test_dockerfile_lint.py` |
| T8 envelope snapshotter | — | post-merge T15 (extension) | `scripts/snapshot_demo_envelopes.py`, `demo/cached/.gitkeep`, `tests/test_envelope_snapshot.py` |
| T9 README body | T4 (shared `README.md`) | post-merge T16 (Loom URL replacement) | `README.md` (modify body), `tests/test_readme_content.py` |
| T10 DEMO-RUNBOOK skeleton | — | T13 (shared `DEMO-RUNBOOK.md`) | `DEMO-RUNBOOK.md`, `tests/test_demo_runbook_present.py` |
| T11 fixture ACs + FR-704 | T1 | post-merge T15 (shared test file) | `tests/test_borderline_band_fr704.py`, `tests/test_ac_fixture_coverage.py` (modify, append parametrize cases) |
| T13 HF Space deploy + UI smoke | T4, T10 | — | `tests/test_deploy_healthz.py`, `DEMO-RUNBOOK.md` (modify, append deploy section) |

### Shared Files (force serialization within this split)

| File | Tasks | Order |
|---|---|---|
| `README.md` | T4 (frontmatter), T9 (body) | T4 → T9 |
| `DEMO-RUNBOOK.md` | T10 (skeleton), T13 (deploy section) | T10 → T13 |

### Execution Waves

```
Wave 1 (4 parallel): [T1, T4, T8, T10]            ← roots, no deps
Wave 2 (2 parallel): [T9, T11]                    ← T9 deps T4; T11 deps T1
Wave 3 (1 task):     [T13]                        ← deps T4, T10
```

**Critical path:** T4 → T9 (W1 → W2) and T4 → T13 (W1 → W3) — 3 waves total.
**Concurrency cap:** 4 (well under the 6-task ceiling).

### Wave ownership-disjointness audit

- **Wave 1 (T1, T4, T8, T10).** `fixtures/`, `scripts/build_fixture_*.py`, `tests/test_demo_fixture_provenance.py` (T1) ⨯ `Dockerfile*`, compose, `.dockerignore`, `README.md` (T4 — first writer), `tests/test_dockerfile_lint.py` ⨯ `scripts/snapshot_demo_envelopes.py`, `demo/cached/`, `tests/test_envelope_snapshot.py` (T8) ⨯ `DEMO-RUNBOOK.md`, `tests/test_demo_runbook_present.py` (T10). All disjoint. ✓
- **Wave 2 (T9, T11).** `README.md` (T9 modify — T4 already committed by W1 barrier), `tests/test_readme_content.py` ⨯ `tests/test_borderline_band_fr704.py`, `tests/test_ac_fixture_coverage.py` (T11 modify — append-only) (T11). Disjoint. ✓
- **Wave 3 (T13).** `tests/test_deploy_healthz.py`, `DEMO-RUNBOOK.md` (T13 modify — T10 already committed by W1 barrier). Single task. ✓

### Execution Strategy

> **For Claude:** Use `parallel-plan-executor` to execute this plan. The executor dispatches every task in a wave concurrently (up to 6 at a time) and holds a barrier between waves. After Wave 3 lands, push the branch and notify the user; the post-merge close-out (T14, T15, T16, T17) is owned by the user.

**Wave 1** — Dispatch T1, T4, T8, T10 concurrently in one message. Barrier; verify 4 commits.
**Wave 2** — Dispatch T9, T11 concurrently in one message. Barrier; verify 2 commits.
**Wave 3** — Dispatch T13 alone. Verify commit.

**After Wave 3 lands:** push `feat/e8-backend`. Open PR or hand off to the user for merge coordination with `feat/e8-eval-pipeline` (eval-pipeline split) and `feat/e7-ui` (UI epoch).
