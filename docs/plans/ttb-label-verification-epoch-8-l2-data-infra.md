# Epoch 8 — Data + Infra Split (L2)

> **Parent L1:** [`ttb-label-verification-epoch-8-demo-eval-deploy.md`](./ttb-label-verification-epoch-8-demo-eval-deploy.md)
> **Master L2 (full epoch):** [`ttb-label-verification-epoch-8-l2.md.draft`](./ttb-label-verification-epoch-8-l2.md.draft) — this file extracts the *fixtures + cache + Docker + README + RUNBOOK + per-fixture ACs + deploy smoke* tasks (T1, T4, T8, T9, T10, T11, T13) for parallel execution.
> **Tier:** L2 (file-level + bite-sized TDD steps).
> **For agentic workers:** REQUIRED SUB-SKILL: `parallel-plan-executor`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal.** Land the data + infrastructure half of E8 — six single-label demo fixtures with metadata, the cache regenerator, Dockerfiles + HF Space frontmatter, full README body, DEMO-RUNBOOK skeleton, per-fixture AC tests, and the env-gated deploy smoke. Pure backend; no UI.

**Scope.** `fixtures/`, `scripts/`, `Dockerfile*`, `docker-compose*.yml`, `README.md`, `DEMO-RUNBOOK.md`, `demo/cached/`, and the corresponding test surface. Joint close-out tasks T14 (eval-full AC), T15 (fixture-05 batch), T17 (L1 hand-back), T16 (recording, E7-blocked) are **not** in this split.

**Branch.** `feat/e8-backend` off current `main` (E5/E6 already shipped). The companion eval-pipeline split is on `feat/e8-eval-pipeline`.

**Architecture.** Pure additive layer on top of the E5 single-label Application Service. Fixtures are file trees under `fixtures/<id>/`. Cache lives at `demo/cached/<id>/`. Deployment is a Dockerfile + HF Space README YAML frontmatter. Per **D-DEPLOY-001**: vanity domain (`ttb.aaroncarney.me` via Cloudflare CNAME) is deferred to pilot phase; the demo runs on the default `context31415-ttb-label.hf.space` URL.

**Tech stack.** Python 3.12 / FastAPI / Pydantic v2 (existing) / Pillow (existing) / Docker (HF Spaces SDK).

---

## 1. Coordination with the eval-pipeline split

The eval-pipeline split (`feat/e8-eval-pipeline`) authors `eval/manifest.jsonl` whose lines reference fixture paths owned by this split (e.g. `fixtures/01-spirits-clean/application.json`). **The eval split does not block on this split** — its schema test only validates manifest lines against `ManifestEntry`, not file existence. The actual file-existence test (`test_demo_fixture_provenance.py`) is owned here.

Once both splits merge to `main`, the post-merge close-out runs T14 (live `eval-full` against the live pipeline + these fixtures), T15 (fixture-05 batch — modifies the eval split's `eval/manifest.jsonl` and this split's regenerator script), and T17 (L1 hand-back).

**File-overlap audit (vs. eval-pipeline split):**

| File | This split | Eval-pipeline split | Conflict? |
|---|---|---|---|
| `fixtures/**` | creates | (none — only references paths in `manifest.jsonl`) | no |
| `scripts/**` | creates | (none) | no |
| `Dockerfile*`, `docker-compose*` | creates | (none) | no |
| `README.md` | creates (frontmatter T4 + body T9) | (none) | no |
| `DEMO-RUNBOOK.md` | creates (T10) + modifies (T13) | (none) | no |
| `demo/cached/**` | creates | (none) | no |
| `tests/test_demo_*`, `test_borderline_*`, `test_cache_*`, `test_dockerfile_*`, `test_readme_*`, `test_deploy_*` | creates | (none) | no |
| `eval/**` | (none) | creates | no |
| `app/**` | (none) | modifies (T7: app/main.py) | no |
| `tests/test_eval_*` | (none) | creates | no |

✓ Disjoint.

---

## 2. File structure

### 2.1 New files

```
fixtures/
  01-spirits-clean/{application.json, expected.json, notes.md}              [T1]
  02-bourbon-stones-throw/{application.json, expected.json, notes.md}       [T1]
  03-warning-title-case/{label.png, application.json, expected.json, notes.md}  [T1]
  04-low-res-blurry/{label.png, application.json, expected.json, notes.md}  [T1]
  06-abv-out-of-tolerance/{label.png, application.json, expected.json, notes.md}  [T1]
  07-borderline-confidence/{label.png, application.json, expected.json, notes.md}  [T1]

scripts/
  build_fixture_03.py                                                        [T1]
  build_fixture_04.py                                                        [T1]
  build_fixture_06.py                                                        [T1]
  build_fixture_07.py                                                        [T1]
  regenerate_fixtures.py                                                     [T8]

Dockerfile              # CPU image, python:3.12-slim                       [T4]
Dockerfile.gpu          # CUDA 12.6 base, paddlepaddle-gpu                  [T4]
docker-compose.yml      # `demo` service (CPU)                              [T4]
docker-compose.gpu.yml  # `demo-gpu` service                                 [T4]
.dockerignore                                                                [T4]
README.md               # HF Space frontmatter + reviewer profiles          [T4, T9]
DEMO-RUNBOOK.md         # T-30/T-5/T-1/T-0 operator timeline                [T10, T13]

tests/
  test_demo_fixture_provenance.py     # synthetic-share + class balance     [T1]
  test_dockerfile_lint.py             # docker artifacts + frontmatter      [T4]
  test_cache_idempotency.py           # regenerator idempotency             [T8]
  test_readme_content.py              # reviewer profiles + links           [T9]
  test_demo_runbook_present.py        # runbook structure                   [T10]
  test_demo_fixture_acs.py            # full-pipeline ACs per fixture       [T11]
  test_borderline_slice.py            # FR-704 confidence aggregation       [T11]
  test_deploy_healthz.py              # deployed URL smoke (env-gated)      [T13]
```

### 2.2 Modified files

```
(none — all paths above are new in this split)
```

---

## 3. Tasks


### Wave 1 — Roots (4 parallel)

---
### Task 1 — Single-label fixture authoring (01, 02, 03, 04, 06, 07)

**Files:**
- Create: `fixtures/01-spirits-clean/{application.json, expected.json, notes.md}`
- Create: `fixtures/02-bourbon-stones-throw/{application.json, expected.json, notes.md}`
- Create: `fixtures/03-warning-title-case/{label.png, application.json, expected.json, notes.md}`
- Create: `fixtures/04-low-res-blurry/{label.png, application.json, expected.json, notes.md}`
- Create: `fixtures/06-abv-out-of-tolerance/{label.png, application.json, expected.json, notes.md}`
- Create: `fixtures/07-borderline-confidence/{label.png, application.json, expected.json, notes.md}`
- Create: `scripts/build_fixture_03.py`, `scripts/build_fixture_04.py`, `scripts/build_fixture_06.py`, `scripts/build_fixture_07.py`
- Test: `tests/test_demo_fixture_provenance.py` (full impl in T11; just the existence/shape contract here)

- [ ] **Step 1: Write the failing provenance contract test (skeleton)**

```python
# tests/test_demo_fixture_provenance.py
import json
from pathlib import Path

import pytest

SINGLE_LABEL_FIXTURES = ["01-spirits-clean", "02-bourbon-stones-throw",
                          "03-warning-title-case", "04-low-res-blurry",
                          "06-abv-out-of-tolerance", "07-borderline-confidence"]


@pytest.mark.parametrize("fid", SINGLE_LABEL_FIXTURES)
def test_fixture_has_required_files(fid):
    base = Path("fixtures") / fid
    assert (base / "application.json").is_file(), f"{fid} missing application.json"
    assert (base / "expected.json").is_file(), f"{fid} missing expected.json"
    assert (base / "notes.md").is_file(), f"{fid} missing notes.md"
    label = list(base.glob("label.*"))
    assert label, f"{fid} missing label.{{png,jpg}}"


@pytest.mark.parametrize("fid", SINGLE_LABEL_FIXTURES)
def test_application_json_has_envelope_keys(fid):
    data = json.loads((Path("fixtures") / fid / "application.json").read_text())
    # PRD §6.1 envelope keys
    for key in ("application_id", "applicant", "product", "label_image_ref",
                 "submitted_at", "rule_set_version"):
        assert key in data, f"{fid}: application.json missing {key}"
```

- [ ] **Step 2: Run; expect FAIL (no fixture metadata yet)**

```bash
cd projects/takehome && uv run pytest tests/test_demo_fixture_provenance.py -v
```
Expected: failures for fixtures missing files.

- [ ] **Step 3: Author fixture-01 metadata**

```json
// fixtures/01-spirits-clean/application.json
{
  "application_id": "FIX-01-SPIRITS-CLEAN",
  "applicant": {"name": "ACME Distilling Co.", "ttb_permit": "DSP-CA-15001"},
  "product": {
    "fanciful_name": "ACME Bourbon",
    "brand_name": "ACME",
    "class_type": "BOURBON WHISKY",
    "alcohol_content_pct": 40.0,
    "net_contents": "750 mL"
  },
  "label_image_ref": "label.png",
  "submitted_at": "2026-04-01T12:00:00Z",
  "rule_set_version": "0.1.0"
}
```

```json
// fixtures/01-spirits-clean/expected.json
{
  "disposition": "pass",
  "per_rule": [
    {"rule_id": "FR-200-government-warning", "result": "pass"},
    {"rule_id": "FR-201-warning-allergen", "result": "pass"},
    {"rule_id": "FR-300-class-type", "result": "pass"},
    {"rule_id": "FR-400-abv-tolerance", "result": "pass"},
    {"rule_id": "FR-500-net-contents", "result": "pass"}
  ],
  "borderline_band": false,
  "ac_refs": ["AC-PRD-§8.1-fixture-01"]
}
```

```markdown
<!-- fixtures/01-spirits-clean/notes.md -->
# Fixture 01 — Spirits clean

**PRD §8.1 reference.** Clean spirits label, all rules pass.

**Exercises.** FR-200/201 warnings, FR-300 class/type, FR-400 ABV tolerance, FR-500 net contents.

**Persona signal.** Persona A (high-volume reviewer) — fast happy path; expected ≤ 5 s P99.

**Provenance.** `synthetic-acme-distilling` — derived from `scripts/build_synthetic_fixture.py`.
```

- [ ] **Step 4: Author fixture-02 metadata (STONE'S THROW Bourbon)**

```json
// fixtures/02-bourbon-stones-throw/application.json
{
  "application_id": "FIX-02-STONES-THROW",
  "applicant": {"name": "Stone's Throw Distillery LLC", "ttb_permit": "DSP-KY-14887"},
  "product": {
    "fanciful_name": "STONE'S THROW Bourbon",
    "brand_name": "STONE'S THROW",
    "class_type": "STRAIGHT BOURBON WHISKY",
    "alcohol_content_pct": 45.0,
    "net_contents": "750 mL"
  },
  "label_image_ref": "label.png",
  "submitted_at": "2026-04-01T12:05:00Z",
  "rule_set_version": "0.1.0"
}
```

```json
// fixtures/02-bourbon-stones-throw/expected.json
{
  "disposition": "pass",
  "per_rule": [
    {"rule_id": "FR-300-class-type", "result": "pass",
     "evidence_note": "STONE'S THROW normalizes via apostrophe-aware brand match (PRD-deferred §3.3)"}
  ],
  "borderline_band": false,
  "ac_refs": ["AC-PRD-§8.1-fixture-02", "PRD-deferred-§3.3"]
}
```

```markdown
<!-- fixtures/02-bourbon-stones-throw/notes.md -->
# Fixture 02 — STONE'S THROW Bourbon

**PRD §8.1 reference.** Apostrophe-bearing brand; tests Stage-A normalization (PRD-deferred §3.3).

**Exercises.** FR-300 class/type with apostrophe in brand; brand-match policy.

**Provenance.** `synthetic-stones-throw` — derived from `scripts/build_synthetic_fixture_02.py`.
```

- [ ] **Step 5: Build fixture-03 image + metadata (title-case warning)**

```python
# scripts/build_fixture_03.py
"""Title-case GOVERNMENT WARNING violation per FR-200 case-sensitivity."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/03-warning-title-case/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (400, 400), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME GIN", fill="black", font=font)
    draw.text((10, 30), "ALC. 42% BY VOL.", fill="black", font=font)
    # Title-case violates FR-200 (must be ALL CAPS)
    draw.text((10, 60), "Government Warning: According to the Surgeon", fill="black", font=font)
    draw.text((10, 80), "General, women should not drink alcoholic", fill="black", font=font)
    draw.text((10, 100), "beverages during pregnancy...", fill="black", font=font)
    img.info["dpi"] = (300, 300)
    img.save(OUT, dpi=(300, 300))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
```

Run: `cd projects/takehome && uv run python scripts/build_fixture_03.py`

```json
// fixtures/03-warning-title-case/application.json
{
  "application_id": "FIX-03-WARNING-TITLE-CASE",
  "applicant": {"name": "ACME Distilling Co.", "ttb_permit": "DSP-CA-15001"},
  "product": {
    "fanciful_name": "ACME Gin",
    "brand_name": "ACME",
    "class_type": "GIN",
    "alcohol_content_pct": 42.0,
    "net_contents": "750 mL"
  },
  "label_image_ref": "label.png",
  "submitted_at": "2026-04-01T12:10:00Z",
  "rule_set_version": "0.1.0"
}
```

```json
// fixtures/03-warning-title-case/expected.json
{
  "disposition": "fail",
  "per_rule": [
    {"rule_id": "FR-200-government-warning", "result": "fail",
     "reason_code": "WARN.CASE.TITLECASE"}
  ],
  "borderline_band": false,
  "ac_refs": ["AC-PRD-§8.1-fixture-03", "AC-FR-200"]
}
```

```markdown
<!-- fixtures/03-warning-title-case/notes.md -->
# Fixture 03 — Title-case warning

**PRD §8.1 reference.** FR-200 case-sensitivity violation.

**Exercises.** FR-200 (Government Warning must be ALL CAPS).

**Provenance.** `synthetic-acme-titlecase`.
```

- [ ] **Step 6: Build fixture-04 image + metadata (low-res / glare from fixture-01)**

```python
# scripts/build_fixture_04.py
"""Controlled blur + glare degradation of fixture-01 per PRD §9.1."""
from pathlib import Path
from PIL import Image, ImageFilter

SRC = Path("fixtures/01-spirits-clean/label.png")
OUT = Path("fixtures/04-low-res-blurry/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(SRC)
    # Mild blur — borderline OCR confidence
    blurred = img.filter(ImageFilter.GaussianBlur(radius=2.0))
    # Add a glare hotspot (white circle, low alpha simulated by overlay)
    hotspot = Image.new("RGBA", blurred.size, (255, 255, 255, 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(hotspot)
    d.ellipse((50, 50, 130, 130), fill=(255, 255, 255, 90))
    composite = Image.alpha_composite(blurred.convert("RGBA"), hotspot).convert("RGB")
    composite.save(OUT, dpi=(300, 300))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
```

Run: `cd projects/takehome && uv run python scripts/build_fixture_04.py`

```json
// fixtures/04-low-res-blurry/application.json
{
  "application_id": "FIX-04-LOW-RES-BLURRY",
  "applicant": {"name": "ACME Distilling Co.", "ttb_permit": "DSP-CA-15001"},
  "product": {
    "fanciful_name": "ACME Bourbon",
    "brand_name": "ACME",
    "class_type": "BOURBON WHISKY",
    "alcohol_content_pct": 40.0,
    "net_contents": "750 mL"
  },
  "label_image_ref": "label.png",
  "submitted_at": "2026-04-01T12:15:00Z",
  "rule_set_version": "0.1.0"
}
```

```json
// fixtures/04-low-res-blurry/expected.json
{
  "disposition": "needs_review",
  "per_rule": [
    {"rule_id": "FR-700-image-quality", "result": "needs_review",
     "reason_code": "IMG.QUALITY.BLUR_GLARE"}
  ],
  "borderline_band": false,
  "ac_refs": ["AC-PRD-§8.1-fixture-04", "AC-FR-700"]
}
```

```markdown
<!-- fixtures/04-low-res-blurry/notes.md -->
# Fixture 04 — Low-res / glare

**PRD §8.1 reference.** Image-quality gate fires (FR-700).

**Exercises.** BRISQUE/NIQE quality thresholds; reviewer prompt for re-upload.

**Provenance.** `synthetic-blur-glare-derived-from-01`.
```

- [ ] **Step 7: Build fixture-06 image + metadata (ABV out-of-tolerance)**

```python
# scripts/build_fixture_06.py
"""ABV value on label conflicts with application by > 1% per FR-400."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path("fixtures/06-abv-out-of-tolerance/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (400, 400), color="white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    draw.text((10, 10), "ACME RYE WHISKEY", fill="black", font=font)
    # Label says 47%, application says 40% — > 1% delta triggers FR-400 fail
    draw.text((10, 30), "ALC. 47% BY VOL.", fill="black", font=font)
    draw.text((10, 60), "GOVERNMENT WARNING: According to the Surgeon", fill="black", font=font)
    draw.text((10, 80), "General, women should not drink alcoholic", fill="black", font=font)
    draw.text((10, 100), "beverages during pregnancy...", fill="black", font=font)
    img.save(OUT, dpi=(300, 300))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
```

Run: `cd projects/takehome && uv run python scripts/build_fixture_06.py`

```json
// fixtures/06-abv-out-of-tolerance/application.json
{
  "application_id": "FIX-06-ABV-OUT-OF-TOLERANCE",
  "applicant": {"name": "ACME Distilling Co.", "ttb_permit": "DSP-CA-15001"},
  "product": {
    "fanciful_name": "ACME Rye Whiskey",
    "brand_name": "ACME",
    "class_type": "RYE WHISKEY",
    "alcohol_content_pct": 40.0,
    "net_contents": "750 mL"
  },
  "label_image_ref": "label.png",
  "submitted_at": "2026-04-01T12:20:00Z",
  "rule_set_version": "0.1.0"
}
```

```json
// fixtures/06-abv-out-of-tolerance/expected.json
{
  "disposition": "fail",
  "per_rule": [
    {"rule_id": "FR-400-abv-tolerance", "result": "fail",
     "reason_code": "ABV.DELTA.OVER_1PCT",
     "evidence_note": "label=47.0, application=40.0, delta=7.0"}
  ],
  "borderline_band": false,
  "ac_refs": ["AC-PRD-§8.1-fixture-06", "AC-FR-400", "AC-FR-803-override-target"]
}
```

```markdown
<!-- fixtures/06-abv-out-of-tolerance/notes.md -->
# Fixture 06 — ABV out-of-tolerance

**PRD §8.1 reference.** FR-400 ABV-tolerance fail; demoes the override path (AC-FR-803).

**Exercises.** FR-400 (ABV delta > 1%); AC-FR-803 three-keystroke override (E7-bound).

**Provenance.** `synthetic-acme-abv-mismatch`.
```

- [ ] **Step 8: Build fixture-07 image + metadata (borderline confidence)**

```python
# scripts/build_fixture_07.py
"""Mid-confidence degradation of fixture-01 per PRD §9.1 borderline slice."""
from pathlib import Path
from PIL import Image, ImageFilter

SRC = Path("fixtures/01-spirits-clean/label.png")
OUT = Path("fixtures/07-borderline-confidence/label.png")


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(SRC)
    # Lighter blur than fixture-04: lands fields in the 0.55–0.75 confidence band
    borderline = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    borderline.save(OUT, dpi=(300, 300))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
```

Run: `cd projects/takehome && uv run python scripts/build_fixture_07.py`

```json
// fixtures/07-borderline-confidence/application.json
{
  "application_id": "FIX-07-BORDERLINE-CONFIDENCE",
  "applicant": {"name": "ACME Distilling Co.", "ttb_permit": "DSP-CA-15001"},
  "product": {
    "fanciful_name": "ACME Bourbon",
    "brand_name": "ACME",
    "class_type": "BOURBON WHISKY",
    "alcohol_content_pct": 40.0,
    "net_contents": "750 mL"
  },
  "label_image_ref": "label.png",
  "submitted_at": "2026-04-01T12:25:00Z",
  "rule_set_version": "0.1.0"
}
```

```json
// fixtures/07-borderline-confidence/expected.json
{
  "disposition": "needs_review",
  "per_rule": [
    {"rule_id": "FR-704-confidence-aggregation", "result": "needs_review",
     "reason_code": "CONF.MEDIUM.BAND",
     "evidence_note": "lowest-confidence field surfaced per FR-704"}
  ],
  "borderline_band": true,
  "ac_refs": ["AC-PRD-§8.1-fixture-07", "AC-FR-704"]
}
```

```markdown
<!-- fixtures/07-borderline-confidence/notes.md -->
# Fixture 07 — Borderline confidence

**PRD §8.1 reference.** Mid-confidence band → `needs_review` with the lowest-confidence field surfaced (FR-704).

**Exercises.** FR-704 confidence aggregation; reviewer-attention prompt.

**Provenance.** `synthetic-borderline-derived-from-01`.
```

- [ ] **Step 9: Run provenance test; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_demo_fixture_provenance.py -v
```
Expected: 12 PASS (6 fixtures × 2 parametrized tests).

- [ ] **Step 10: Commit**

```bash
cd projects/takehome
git add fixtures/01-spirits-clean fixtures/02-bourbon-stones-throw \
        fixtures/03-warning-title-case fixtures/04-low-res-blurry \
        fixtures/06-abv-out-of-tolerance fixtures/07-borderline-confidence \
        scripts/build_fixture_03.py scripts/build_fixture_04.py \
        scripts/build_fixture_06.py scripts/build_fixture_07.py \
        tests/test_demo_fixture_provenance.py
git commit -m "feat(fixtures): single-label demo fixtures 01-04, 06-07 (E8 T1)"
```

---
### Task 4 — Dockerfiles + compose + HF Space frontmatter

**Files:**
- Create: `Dockerfile`, `Dockerfile.gpu`, `docker-compose.yml`, `docker-compose.gpu.yml`, `.dockerignore`
- Modify: `README.md` (HF Space YAML frontmatter only — content rewrite is T9)

- [ ] **Step 1: Write a Docker-build smoke test**

```python
# tests/test_dockerfile_lint.py
"""Smoke-lint the Dockerfile without invoking docker — verifies expected directives."""
from pathlib import Path


def test_cpu_dockerfile_uses_python_312_slim():
    content = Path("Dockerfile").read_text()
    assert "FROM python:3.12-slim" in content
    assert "uv sync" in content
    assert "CMD" in content and "uvicorn" in content
    assert "0.0.0.0" in content and "8000" in content


def test_gpu_dockerfile_uses_cuda():
    content = Path("Dockerfile.gpu").read_text()
    assert "nvidia/cuda" in content
    assert "uv sync --extra gpu" in content


def test_compose_files_exist():
    assert Path("docker-compose.yml").is_file()
    assert Path("docker-compose.gpu.yml").is_file()


def test_readme_has_hf_frontmatter():
    content = Path("README.md").read_text()
    assert content.startswith("---\n"), "README must lead with HF Space YAML frontmatter"
    assert "sdk: docker" in content
    assert "app_port: 8000" in content
    assert "hardware: cpu-basic" in content
```

- [ ] **Step 2: Run; expect FAIL**

```bash
cd projects/takehome && uv run pytest tests/test_dockerfile_lint.py -v
```

- [ ] **Step 3: Author `Dockerfile` (CPU)**

```dockerfile
# Dockerfile — CPU image for HF Spaces (cpu-basic tier per D-015)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

# System deps for Pillow + opencv-python-headless
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# uv for fast, reproducible installs
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# App + UI bundle (built island lives at app/ui/static/island/)
COPY app ./app
COPY eval ./eval
COPY fixtures ./fixtures
COPY demo ./demo
COPY rules ./rules
COPY assets ./assets

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
COPY eval ./eval
COPY fixtures ./fixtures
COPY demo ./demo
COPY rules ./rules
COPY assets ./assets

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
      LLM_MODEL_SNAPSHOT: ${LLM_MODEL_SNAPSHOT:-gpt-4o-2024-11-20}
      ORCHESTRATOR_BACKEND: ${ORCHESTRATOR_BACKEND:-openai}
      LOOKAHEAD_K: ${LOOKAHEAD_K:-3}
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
      LLM_MODEL_SNAPSHOT: ${LLM_MODEL_SNAPSHOT:-gpt-4o-2024-11-20}
      ORCHESTRATOR_BACKEND: ${ORCHESTRATOR_BACKEND:-openai}
      LOOKAHEAD_K: ${LOOKAHEAD_K:-3}
      DEMO_CACHE: ${DEMO_CACHE:-1}
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

- [ ] **Step 6: Author `.dockerignore`**

```
.git/
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
node_modules/
frontend/node_modules/
docs/
tests/
*.md
!README.md
```

- [ ] **Step 7: Add HF Space frontmatter to `README.md`** (full content rewrite is T9)

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

(Content to be filled in by T9.)
```

- [ ] **Step 8: Run lint; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_dockerfile_lint.py -v
```

- [ ] **Step 9: Commit**

```bash
cd projects/takehome
git add Dockerfile Dockerfile.gpu docker-compose.yml docker-compose.gpu.yml \
        .dockerignore README.md tests/test_dockerfile_lint.py
git commit -m "feat(deploy): Dockerfile + compose + HF Space frontmatter (E8 T4)"
```


---
### Task 8 — Cache regenerator + idempotency

**Files:**
- Create: `scripts/regenerate_fixtures.py`
- Test: `tests/test_cache_idempotency.py`

> **E5 dependency.** The live OpenAI/extractor calls are gated behind a `--live` flag; the default mode reads existing `cached_responses.json` (if present) and re-emits canonicalized JSON, which is what the idempotency test exercises. Once E5 lands, the executor extends `--live` to actually call.

- [ ] **Step 1: Write the idempotency test**

```python
# tests/test_cache_idempotency.py
import json
import shutil
import subprocess
from pathlib import Path


def test_regenerate_idempotent_on_unchanged_inputs(tmp_path):
    """Running regenerator twice on unchanged fixtures yields byte-identical cache."""
    # Seed a minimal cached response for fixture-01 to exercise the read path.
    target = Path("demo/cached/01-spirits-clean")
    target.mkdir(parents=True, exist_ok=True)
    (target / "cached_responses.json").write_text(json.dumps({
        "cache_key": "seed",
        "tasks": {"brand_disambig": {"response": "ACME"}}
    }, indent=2, sort_keys=True))

    # First regeneration (no --live → reads + canonicalizes)
    subprocess.run(["python", "scripts/regenerate_fixtures.py",
                    "--fixtures", "01-spirits-clean"], check=True)
    first = (target / "cached_responses.json").read_bytes()

    # Second regeneration on unchanged inputs
    subprocess.run(["python", "scripts/regenerate_fixtures.py",
                    "--fixtures", "01-spirits-clean"], check=True)
    second = (target / "cached_responses.json").read_bytes()

    assert first == second, "Regenerator must produce byte-identical output on unchanged inputs"
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Implement `scripts/regenerate_fixtures.py`**

```python
# scripts/regenerate_fixtures.py
"""Idempotent cache regenerator for demo/cached/<fixture-id>/ (E8 T8).

Without --live: reads existing cached_responses.json and re-emits canonical JSON
  (sort_keys=True, indent=2). Used by CI to assert idempotency.
With --live: invokes the live CloudVisionExtractor + OpenAIStrictOrchestrator
  (E5), records each task's response, and writes the canonicalized cache.

Triggers (per L1 §2.3): LLM_MODEL_SNAPSHOT change, PROMPT_VERSION bump,
rule_pack_version bump, or fixture image/application.json hash diff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SINGLE_LABEL_FIXTURES = (
    "01-spirits-clean", "02-bourbon-stones-throw", "03-warning-title-case",
    "04-low-res-blurry", "06-abv-out-of-tolerance", "07-borderline-confidence",
)


def _hash_inputs(fixture_id: str) -> str:
    base = Path("fixtures") / fixture_id
    h = hashlib.sha256()
    for name in ("application.json", "label.png", "label.jpg"):
        f = base / name
        if f.is_file():
            h.update(f.read_bytes())
    return h.hexdigest()


def _canonicalize(payload: dict) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def regenerate(fixture_id: str, live: bool = False) -> None:
    target_dir = Path("demo/cached") / fixture_id
    target_dir.mkdir(parents=True, exist_ok=True)
    cache_file = target_dir / "cached_responses.json"

    if live:
        # E5 dependency: live extractor + orchestrator calls.
        from app.services.application import Evaluator  # noqa: I001  E5
        evaluator = Evaluator()
        # Capture the per-task call records via the existing ring-buffer / call-recorder
        # surface (E1 schemas/calls.py). The exact integration is finalized when
        # E5 lands; structure here matches the cached_responses.json shape.
        envelope = evaluator.evaluate(
            application_ref=str(Path("fixtures") / fixture_id / "application.json"),
            image_ref=str(Path("fixtures") / fixture_id / "label.png"),
        )
        payload = {
            "cache_key": _hash_inputs(fixture_id),
            "tasks": {c.task: {"response": c.response} for c in envelope.audit_trail.calls},
        }
    else:
        if not cache_file.is_file():
            print(f"[skip] {fixture_id}: no cache present and --live not set")
            return
        payload = json.loads(cache_file.read_text())
        payload["cache_key"] = _hash_inputs(fixture_id)

    cache_file.write_text(_canonicalize(payload))
    print(f"[ok] {fixture_id}: cache written ({cache_file})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", nargs="+", default=list(SINGLE_LABEL_FIXTURES))
    parser.add_argument("--live", action="store_true",
                        help="Make live OpenAI calls (requires E5 + OPENAI_API_KEY)")
    args = parser.parse_args()
    for fid in args.fixtures:
        regenerate(fid, live=args.live)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_cache_idempotency.py -v
```

- [ ] **Step 5: Commit**

```bash
cd projects/takehome
git add scripts/regenerate_fixtures.py tests/test_cache_idempotency.py
git commit -m "feat(scripts): regenerate_fixtures.py with idempotency gate (E8 T8)"
```

---

---
### Task 10 — DEMO-RUNBOOK skeleton

**Files:**
- Create: `DEMO-RUNBOOK.md`
- Test: `tests/test_demo_runbook_present.py`

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
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Author `DEMO-RUNBOOK.md`**

```markdown
# Demo Runbook

Operator timeline for the 5-minute recorded walkthrough (PRD §10.2).

> **Status of TODOs.** `[E6]` markers wait on the batch + override server.
> `[E7]` markers wait on the React island UI. The runbook's structure is
> finalized; the narration in those sections is filled in once those
> epochs land.

---

## T-30 minutes — environment check

```bash
# 1. Deployment reachable with valid TLS
curl -I https://context31415-ttb-label.hf.space/healthz
# Expect: HTTP/2 200 and a valid HF-issued cert (no `--insecure` flag needed)

# 2. API credentials valid
curl https://context31415-ttb-label.hf.space/healthz | jq '.mode.orchestrator'
# Expect: "openai"

# 3. Repo clean
gh release list && git status
# Expect: working tree clean, latest release tagged

# 4. Cache idempotency
uv run python scripts/regenerate_fixtures.py
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

Open https://context31415-ttb-label.hf.space in a fresh browser tab. Drop fixture-01 onto
the upload area. Confirm a `pass` disposition appears within 5 s.

## T-0 — begin recording

Six-stage path per PRD §10.2:

1. **Stage 1 — Upload fixture-01** (clean spirits). Disposition: `pass`. Show
   the citation chips backing each rule.
2. **Stage 2 — Upload fixture-02** (STONE'S THROW Bourbon). Disposition: `pass`.
   Narrate the apostrophe-aware brand normalization (PRD-deferred §3.3).
3. **Stage 3 — Upload fixture-03** (title-case warning). Disposition: `fail`
   on FR-200. Show the `WARN.CASE.TITLECASE` reason code.
4. **Stage 4 — Upload fixture-04** (low-res / glare). Disposition:
   `needs_review`. Show the image-quality gate prompting re-upload.
5. **Stage 5 — Upload fixture-05** (50-label batch). `[E6]` Show the SSE
   stream, queue position, and lookahead progress. `[E6]` Trigger the M-of-N
   anomaly advisory by submitting same-reason fails.
6. **Stage 6 — Override on fixture-06** (ABV out-of-tolerance). `[E7]`
   Three-keystroke override demo (AC-FR-803). `[E7]` Show the audit-trail
   entry with reason code + reviewer ID + timestamp.

Bonus (deployed but cut from recording for time): fixture-07 borderline-band
`needs_review` with the lowest-confidence field surfaced.

## Failure recovery

| Scenario | Recovery |
|---|---|
| Network drops mid-batch | `[E6]` SSE auto-reconnect from `current_index`; reviewer continues |
| LLM timeout | Cached responses serve from `demo/cached/` (DEMO_CACHE=1); cache miss falls through to live with a warning toast |
| OCR low-confidence on a demo image | Switch to fixture-01 as fallback; document image quality is a separate FR-700 demo |
| HF Space cold-start exceeds 5 s | T-5 pre-warm absorbs this; if it recurs mid-demo, point at the `/healthz` curl in T-30 as evidence the deploy is healthy |
| Cache stale relative to active LLM_MODEL_SNAPSHOT | `uv run python scripts/regenerate_fixtures.py --live` (requires OPENAI_API_KEY); commit the diff |

## Re-record protocol

If the recording goes long or the cursor lands on the wrong control, re-shoot
following the same six-stage path. The narration script lives at
`docs/demo-narration.md` (TODO — author with T16).
```

- [ ] **Step 4: Run; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_demo_runbook_present.py -v
```

- [ ] **Step 5: Commit**

```bash
cd projects/takehome
git add DEMO-RUNBOOK.md tests/test_demo_runbook_present.py
git commit -m "docs(runbook): T-30/T-5/T-1/T-0 skeleton + failure recovery (E8 T10)"
```

---

---

### Wave 2 — Body docs + fixture ACs (2 parallel; depend on T4 + T1)

---
### Task 9 — README upgrade

**Files:**
- Modify: `README.md` (preserve T4's HF Space frontmatter; replace placeholder body)

- [ ] **Step 1: Write the README content test**

```python
# tests/test_readme_content.py
from pathlib import Path


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
    # Placeholder until T16 records and replaces with the real URL.
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

### Profile A — WSL2 + GPU (full local-mode path)
```bash
git clone https://github.com/aaroncarney/ttb-label-verification && cd ttb-label-verification
uv sync --extra gpu
uv run task demo
# Open http://localhost:8000
```

### Profile B — macOS, no GPU (cloud-mode only)
```bash
git clone https://github.com/aaroncarney/ttb-label-verification && cd ttb-label-verification
uv sync
export OPENAI_API_KEY=sk-...
uv run task demo
```

### Profile C — Linux, no GPU (cloud-mode only)
Same as Profile B.

## Headline trade-off

This prototype optimizes for **citation-grounded transparency** over **end-to-end
automation**. The deterministic rule core (`rules/`) makes pass/fail decisions;
the AI surface (Vision + Orchestrator) extracts evidence and proposes
explanations but never decides — see D-002 / FR-303.

The economic case (`docs/research/T11-output.md`) and policy case
(`docs/research/T7-output.md`) settle the trade-off range.

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
uv run task eval-dashboard  # render eval/history/ → /eval
```

The `/eval` route is `DEV_MODE`-gated.

## License

Prototype; not for production use.
```

- [ ] **Step 4: Run; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_readme_content.py -v
```

- [ ] **Step 5: Commit**

```bash
cd projects/takehome
git add README.md tests/test_readme_content.py
git commit -m "docs(readme): reviewer profiles + headline tradeoff + Loom placeholder (E8 T9)"
```

---

---
### Task 11 — Demo-fixture AC tests

**Files:**
- Create: `tests/test_demo_fixture_acs.py`, `tests/test_borderline_slice.py`

- [ ] **Step 1: Write the AC test (single-label fixtures)**

```python
# tests/test_demo_fixture_acs.py
"""Per-fixture AC checks. Goes green when E5 + cached responses both land."""
import json
from pathlib import Path

import pytest

SINGLE_LABEL_FIXTURES = ["01-spirits-clean", "02-bourbon-stones-throw",
                          "03-warning-title-case", "04-low-res-blurry",
                          "06-abv-out-of-tolerance", "07-borderline-confidence"]


@pytest.mark.parametrize("fid", SINGLE_LABEL_FIXTURES)
def test_fixture_pipeline_matches_expected(fid):
    """Run the fixture through the full pipeline (cached LLM); assert disposition + per-rule."""
    pytest.importorskip("app.services.application", reason="E5 not yet shipped")
    from app.services.application import Evaluator

    expected = json.loads((Path("fixtures") / fid / "expected.json").read_text())
    evaluator = Evaluator(demo_cache=True)  # E5 honors the DEMO_CACHE flag

    envelope = evaluator.evaluate(
        application_ref=str(Path("fixtures") / fid / "application.json"),
        image_ref=str(Path("fixtures") / fid / "label.png"),
    )
    assert envelope.disposition == expected["disposition"]
    expected_rule_ids = {r["rule_id"] for r in expected["per_rule"]}
    actual_rule_ids = {r.rule_id for r in envelope.per_rule}
    # All expected rules must appear in the verdict (others may also fire).
    assert expected_rule_ids.issubset(actual_rule_ids)
    for er in expected["per_rule"]:
        actual = next(r for r in envelope.per_rule if r.rule_id == er["rule_id"])
        assert actual.result == er["result"], f"{fid}/{er['rule_id']}: result mismatch"
```

```python
# tests/test_borderline_slice.py
"""FR-704: borderline-confidence fixture lands in medium band, lowest-confidence field surfaced."""
import json
from pathlib import Path

import pytest


def test_fixture_07_borderline_band():
    pytest.importorskip("app.services.application", reason="E5 not yet shipped")
    from app.services.application import Evaluator

    fid = "07-borderline-confidence"
    evaluator = Evaluator(demo_cache=True)
    envelope = evaluator.evaluate(
        application_ref=str(Path("fixtures") / fid / "application.json"),
        image_ref=str(Path("fixtures") / fid / "label.png"),
    )
    assert envelope.disposition == "needs_review"
    # Confidence in medium band per FR-704
    assert 0.55 <= envelope.aggregate_confidence <= 0.75
    # Lowest-confidence field surfaced in evidence
    assert envelope.lowest_confidence_field is not None
```

- [ ] **Step 2: Run; expect skip (E5 not shipped) — captures intent without failing CI**

```bash
cd projects/takehome && uv run pytest tests/test_demo_fixture_acs.py tests/test_borderline_slice.py -v
```
Expected: `pytest.importorskip` reports SKIP for each test until E5 lands; runs and asserts when it does.

- [ ] **Step 3: Commit**

```bash
cd projects/takehome
git add tests/test_demo_fixture_acs.py tests/test_borderline_slice.py
git commit -m "test(fixtures): per-fixture AC checks + FR-704 borderline (E8 T11; skips until E5)"
```

---

---

### Wave 3 — Deploy smoke (1 task; depends on T4 + T10)

---
### Task 13 — HF Space deploy + smoke

**Files:**
- Modify: `DEMO-RUNBOOK.md` (record HF Space provisioning state)
- Create: `tests/test_deploy_healthz.py`

> **What this task does and doesn't:** the deployment itself is a **manual,
> one-time setup** (HF Space create, secrets entry, `git push hf main`). Per
> **D-DEPLOY-001** there is **no Cloudflare CNAME and no custom domain** in
> the demo path — HF custom domains require Pro ($9/mo) and the default
> `*.hf.space` URL is sufficient for take-home review. The automated portion
> is the smoke test that an env-gated CI job runs against the live URL. Mark
> this task done when (a) the manual steps are followed per the runbook
> section and (b) the smoke test passes locally with
> `TTB_DEPLOY_URL=https://context31415-ttb-label.hf.space`.

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
    assert body["status"] == "ok"
    assert "version" in body and "mode" in body


def test_deployed_tls_chain_valid(deploy_url):
    """HF-issued cert; no insecure flag."""
    r = httpx.get(f"{deploy_url}/healthz", verify=True, timeout=10.0)
    assert r.status_code == 200
```

- [ ] **Step 2: Add HF Space setup section to `DEMO-RUNBOOK.md`** (no Cloudflare; per D-DEPLOY-001)

Append to `DEMO-RUNBOOK.md`:

```markdown
## Initial deployment setup (one-time, executed 2026-05-04)

1. **HF Space create** — `hf repos create Context31415/ttb-label --type space --space-sdk docker --public`
2. **Push** (deferred until E8 ships real code) — `git remote add hf https://huggingface.co/spaces/Context31415/ttb-label && git push hf main`
3. **Variables** (set via API at provisioning time; verify in HF Space → Settings → Variables and secrets):
   - `ORCHESTRATOR_BACKEND` = `openai`
   - `LLM_MODEL_SNAPSHOT` = `gpt-4o-2024-08-06`
   - `LOOKAHEAD_K` = `3`
   - `PROMPT_VERSION` = `v1`
   - `VISION_MODE` = `cloud` (cpu-basic has no GPU; `auto` would degrade)
   - `DEV_MODE` — leave unset for the public URL
4. **Secrets** (UI-only — Space → Settings → Variables and secrets → New secret):
   - `OPENAI_API_KEY`
5. **Custom domain** — **NOT USED.** HF custom domains require Pro ($9/mo).
   Per **D-DEPLOY-001** (decisions log), the demo uses the default
   `https://context31415-ttb-label.hf.space` URL; vanity `ttb.aaroncarney.me`
   is deferred to pilot phase. Cloudflare CNAME stays dangling — harmless.
6. **Verify** — `curl -I https://context31415-ttb-label.hf.space/healthz`
   returns 200 with a valid HF-issued (Let's Encrypt at HF edge) cert.
```

- [ ] **Step 3: Manual deploy steps** (operator runs the steps above)

- [ ] **Step 4: Run smoke against the deployed URL**

```bash
TTB_DEPLOY_URL=https://context31415-ttb-label.hf.space uv run pytest tests/test_deploy_healthz.py -v
```

- [ ] **Step 5: Commit**

```bash
cd projects/takehome
git add tests/test_deploy_healthz.py DEMO-RUNBOOK.md
git commit -m "feat(deploy): HF Space setup steps + env-gated smoke test (E8 T13)"
```

---

---

## 4. Self-review

**Spec coverage (vs L1 §2 components delivered):**

| L1 §2.x | This split's task |
|---|---|
| 2.1 Demo fixtures (01–04, 06, 07 single-label) | T1 |
| 2.2 Demo cache (`demo/cached/<id>/cached_responses.json`) | T8 (script — populated live by T8 cache regenerator) |
| 2.3 Cache regeneration (`scripts/regenerate_fixtures.py`) | T8 |
| 2.6 Deployment (Dockerfile, compose, HF config) | T4, T13 |
| 2.7 Demo runbook | T10, T13 (deploy section) |
| 2.9 README upgrade | T9 |
| 2.10 Test surface (fixture portion) | T11 (single-label fixture ACs + borderline) |

**Out of scope for this split (handled by eval-pipeline split or post-merge):**

| L1 §2.x | Owner |
|---|---|
| 2.4 Eval harness | eval-pipeline split (T2, T3, T5) |
| 2.5 `/eval` route | eval-pipeline split (T7) |
| 2.6 Eval dashboard | eval-pipeline split (T6) |
| 2.10 Eval test surface | eval-pipeline split (T12) |
| 2.1 Demo fixture-05 (batch) | post-merge T15 (E6 was blocking; now unblocked but coordinates with eval split's manifest) |
| 2.8 Recorded walkthrough | E7-blocked T16 |
| AC-§8.4 macro-F1 ≥ 0.70 | post-merge T14 |

**E5 surface this split assumes (already on `main`):**
`Evaluator(demo_cache: bool = False).evaluate(application_ref: str, image_ref: str) -> DispositionEnvelope` with `disposition`, `per_rule[]`, `aggregate_confidence`, `lowest_confidence_field`. T11 uses `pytest.importorskip` so it skips cleanly if the import target moves.

---

## 5. Out of scope for this L2

- Eval harness, metrics, dashboard, `/eval` route, manifest schema — owned by the eval-pipeline split.
- T14 (live `eval-full` AC), T15 (fixture-05 batch), T16 (recording, E7-blocked), T17 (L1 hand-back) — joint close-out / E7-blocked.
- Full COLA Registry corpus authoring beyond ~50 entries — pilot-phase per OQ-PRD-5.
- Krippendorff α inter-rater gate — pilot-phase.

---

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `Evaluator` signature in E5 differs from the one assumed in T11 | Low | Low | T11 uses `pytest.importorskip`; signature mismatch caught at green-time on `main` post-merge |
| Pillow defaults render fixture images differently across platforms — provenance test passes locally but image quality drifts | Low | Low | Fixture builders pin `dpi=(300, 300)` explicitly; the fixtures-{03,04,06,07} build scripts are deterministic given same Pillow version (pinned via `uv.lock`) |
| HF Space cold-start at deploy time exceeds reasonable bound | Medium | Low | T13 manual step verifies via `curl`; if fails, fall back to `cpu-upgrade` tier (paid) per L1 risk register |
| Docker build OOMs on cpu-basic during HF Spaces autobuild | Low | Medium | `.dockerignore` excludes test artifacts and docs; the CPU image base (`python:3.12-slim`) is small enough; HF Spaces builds in their infra not cpu-basic at runtime |
| `demo/cached/` directory has no contents at this split's close (live regeneration is T14) | High | None | T8 ships the script with idempotency on read-path; `--live` cache fill happens in T14 post-merge with OPENAI_API_KEY present. Documented in T8 |

---

## 7. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-04 | Project team | Initial split — extracted T1/T4/T8/T9/T10/T11/T13 from master `.draft` for parallel execution. |

---

## 8. Dependency Graph

### Task Dependencies

| Task | Depends On | Blocks | Files Owned |
|------|-----------|--------|-------------|
| T1 single-label fixtures | — | T11, T8 (logical) | `fixtures/{01,02,03,04,06,07}-*/`, `scripts/build_fixture_{03,04,06,07}.py`, `tests/test_demo_fixture_provenance.py` |
| T4 Dockerfiles + HF frontmatter | — | T9 (shared `README.md`), T13 | `Dockerfile`, `Dockerfile.gpu`, `docker-compose.yml`, `docker-compose.gpu.yml`, `.dockerignore`, `README.md` (creates frontmatter), `tests/test_dockerfile_lint.py` |
| T8 cache regenerator | — | (post-merge T15 shared script) | `scripts/regenerate_fixtures.py`, `tests/test_cache_idempotency.py` |
| T9 README upgrade | T4 (shared `README.md`) | (post-merge T16 shared `README.md`) | `README.md` (modify body), `tests/test_readme_content.py` |
| T10 DEMO-RUNBOOK skeleton | — | T13 (shared `DEMO-RUNBOOK.md`) | `DEMO-RUNBOOK.md`, `tests/test_demo_runbook_present.py` |
| T11 demo-fixture AC tests | T1 | (post-merge T15 shared test file) | `tests/test_demo_fixture_acs.py`, `tests/test_borderline_slice.py` |
| T13 HF Space deploy + smoke | T4, T10 | — | `tests/test_deploy_healthz.py`, `DEMO-RUNBOOK.md` (modify, append deploy section) |

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

**Critical path:** T4 → T13 (or T1 → T11) — 2 waves. With T9 chained off T4, the longest path is T4 → T9 → (close) which sits at 2 waves; T13 in W3 makes it 3 waves total.
**Concurrency cap:** 4 (well under the 6-task ceiling).

### Wave ownership-disjointness audit

- **Wave 1 (T1, T4, T8, T10).** `fixtures/`, `scripts/build_fixture_*.py` (T1) ⨯ `Dockerfile*`, compose, `.dockerignore`, `README.md` (T4 — first writer) ⨯ `scripts/regenerate_fixtures.py` (T8) ⨯ `DEMO-RUNBOOK.md` (T10). All disjoint. ✓
- **Wave 2 (T9, T11).** `README.md` (T9 modify — T4 already committed by W1 barrier) ⨯ `tests/test_demo_fixture_acs.py`, `tests/test_borderline_slice.py` (T11). Disjoint. ✓
- **Wave 3 (T13).** `tests/test_deploy_healthz.py`, `DEMO-RUNBOOK.md` (T13 modify — T10 already committed by W1 barrier). Single task, no overlap. ✓

### Execution Strategy

> **For Claude:** Use `parallel-plan-executor` to execute this plan. The executor dispatches every task in a wave concurrently (up to 6 at a time) and holds a barrier between waves. After Wave 3 lands, push the branch and notify the user; the post-merge close-out (T14, T15, T17) is owned by the user.

**Wave 1** — Dispatch T1, T4, T8, T10 concurrently in one message. Barrier; verify 4 commits.
**Wave 2** — Dispatch T9, T11 concurrently in one message. Barrier; verify 2 commits.
**Wave 3** — Dispatch T13 alone. Verify commit.

**After Wave 3 lands:** push `feat/e8-backend`. Open PR or hand off to the user for merge coordination with `feat/e8-eval-pipeline` (eval-pipeline split).
