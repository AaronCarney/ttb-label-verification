# Epoch 8 — Eval Pipeline Split (L2)

> **Parent L1:** [`ttb-label-verification-epoch-8-demo-eval-deploy.md`](./ttb-label-verification-epoch-8-demo-eval-deploy.md)
> **Master L2 (full epoch):** [`ttb-label-verification-epoch-8-l2.md.draft`](./ttb-label-verification-epoch-8-l2.md.draft) — this file extracts the *eval pipeline* tasks (T2, T3, T5, T6, T7, T12) for parallel execution by a separate session.
> **Tier:** L2 (file-level + bite-sized TDD steps).
> **For agentic workers:** REQUIRED SUB-SKILL: `parallel-plan-executor`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal.** Land the eval pipeline half of E8 — manifest + datasheet + line schema, metrics module, harness CLI, dashboard renderer + Jinja template, `/eval` route, and harness/dashboard test surface. Pure backend; no UI. Goes green against the live E5 Application Service (already on `main`).

**Scope.** Eval/ package + `/eval` route + tests. Joint close-out tasks T14 (eval-full AC), T15 (fixture-05 batch), T17 (L1 hand-back) are **not** in this split — they run after both this split and the data+infra split land on `main`.

**Branch.** `feat/e8-eval-pipeline` off current `main` (E5/E6 already shipped). The companion data+infra split is on `feat/e8-backend` — the two branches modify disjoint files (verified below).

**Architecture.** Pure additive layer on top of the E5 single-label Application Service. `eval/` is a sibling Python package with its own manifest/datasheet/harness/metrics/dashboard. `/eval` is a single DEV_MODE-gated FastAPI route. No orchestrator change.

**Dependency-direction invariant.** `eval/` may import from `app.services.*` (one-way: harness needs the live Evaluator). `app/` may NOT import from `eval/` **except through the single adapter `app/api/eval.py`**, which exists solely to bind `eval.dashboard.render_dashboard` to a FastAPI route. Any other `app → eval` import is a layering violation.

**Tech stack.** Python 3.12 / FastAPI / Pydantic v2 / Jinja2 / pytest + pytest-asyncio (existing).

---

## 1. Coordination with the data+infra split

The data+infra split (`feat/e8-backend`) authors `fixtures/01..04, 06, 07/` directories — fixture metadata that this split's `eval/manifest.jsonl` will reference by path. **This split does not block on those fixtures** — `manifest.jsonl` lines reference fixture paths by string; the schema test (T2) validates lines against `ManifestEntry`, not file existence. The full eval test (T12) is `@pytest.mark.slow` and skips by default.

Once both splits merge to `main`, the post-merge close-out runs T14 (live `eval-full` against the live pipeline + Split-B fixtures), T15 (fixture-05 batch — modifies this split's `eval/manifest.jsonl` and the data+infra split's regenerator script), and T17 (L1 hand-back).

**File-overlap audit (vs. data+infra split):**

| File | This split | Data+infra split | Conflict? |
|---|---|---|---|
| `eval/**` | creates | (none) | no |
| `app/api/eval.py` | creates | (none) | no |
| `app/main.py` | modifies (1 line: register router) | (none in this split — E7 owns its own additions) | no |
| `tests/test_eval_*` | creates | (none) | no |
| `fixtures/**` | (none — only references paths in `manifest.jsonl`) | creates | no |
| `Dockerfile*`, `docker-compose*` | (none) | creates | no |
| `README.md`, `DEMO-RUNBOOK.md` | (none) | creates | no |

✓ Disjoint.

---

## 2. File structure

### 2.1 New files

```
eval/
  __init__.py                                                                [T2]
  _schema.py            # Pydantic for manifest line + history record       [T2]
  manifest.jsonl                                                             [T2]
  datasheet.md          # Gebru et al. 2021 §1–7                            [T2]
  metrics.py            # macro-F1, per-rule P/R, ECE, latency              [T3]
  harness.py            # __main__ entry, --subset {smoke,full}             [T5]
  dashboard.py          # Jinja2 renderer for /eval                          [T6]
  templates/
    dashboard.html      # confusion matrix + per-rule table + chart island  [T6]
  history/
    .gitkeep                                                                 [T5]

app/api/
  eval.py               # DEV_MODE-gated GET /eval                           [T7]

tests/
  test_eval_manifest_schema.py                                               [T2]
  test_eval_metrics.py                                                       [T3]
  test_eval_harness_cli.py                                                   [T5]
  test_eval_dashboard_render.py                                              [T6]
  test_eval_dashboard_route.py                                               [T7]
  test_eval_harness.py                # smoke subset                         [T12]
  test_eval_full.py                   # full subset, @pytest.mark.slow      [T12]
```

### 2.2 Modified files

```
app/main.py             # register /eval router (DEV_MODE-conditional)      [T7]
```

---

## 3. Tasks


### Wave 1 — Manifest root (1 task)

---
### Task 2 — Eval manifest + datasheet + line schema

**Files:**
- Create: `eval/__init__.py`, `eval/_schema.py`, `eval/manifest.jsonl`, `eval/datasheet.md`
- Test: `tests/test_eval_manifest_schema.py`

- [ ] **Step 1: Write the failing schema test**

```python
# tests/test_eval_manifest_schema.py
import json
from pathlib import Path

from eval._schema import ManifestEntry


def test_every_manifest_line_validates():
    path = Path("eval/manifest.jsonl")
    assert path.is_file()
    for i, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        ManifestEntry.model_validate_json(line)  # raises ValidationError on malformed lines


def test_class_balance_meets_prd_91():
    """spirits 30–40%, wine 30–40%, malt 20–30%; synthetic ≤30%; borderline ≥4 (smoke 20-entry split; full ~50 corpus must hit PRD ≥10)."""
    path = Path("eval/manifest.jsonl")
    entries = [ManifestEntry.model_validate_json(l) for l in path.read_text().splitlines() if l.strip()]
    n = len(entries)
    spirits = sum(1 for e in entries if e.class_balance_tag == "spirits")
    wine = sum(1 for e in entries if e.class_balance_tag == "wine")
    malt = sum(1 for e in entries if e.class_balance_tag == "malt")
    synth = sum(1 for e in entries if e.provenance.source.startswith("synthetic-"))
    borderline = sum(1 for e in entries if e.borderline_band)
    assert 0.30 <= spirits / n <= 0.40, f"spirits ratio {spirits/n}"
    assert 0.30 <= wine / n <= 0.40, f"wine ratio {wine/n}"
    assert 0.20 <= malt / n <= 0.30, f"malt ratio {malt/n}"
    assert synth / n <= 0.30, f"synthetic ratio {synth/n}"
    assert borderline >= 4, f"borderline count {borderline}"  # smoke 20-entry scaling; full ~50 corpus retains PRD ≥10
```

- [ ] **Step 2: Run; expect FAIL (no module / no manifest)**

```bash
cd projects/takehome && uv run pytest tests/test_eval_manifest_schema.py -v
```
Expected: ImportError or FileNotFoundError.

- [ ] **Step 3: Implement the line schema**

```python
# eval/__init__.py
"""Eval harness package — manifest, metrics, harness, dashboard."""
```

```python
# eval/_schema.py
"""Manifest line schema + history record schema (E8 T2)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: str = Field(..., description="`^synthetic-<slug>` or COLA Registry id")


class ExpectedRule(BaseModel):
    rule_id: str
    result: Literal["pass", "fail", "needs_review"]
    reason_code: str | None = None


class ManifestEntry(BaseModel):
    label_id: str
    application_ref: str  # path or URL
    image_ref: str
    expected_disposition: Literal["pass", "fail", "needs_review"]
    expected_per_rule: list[ExpectedRule]
    provenance: Provenance
    class_balance_tag: Literal["spirits", "wine", "malt"]
    borderline_band: bool = False


class HistoryRecord(BaseModel):
    """Single entry in eval/history/<ISO-8601>.json (one per harness run)."""
    timestamp: str
    subset: Literal["smoke", "full"]
    n_labels: int
    macro_f1: float
    per_rule_precision: dict[str, float]
    per_rule_recall: dict[str, float]
    ece: float
    latency_p50_s: float
    latency_p95_s: float
    latency_p99_s: float
    cost_weighted_score: float  # cost-weighted accuracy (T9 Q9.1); FP penalty 3×, FR 1×
```

- [ ] **Step 4: Author `eval/manifest.jsonl` with the right-sized corpus per PRD v0.6 §9.1**

The full corpus is ~50 entries: 18 spirits (36%), 17 wine (34%), 13 malt (26%), with ≥10 borderline-band, synthetic ≤30%. Encode with one line per label. The smoke subset is the first 20 entries — the harness honors `--subset` by index.

```jsonl
{"label_id": "FIX-01-SPIRITS-CLEAN", "application_ref": "fixtures/01-spirits-clean/application.json", "image_ref": "fixtures/01-spirits-clean/label.png", "expected_disposition": "pass", "expected_per_rule": [{"rule_id": "FR-200-government-warning", "result": "pass"}, {"rule_id": "FR-300-class-type", "result": "pass"}, {"rule_id": "FR-400-abv-tolerance", "result": "pass"}, {"rule_id": "FR-500-net-contents", "result": "pass"}], "provenance": {"source": "synthetic-acme-distilling"}, "class_balance_tag": "spirits", "borderline_band": false}
{"label_id": "FIX-02-STONES-THROW", "application_ref": "fixtures/02-bourbon-stones-throw/application.json", "image_ref": "fixtures/02-bourbon-stones-throw/label.png", "expected_disposition": "pass", "expected_per_rule": [{"rule_id": "FR-300-class-type", "result": "pass"}], "provenance": {"source": "synthetic-stones-throw"}, "class_balance_tag": "spirits", "borderline_band": false}
{"label_id": "FIX-03-WARNING-TITLE-CASE", "application_ref": "fixtures/03-warning-title-case/application.json", "image_ref": "fixtures/03-warning-title-case/label.png", "expected_disposition": "fail", "expected_per_rule": [{"rule_id": "FR-200-government-warning", "result": "fail", "reason_code": "WARN.CASE.TITLECASE"}], "provenance": {"source": "synthetic-acme-titlecase"}, "class_balance_tag": "spirits", "borderline_band": false}
{"label_id": "FIX-04-LOW-RES-BLURRY", "application_ref": "fixtures/04-low-res-blurry/application.json", "image_ref": "fixtures/04-low-res-blurry/label.png", "expected_disposition": "needs_review", "expected_per_rule": [{"rule_id": "FR-700-image-quality", "result": "needs_review", "reason_code": "IMG.QUALITY.BLUR_GLARE"}], "provenance": {"source": "synthetic-blur-glare-derived-from-01"}, "class_balance_tag": "spirits", "borderline_band": false}
{"label_id": "FIX-06-ABV-OUT-OF-TOLERANCE", "application_ref": "fixtures/06-abv-out-of-tolerance/application.json", "image_ref": "fixtures/06-abv-out-of-tolerance/label.png", "expected_disposition": "fail", "expected_per_rule": [{"rule_id": "FR-400-abv-tolerance", "result": "fail", "reason_code": "ABV.DELTA.OVER_1PCT"}], "provenance": {"source": "synthetic-acme-abv-mismatch"}, "class_balance_tag": "spirits", "borderline_band": false}
{"label_id": "FIX-07-BORDERLINE-CONFIDENCE", "application_ref": "fixtures/07-borderline-confidence/application.json", "image_ref": "fixtures/07-borderline-confidence/label.png", "expected_disposition": "needs_review", "expected_per_rule": [{"rule_id": "FR-704-confidence-aggregation", "result": "needs_review", "reason_code": "CONF.MEDIUM.BAND"}], "provenance": {"source": "synthetic-borderline-derived-from-01"}, "class_balance_tag": "spirits", "borderline_band": true}
```

Then add 12 more spirits, 17 wine, 13 malt entries — composed from public COLA Registry IDs (per L1 §2.1 prov rules) plus synthetic variants. The L2 executor expands this list to the full ~50; the schema and ratio gates are what enforce correctness. Use existing fixture-01..07 as the seed for borderline-band variants until ≥10 borderline entries land.

> **Note on COLA IDs.** When entering registry-sourced labels, set `provenance.source` to the public COLA TTB ID (e.g. `cola-22148001000123`); the file refs may point at locally-cached copies under `fixtures/_corpus/<id>/`.

- [ ] **Step 5: Author `eval/datasheet.md`**

```markdown
# Eval Corpus Datasheet (Gebru et al. 2021)

## §1 Motivation
Why was this corpus created? — To gate the macro-F1 ≥ 0.70 AC of the TTB Label
Verification prototype (PRD v0.6 §8.4) and to surface per-rule recall on
government-health-warning rules (FR-200 through FR-205).

## §2 Composition
~50 labels: spirits 30–40%, wine 30–40%, malt 20–30%; ≥10 borderline-band labels;
synthetic share ≤30%. See `manifest.jsonl` for the full enumeration.

## §3 Collection process
Synthetic labels are generated by the `scripts/build_fixture_*.py` set; registry
labels are referenced by their public COLA ID and locally cached under
`fixtures/_corpus/<id>/` (cache only — original is the public TTB Public COLA
Registry source, BRD §8.2 prototype tier no-PII).

## §4 Preprocessing
None at corpus level — fixtures are stored at the resolution they are evaluated
against. Quality-degradation fixtures (04, 07) carry their degradation in the
committed PNG.

## §5 Uses
Eval harness only. Not training data; the system has no learnable parameters
beyond rule-pack thresholds (which are tuned out-of-band per PRD §3.2 v0.3
stretch automated re-calibration).

## §6 Distribution
The corpus ships with the repository under `eval/manifest.jsonl` and the
`fixtures/` tree.

## §7 Maintenance
Owner: project team. Updates triggered by rule-pack version bumps or
LLM_MODEL_SNAPSHOT changes; see `scripts/regenerate_fixtures.py` (T8).
```

- [ ] **Step 6: Run schema test; expect PASS (manifest validates and ratios hold once full corpus is authored)**

```bash
cd projects/takehome && uv run pytest tests/test_eval_manifest_schema.py -v
```
Expected: PASS once the executor adds the rest of the ~50 entries to satisfy ratios.

> **Manifest scope decision.** This L2 ships the **20-entry smoke subset** as the AC-gating manifest: the 6 fixture-derived entries authored above (FIX-01..FIX-04, FIX-06, FIX-07) **plus 14 additional entries** the executor authors in this task — 8 spirits / 4 wine / 2 malt — sourced from public COLA Registry IDs and locally cached under `fixtures/_corpus/<cola-id>/`. Class-balance assertions in the schema test cover this 20-entry shape (spirits 0.30–0.40 → 6–8/20; wine 0.30–0.40 → 6–8/20; malt 0.20–0.30 → 4–6/20). **Borderline floor for the smoke split is ≥4** (down from PRD ≥10, which was sized against the ~50-entry full corpus): the executor satisfies it by setting `borderline_band: true` on FIX-07 (already), FIX-04 (re-classify the blur+glare entry as borderline — it inherently is), plus 2 of the 14 new entries (1 wine + 1 malt borderline-confidence variant). The PRD ≥10 floor is preserved for the wine/malt depth-expansion follow-up that lifts the corpus to ~50.
>
> **Wine/malt depth-expansion to ~50 entries is a tracked follow-up**, not part of this L2: see L1 §6 stretch ("Wine / Malt depth — stretch (parent §8); rule-pack additions; lands in E2 if pulled in"). When pulled in, a follow-up task expands the manifest under the same `ManifestEntry` schema; no L2 re-write needed.
>
> Per-rule positive coverage ≥1 case per rule (L1 §4 exit-gate item 3) is the minimum the 20-entry corpus must hit; the executor's 14 additional entries SHOULD include at least one positive case for each FR-200..FR-205 rule and one for FR-300/400/500/700.

- [ ] **Step 7: Commit**

```bash
cd projects/takehome
git add eval/__init__.py eval/_schema.py eval/manifest.jsonl eval/datasheet.md \
        tests/test_eval_manifest_schema.py
git commit -m "feat(eval): manifest line schema + datasheet + initial corpus (E8 T2)"
```


---

### Wave 2 — Metrics + Dashboard (2 parallel; depend on T2)

---
### Task 3 — Eval metrics

**Files:**
- Create: `eval/metrics.py`
- Test: `tests/test_eval_metrics.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_eval_metrics.py
from eval.metrics import (
    macro_f1, per_rule_precision_recall, expected_calibration_error,
    cost_weighted_score, latency_percentiles,
)


def test_macro_f1_perfect():
    pred = ["pass", "fail", "needs_review"]
    actual = ["pass", "fail", "needs_review"]
    assert macro_f1(pred, actual) == 1.0


def test_macro_f1_balanced_errors():
    pred = ["pass", "pass", "fail"]
    actual = ["pass", "fail", "fail"]
    f1 = macro_f1(pred, actual)
    assert 0.5 <= f1 <= 0.8


def test_per_rule_precision_recall_only_warning_rules():
    per_label_rule_results = [
        {"FR-200-government-warning": ("pass", "pass")},
        {"FR-200-government-warning": ("fail", "pass")},  # FP
        {"FR-200-government-warning": ("pass", "fail")},  # FN
    ]
    pr = per_rule_precision_recall(per_label_rule_results)
    p, r = pr["FR-200-government-warning"]
    assert p == 0.5  # 1 TP / (1 TP + 1 FP)
    assert r == 0.5  # 1 TP / (1 TP + 1 FN)


def test_cost_weighted_score_penalizes_false_pass_more():
    """T9 Q9.1 — false-pass weighted higher than false-reject."""
    # Same raw error count, composition differs: false-pass dominates one, false-reject the other.
    fp_dominant = (["pass"] * 3 + ["fail"] * 1, ["fail"] * 3 + ["fail"] * 1)
    fn_dominant = (["fail"] * 3 + ["pass"] * 1, ["pass"] * 3 + ["pass"] * 1)
    score_fp = cost_weighted_score(*fp_dominant)
    score_fn = cost_weighted_score(*fn_dominant)
    assert score_fp < score_fn


def test_latency_percentiles():
    latencies = [0.1, 0.2, 0.5, 1.0, 5.0]
    p = latency_percentiles(latencies)
    assert p["p50"] == 0.5
    assert p["p95"] >= 4.0


def test_ece_perfectly_calibrated():
    confidences = [0.9, 0.9, 0.9, 0.1]
    correct = [True, True, True, False]
    ece = expected_calibration_error(confidences, correct, n_bins=10)
    assert ece < 0.05
```

- [ ] **Step 2: Run; expect FAIL**

```bash
cd projects/takehome && uv run pytest tests/test_eval_metrics.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement metrics**

```python
# eval/metrics.py
"""Eval metrics: macro-F1, per-rule P/R, ECE, latency, cost-weighted score (cost-weighted accuracy per T9 Q9.1)."""
from __future__ import annotations

from collections import defaultdict
from statistics import quantiles
from typing import Literal

Disposition = Literal["pass", "fail", "needs_review"]
DISPOSITIONS: tuple[Disposition, ...] = ("pass", "fail", "needs_review")

# T9 Q9.1 / BRD §8.2 (regulator-facing prototype tier): a false PASS — the system
# clears a label that violates a TTB regulation — exposes the agency to
# downstream enforcement risk and applicant trust damage. A false REJECT — the
# system flags a compliant label — costs the applicant one re-review cycle.
# The 3:1 ratio matches the T9 Q9.1 starting point and is intentionally rounded
# (the prototype is not an FDA-equivalent ratio elicitation). To re-tune,
# override the constants below or wire to a Settings field; the metric is
# additive in the weights so any future calibration plugs in without API change.
COST_FALSE_PASS = 3.0
COST_FALSE_REJECT = 1.0


def _confusion(pred: list[Disposition], actual: list[Disposition]) -> dict[tuple[str, str], int]:
    cm: dict[tuple[str, str], int] = defaultdict(int)
    for p, a in zip(pred, actual, strict=True):
        cm[(p, a)] += 1
    return dict(cm)


def macro_f1(pred: list[Disposition], actual: list[Disposition]) -> float:
    cm = _confusion(pred, actual)
    f1s: list[float] = []
    for d in DISPOSITIONS:
        tp = cm.get((d, d), 0)
        fp = sum(cm.get((d, a), 0) for a in DISPOSITIONS if a != d)
        fn = sum(cm.get((p, d), 0) for p in DISPOSITIONS if p != d)
        if tp + fp == 0 or tp + fn == 0:
            f1s.append(0.0)
            continue
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        if precision + recall == 0:
            f1s.append(0.0)
        else:
            f1s.append(2 * precision * recall / (precision + recall))
    return sum(f1s) / len(f1s)


def per_rule_precision_recall(
    per_label_rule_results: list[dict[str, tuple[Disposition, Disposition]]],
) -> dict[str, tuple[float, float]]:
    """Each label's rule results = {rule_id: (predicted, expected)}."""
    out: dict[str, tuple[float, float]] = {}
    by_rule: dict[str, list[tuple[Disposition, Disposition]]] = defaultdict(list)
    for label in per_label_rule_results:
        for rule_id, (p, e) in label.items():
            by_rule[rule_id].append((p, e))
    for rule_id, results in by_rule.items():
        # Treat fail/needs_review as "positive"; pass as "negative".
        tp = sum(1 for p, e in results if p != "pass" and e != "pass")
        fp = sum(1 for p, e in results if p != "pass" and e == "pass")
        fn = sum(1 for p, e in results if p == "pass" and e != "pass")
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        out[rule_id] = (precision, recall)
    return out


def cost_weighted_score(pred: list[Disposition], actual: list[Disposition]) -> float:
    """Cost-weighted accuracy per T9 Q9.1: 1 - (3·false_pass + 1·false_reject) / (3·n).

    Range [0, 1]; monotonic decreasing in each error count. Named "score", not "f1",
    because it is not a precision/recall composition — it is a cost-scaled accuracy.
    Reported on the dashboard alongside macro_f1 to surface the FP/FR asymmetry the
    regulator-facing prototype tier (BRD §8.2) cares about."""
    cm = _confusion(pred, actual)
    # False pass: predicted "pass" but actual was fail / needs_review.
    false_pass = sum(cm.get(("pass", a), 0) for a in ("fail", "needs_review"))
    # False reject: predicted "fail" but actual was pass.
    false_reject = cm.get(("fail", "pass"), 0)
    correct = sum(cm.get((d, d), 0) for d in DISPOSITIONS)
    n = correct + sum(cm.get((p, a), 0) for p in DISPOSITIONS for a in DISPOSITIONS if p != a)
    if n == 0:
        return 0.0
    weighted_errors = COST_FALSE_PASS * false_pass + COST_FALSE_REJECT * false_reject
    max_weighted = COST_FALSE_PASS * n
    return 1.0 - weighted_errors / max_weighted


def latency_percentiles(latencies_s: list[float]) -> dict[str, float]:
    if not latencies_s:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
    sorted_ls = sorted(latencies_s)

    def pct(p: float) -> float:
        idx = max(0, min(len(sorted_ls) - 1, int(round(p * (len(sorted_ls) - 1)))))
        return sorted_ls[idx]

    return {"p50": pct(0.50), "p95": pct(0.95), "p99": pct(0.99)}


def expected_calibration_error(
    confidences: list[float], correct: list[bool], n_bins: int = 10,
) -> float:
    """Standard ECE (Naeini et al.)."""
    if not confidences:
        return 0.0
    n = len(confidences)
    bin_width = 1.0 / n_bins
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b * bin_width, (b + 1) * bin_width
        in_bin = [(c, ok) for c, ok in zip(confidences, correct, strict=True) if lo <= c < hi or (b == n_bins - 1 and c == hi)]
        if not in_bin:
            continue
        avg_conf = sum(c for c, _ in in_bin) / len(in_bin)
        accuracy = sum(1 for _, ok in in_bin if ok) / len(in_bin)
        ece += (len(in_bin) / n) * abs(avg_conf - accuracy)
    return ece
```

- [ ] **Step 4: Run; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_eval_metrics.py -v
```
Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
cd projects/takehome
git add eval/metrics.py tests/test_eval_metrics.py
git commit -m "feat(eval): metrics — macro-F1, per-rule P/R, ECE, cost-weighted F1 (E8 T3)"
```

---
### Task 6 — Eval dashboard

**Files:**
- Create: `eval/dashboard.py`, `eval/templates/dashboard.html`
- Test: `tests/test_eval_dashboard_render.py`

- [ ] **Step 1: Write the rendering test**

```python
# tests/test_eval_dashboard_render.py
from pathlib import Path

from eval.dashboard import render_dashboard


def test_render_dashboard_against_synthetic_history(tmp_path):
    history = tmp_path / "history"
    history.mkdir()
    (history / "summary.json").write_text(
        '{"runs": [{"timestamp": "2026-05-04T00:00:00+00:00", '
        '"subset": "smoke", "macro_f1": 0.85}]}'
    )
    (history / "2026-05-04T00-00-00+00-00.json").write_text("""{
        "timestamp": "2026-05-04T00:00:00+00:00",
        "subset": "smoke",
        "n_labels": 20,
        "macro_f1": 0.85,
        "per_rule_precision": {"FR-200-government-warning": 0.9},
        "per_rule_recall": {"FR-200-government-warning": 0.85},
        "ece": 0.04,
        "latency_p50_s": 1.2,
        "latency_p95_s": 4.1,
        "latency_p99_s": 4.9,
        "cost_weighted_score": 0.79
    }""")

    html = render_dashboard(history_dir=history)
    assert "macro_f1" in html.lower() or "macro-f1" in html.lower()
    assert "0.85" in html
    assert "FR-200-government-warning" in html
    assert "Confusion" in html or "confusion" in html
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Implement `eval/dashboard.py`**

```python
# eval/dashboard.py
"""Render /eval HTML against eval/history/. Server-side Jinja2."""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(("html",)),
)


def render_dashboard(history_dir: Path) -> str:
    summary_path = history_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.is_file() else {"runs": []}

    latest = None
    history_files = sorted(p for p in history_dir.glob("*.json") if p.name != "summary.json")
    if history_files:
        latest = json.loads(history_files[-1].read_text())

    template = _env.get_template("dashboard.html")
    return template.render(summary=summary, latest=latest)
```

```html
<!-- eval/templates/dashboard.html -->
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TTB Label Verification — Eval Dashboard</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
    th { background: #f7f7f7; }
    .metric { font-size: 1.6rem; font-weight: 600; }
    .ok { color: #1a7f37; }
    .warn { color: #b08800; }
    .fail { color: #cf222e; }
  </style>
</head>
<body>
  <h1>TTB Label Verification — Eval Dashboard</h1>

  {% if not latest %}
    <p>No eval runs recorded yet. Run <code>uv run task eval-smoke</code>.</p>
  {% else %}
    <h2>Latest run — {{ latest.subset }} @ {{ latest.timestamp }}</h2>
    <p>n labels: <strong>{{ latest.n_labels }}</strong></p>
    <p>macro-F1: <span class="metric {% if latest.macro_f1 >= 0.70 %}ok{% else %}fail{% endif %}">{{ "%.3f"|format(latest.macro_f1) }}</span> (gate: 0.70)</p>
    <p>cost-weighted score: <span class="metric">{{ "%.3f"|format(latest.cost_weighted_score) }}</span></p>
    <p>ECE: {{ "%.3f"|format(latest.ece) }} · latency p50/p95/p99 s: {{ "%.2f"|format(latest.latency_p50_s) }} / {{ "%.2f"|format(latest.latency_p95_s) }} / {{ "%.2f"|format(latest.latency_p99_s) }}</p>

    <h3>Per-rule precision / recall</h3>
    <table>
      <thead><tr><th>Rule</th><th>Precision</th><th>Recall</th></tr></thead>
      <tbody>
      {% for rule_id, p in latest.per_rule_precision.items() %}
        {% set r = latest.per_rule_recall[rule_id] %}
        <tr>
          <td>{{ rule_id }}</td>
          <td>{{ "%.2f"|format(p) }}</td>
          <td class="{% if rule_id.startswith('FR-20') and r >= 0.80 %}ok{% elif rule_id.startswith('FR-20') %}fail{% endif %}">{{ "%.2f"|format(r) }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>

    <h3>Run history</h3>
    <table>
      <thead><tr><th>Timestamp</th><th>Subset</th><th>macro-F1</th></tr></thead>
      <tbody>
      {% for run in summary.runs %}
        <tr><td>{{ run.timestamp }}</td><td>{{ run.subset }}</td><td>{{ "%.3f"|format(run.macro_f1) }}</td></tr>
      {% endfor %}
      </tbody>
    </table>
  {% endif %}

  <h3>Confusion matrix</h3>
  <p><em>Rendered from latest run history; chart island deferred to T16 stretch.</em></p>
</body>
</html>
```

- [ ] **Step 4: Run; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_eval_dashboard_render.py -v
```

- [ ] **Step 5: Commit**

```bash
cd projects/takehome
git add eval/dashboard.py eval/templates/dashboard.html tests/test_eval_dashboard_render.py
git commit -m "feat(eval): /eval dashboard renderer + Jinja2 template (E8 T6)"
```

---

### Wave 3 — Harness + Route (2 parallel; depend on Wave 1+2)

---
### Task 5 — Eval harness

**Files:**
- Create: `eval/harness.py`, `eval/history/.gitkeep`
- Test: `tests/test_eval_harness.py` (deferred green to T12 — this task only ships the module)

- [ ] **Step 1: Write the harness CLI test**

```python
# tests/test_eval_harness_cli.py
import subprocess
from pathlib import Path


def test_harness_module_invocable():
    """`python -m eval.harness --help` should print usage."""
    result = subprocess.run(
        ["python", "-m", "eval.harness", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "--subset" in result.stdout
    assert "smoke" in result.stdout and "full" in result.stdout


def test_harness_writes_history_record(tmp_path, monkeypatch):
    """Smoke run with a fake evaluator writes a timestamped history JSON."""
    from eval.harness import run_subset
    from eval._schema import HistoryRecord

    history_dir = tmp_path / "history"
    history_dir.mkdir()

    # The harness accepts an injected evaluator for testability.
    def fake_evaluator(entry):
        return entry.expected_disposition, entry.expected_per_rule, 0.42, 0.88

    record = run_subset(subset="smoke", manifest_path=Path("eval/manifest.jsonl"),
                       history_dir=history_dir, evaluator=fake_evaluator)
    assert isinstance(record, HistoryRecord)
    assert record.subset == "smoke"
    assert record.macro_f1 == 1.0  # fake returns expected, so perfect
    files = list(history_dir.glob("*.json"))
    assert len(files) == 1
    assert (history_dir / "summary.json").is_file()
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Implement `eval/harness.py`**

```python
# eval/harness.py
"""Eval harness — runs the manifest through the Application Service.

CLI:  python -m eval.harness --subset {smoke,full} [--history-dir eval/history]

Programmatic:  run_subset(subset, manifest_path, history_dir, evaluator)
  where `evaluator` takes a ManifestEntry and returns
  (predicted_disposition, predicted_per_rule, latency_s, confidence).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from eval._schema import HistoryRecord, ManifestEntry
from eval.metrics import (
    cost_weighted_score, expected_calibration_error,
    latency_percentiles, macro_f1, per_rule_precision_recall,
)

SMOKE_SIZE = 20

EvaluatorFn = Callable[[ManifestEntry], tuple[str, list, float, float]]


def _load_manifest(path: Path) -> list[ManifestEntry]:
    return [ManifestEntry.model_validate_json(line)
            for line in path.read_text().splitlines() if line.strip()]


def _live_evaluator(entry: ManifestEntry) -> tuple[str, list, float, float]:
    """Live `Evaluator` adapter — DEFERRED to T14 (post-merge close-out).

    Why deferred: the real `app.services.evaluator.Evaluator` is **async**, takes
    typed `Application` + `Label` Pydantic objects (not string paths), and
    returns `DispositionEnvelope` with `disposition_confidence` +
    `audit_trail.per_rule_trace[]` — there is no `per_rule` attribute and no
    `aggregate_confidence` attribute. Building the manifest-ref → Application/Label
    loaders + asyncio glue (`asyncio.run`) + envelope-mapper
    (`audit_trail.per_rule_trace` → `[{rule_id, result}]`; confidence sourced from
    `disposition_confidence.numeric`, the min-over-fields per the schema docstring)
    is a meaningful chunk of work that doesn't gate this L2's tests:

      - Smoke tests inject an explicit `evaluator` fake (see test_eval_harness_cli.py
        and tests/test_eval_harness.py).
      - Full eval (`tests/test_eval_full.py`) uses `pytest.importorskip` and
        `@pytest.mark.slow` — it skips by default.

    T14 (post-merge close-out, owned by whichever session merges last) wires this
    adapter against the live pipeline.
    """
    raise NotImplementedError(
        "Live evaluator adapter is implemented in T14 (post-merge close-out). "
        "Pass an explicit `evaluator` argument to `run_subset` to use a fake."
    )


def run_subset(
    subset: str,
    manifest_path: Path,
    history_dir: Path,
    evaluator: EvaluatorFn = _live_evaluator,
) -> HistoryRecord:
    entries = _load_manifest(manifest_path)
    if subset == "smoke":
        entries = entries[:SMOKE_SIZE]

    pred_disp: list = []
    actual_disp: list = []
    latencies: list[float] = []
    confidences: list[float] = []
    correct: list[bool] = []
    per_rule_results: list[dict] = []

    for entry in entries:
        p_disp, p_rules, latency, confidence = evaluator(entry)
        pred_disp.append(p_disp)
        actual_disp.append(entry.expected_disposition)
        latencies.append(latency)
        confidences.append(confidence)
        correct.append(p_disp == entry.expected_disposition)

        rule_pairs: dict[str, tuple[str, str]] = {}
        expected_by_id = {r.rule_id: r.result for r in entry.expected_per_rule}
        for r in p_rules:
            rid = r["rule_id"]
            if rid in expected_by_id:
                rule_pairs[rid] = (r["result"], expected_by_id[rid])
        per_rule_results.append(rule_pairs)

    pr = per_rule_precision_recall(per_rule_results)
    lats = latency_percentiles(latencies)

    record = HistoryRecord(
        timestamp=datetime.now(timezone.utc).isoformat(),
        subset=subset,
        n_labels=len(entries),
        macro_f1=macro_f1(pred_disp, actual_disp),
        per_rule_precision={k: v[0] for k, v in pr.items()},
        per_rule_recall={k: v[1] for k, v in pr.items()},
        ece=expected_calibration_error(confidences, correct),
        latency_p50_s=lats["p50"],
        latency_p95_s=lats["p95"],
        latency_p99_s=lats["p99"],
        cost_weighted_score=cost_weighted_score(pred_disp, actual_disp),
    )

    history_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = record.timestamp.replace(":", "-")
    (history_dir / f"{safe_ts}.json").write_text(record.model_dump_json(indent=2))

    summary_path = history_dir / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.is_file() else {"runs": []}
    summary["runs"].append({"timestamp": record.timestamp, "subset": subset,
                             "macro_f1": record.macro_f1})
    summary_path.write_text(json.dumps(summary, indent=2))

    return record


def _main() -> int:
    parser = argparse.ArgumentParser(description="TTB Label Verification eval harness")
    parser.add_argument("--subset", choices=("smoke", "full"), required=True)
    parser.add_argument("--manifest", type=Path, default=Path("eval/manifest.jsonl"))
    parser.add_argument("--history-dir", type=Path, default=Path("eval/history"))
    args = parser.parse_args()

    record = run_subset(args.subset, args.manifest, args.history_dir)
    print(f"macro_f1={record.macro_f1:.3f} cost_weighted_score={record.cost_weighted_score:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
```

- [ ] **Step 4: Add `.gitkeep`**

```bash
touch projects/takehome/eval/history/.gitkeep
```

- [ ] **Step 5: Run CLI test; expect PASS for `--help`, programmatic test PASSes**

```bash
cd projects/takehome && uv run pytest tests/test_eval_harness_cli.py -v
```

- [ ] **Step 6: Commit**

```bash
cd projects/takehome
git add eval/harness.py eval/history/.gitkeep tests/test_eval_harness_cli.py
git commit -m "feat(eval): harness CLI + programmatic API + history persistence (E8 T5)"
```


---
### Task 7 — `/eval` route (DEV_MODE-gated)

**Files:**
- Create: `app/api/eval.py`
- Modify: `app/main.py` (register router conditionally on `settings.dev_mode`)
- Test: `tests/test_eval_dashboard_route.py`

- [ ] **Step 1: Write the route test**

```python
# tests/test_eval_dashboard_route.py
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def _client(dev_mode: bool) -> TestClient:
    # Construct Settings explicitly and pass to the create_app factory — avoids
    # importlib.reload + os.environ mutation, both of which leak into sibling
    # tests via the module-level `app: FastAPI = create_app()` at the bottom of
    # app/main.py.
    return TestClient(create_app(settings=Settings(dev_mode=dev_mode)))


def test_eval_route_404_when_dev_mode_off():
    client = _client(dev_mode=False)
    r = client.get("/eval")
    assert r.status_code == 404


def test_eval_route_200_when_dev_mode_on():
    client = _client(dev_mode=True)
    r = client.get("/eval")
    assert r.status_code == 200
    assert "TTB Label Verification" in r.text
```

- [ ] **Step 2: Run; expect FAIL**

- [ ] **Step 3: Implement `app/api/eval.py`**

```python
# app/api/eval.py
"""GET /eval — DEV_MODE-gated eval dashboard route (E8 T7).

Only registered when settings.dev_mode is truthy. See app/main.py.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from eval.dashboard import render_dashboard

router = APIRouter(tags=["eval"])
# Repo-root-relative; resolves correctly regardless of CWD or container WORKDIR.
# app/api/eval.py → parents[0]=api, [1]=app, [2]=repo root.
_HISTORY_DIR = Path(__file__).resolve().parents[2] / "eval" / "history"


@router.get("/eval", response_class=HTMLResponse)
async def eval_dashboard() -> str:
    return render_dashboard(history_dir=_HISTORY_DIR)
```

- [ ] **Step 4: Modify `app/main.py` to register conditionally**

Post-rebase onto current `main`, `create_app(settings: Settings | None = None)` already includes 6 routers in this order: `healthz`, `ui`, `labels`, `raw`, `batches`, `overrides` (the `ui_router` was added by E7 in commit `60519d6`). Add the conditional `eval_router` include **after the existing block**, before any return statement:

```python
# In create_app(), AFTER all existing application.include_router(...) lines:
if settings.dev_mode:
    from app.api.eval import router as eval_router
    application.include_router(eval_router)
```

`Settings.dev_mode` already exists at `app/config.py:52` (`dev_mode: bool = Field(default=False, alias="DEV_MODE")`) — no schema change required.

- [ ] **Step 5: Run; expect PASS**

```bash
cd projects/takehome && uv run pytest tests/test_eval_dashboard_route.py -v
```

- [ ] **Step 6: Commit**

```bash
cd projects/takehome
git add app/api/eval.py app/main.py tests/test_eval_dashboard_route.py
git commit -m "feat(api): GET /eval DEV_MODE-gated dashboard route (E8 T7)"
```

---

---

### Wave 4 — Harness tests (1 task; depends on T5)

---
### Task 12 — Eval harness + dashboard route tests

**Files:**
- Create: `tests/test_eval_harness.py`, `tests/test_eval_full.py`
- (Existing from T7: `tests/test_eval_dashboard_route.py`)

- [ ] **Step 1: Write smoke + full eval tests**

```python
# tests/test_eval_harness.py
"""Smoke eval — HARNESS MECHANICS test, not the AC gate.

These tests pass a tautological fake evaluator that returns each entry's
expected disposition verbatim, so `macro_f1 == 1.0` and per-rule recall == 1.0
by construction. They verify that:

  - `run_subset` plumbs entries → fake → metrics → history correctly,
  - History records serialize against `HistoryRecord` shape,
  - The smoke subset honors the SMOKE_SIZE cap.

The **real AC-§8.4 gate** (macro-F1 ≥ 0.70 against the live `Evaluator`) lives
in `tests/test_eval_full.py` and is exercised by T14 once E5+E6 land.
"""
from pathlib import Path

from eval._schema import HistoryRecord
from eval.harness import run_subset


def test_smoke_subset_writes_history(tmp_path):
    history = tmp_path / "history"
    history.mkdir()

    def fake(entry):
        # Return expected to drive a clean run
        return entry.expected_disposition, [
            {"rule_id": r.rule_id, "result": r.result} for r in entry.expected_per_rule
        ], 0.5, 0.85

    record = run_subset("smoke", Path("eval/manifest.jsonl"), history, fake)
    assert isinstance(record, HistoryRecord)
    assert record.subset == "smoke"
    assert record.n_labels <= 20
    assert record.macro_f1 == 1.0
    assert record.latency_p50_s == 0.5


def test_smoke_subset_recall_gate_for_warning_rules(tmp_path):
    """Per-rule recall ≥ 0.80 on FR-200 series when all expected rules predict correctly."""
    history = tmp_path / "history"
    history.mkdir()

    def fake(entry):
        return entry.expected_disposition, [
            {"rule_id": r.rule_id, "result": r.result} for r in entry.expected_per_rule
        ], 0.5, 0.85

    record = run_subset("smoke", Path("eval/manifest.jsonl"), history, fake)
    for rule_id, recall in record.per_rule_recall.items():
        if rule_id.startswith("FR-20"):
            assert recall >= 0.80, f"{rule_id} recall {recall} < 0.80"
```

```python
# tests/test_eval_full.py
"""Full eval — ~50 labels; merge-to-main gate; gated by @pytest.mark.slow."""
from pathlib import Path

import pytest

from eval.harness import run_subset


@pytest.mark.slow
def test_full_subset_macro_f1_gate(tmp_path):
    """AC-§8.4: macro-F1 ≥ 0.70 on the ~50-label corpus.

    BLOCKED on E5+E6: runs against the live Evaluator. The smoke variant
    above exercises the harness mechanics with a fake; this test exercises
    the AC-§8.4 number with the real pipeline.
    """
    pytest.importorskip("app.services.application", reason="E5+E6 required for live full eval")
    history = tmp_path / "history"
    history.mkdir()
    record = run_subset("full", Path("eval/manifest.jsonl"), history)
    assert record.macro_f1 >= 0.70, f"AC-§8.4 macro-F1 {record.macro_f1} < 0.70"

    # Per-rule recall ≥ 0.80 on FR-200 through FR-205
    for rid, recall in record.per_rule_recall.items():
        if rid.startswith("FR-20") and rid[5:].split("-")[0] in {"200", "201", "202", "203", "204", "205"}:
            assert recall >= 0.80, f"{rid} recall {recall} < 0.80"
```

- [ ] **Step 2: Run; expect smoke PASS, full SKIP**

```bash
cd projects/takehome && uv run pytest tests/test_eval_harness.py -v
cd projects/takehome && uv run pytest tests/test_eval_full.py -v -m slow
```

- [ ] **Step 3: Commit**

```bash
cd projects/takehome
git add tests/test_eval_harness.py tests/test_eval_full.py
git commit -m "test(eval): smoke + full subset gates (full skips until E5+E6) (E8 T12)"
```

---

---

## 4. Self-review

**Spec coverage (vs L1 §2 components delivered):**

| L1 §2.x | This split's task |
|---|---|
| 2.4 Eval harness (`eval/`) | T2, T3, T5 |
| 2.5 `/eval` route | T7 |
| 2.6 Eval dashboard | T6 |
| 2.10 Test surface (eval portion) | T12 |

**Out of scope for this split (handled by data+infra split or post-merge):**

| L1 §2.x | Owner |
|---|---|
| 2.1 Demo fixtures | data+infra split (T1, T15) |
| 2.2 Demo cache | data+infra split (T8) |
| 2.3 Cache regeneration | data+infra split (T8) |
| 2.6 Deployment | data+infra split (T4, T13) |
| 2.7 Demo runbook | data+infra split (T10) |
| 2.9 README upgrade | data+infra split (T9) |
| AC-§8.4 macro-F1 ≥ 0.70 | post-merge T14 |

**Type consistency:** `ManifestEntry`, `HistoryRecord`, `Provenance`, `ExpectedRule` defined in T2 and consumed in T3, T5, T6, T7, T12.

**E5 surface this split assumes (already on `main`):**
`Evaluator(demo_cache: bool = False).evaluate(application_ref: str, image_ref: str) -> DispositionEnvelope` with `disposition`, `per_rule[]`, `aggregate_confidence`, `lowest_confidence_field`, `audit_trail`. If the actual surface differs, T5/T12 adjust at green-time.

---

## 5. Out of scope for this L2

- Demo fixtures, cache regenerator, Docker/HF Space, README, RUNBOOK — owned by the data+infra split.
- T14 (live `eval-full` AC), T15 (fixture-05 batch), T16 (recording), T17 (L1 hand-back) — joint close-out / E7-blocked.

---

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Manifest ratio gates fail because executor only seeds 6 entries | Medium | Medium | T2 step 6 explicitly requires expanding the manifest to ~20 entries; the schema test is the gate |
| `Evaluator` signature in E5 differs from the one assumed in T5/T12 | Low | Low | T12 full test uses `pytest.importorskip` and is `@pytest.mark.slow`; smoke test uses an injected fake. Signature mismatch caught at green-time on `main` post-merge |
| `app/main.py` router-registration block doesn't conditionally import based on `dev_mode` | Low | Low | T7 step 4 explicitly states the conditional import pattern; if `Settings.dev_mode` doesn't exist yet, T7 also adds the field to `app/config.py` |
| `eval/manifest.jsonl` references registry IDs that don't exist locally | Medium | Low | T2 explicitly notes the local-cache convention `fixtures/_corpus/<id>/`; the schema test does not require image existence — T14 (post-merge) is the operational test |

---

## 7. Change log

| Version | Date | Author | Notes |
|---|---|---|---|
| 0.1 | 2026-05-04 | Project team | Initial split — extracted T2/T3/T5/T6/T7/T12 from master `.draft` for parallel execution. |
| 0.2 | 2026-05-04 | Project team (eval session) | Plan-review patches + rebase onto current `main` (post-E7). Changes: (a) **Rebased** branch from stale `feat/e8-backend` to current `origin/main` so E7's `ui_router` and frontend additions are present; T7's `app/main.py` insertion guidance updated for the post-E7 router list. (b) **T2** — fixed malformed `assert` (line 111 was a tuple expression); reduced borderline floor from ≥10 to ≥4 for the smoke 20-entry split (PRD ≥10 stays for the full ~50 corpus follow-up); enumerated which entries get `borderline_band=true`. (c) **T3** — renamed `cost_of_error_weighted_f1` → `cost_weighted_score` (the metric is a cost-weighted accuracy, not an F1 — name was misleading); rename propagates to `HistoryRecord` field, T5 imports/build, T6 dashboard. (d) **T5** — `_live_evaluator` now `raise NotImplementedError` with explicit deferral note; the real `Evaluator` is async + takes Pydantic objects + returns a different envelope shape (`disposition_confidence`, `audit_trail.per_rule_trace[]`, no `per_rule`/`aggregate_confidence`) — the adapter is T14 work. Smoke tests still inject fakes; full test still skips via `importorskip`. (e) **T6** — fixed dead `{% elif r >= 0.80 %}` branch in dashboard template (no class emitted). (f) **T7** — `_HISTORY_DIR` is now `Path(__file__).resolve().parents[2] / "eval" / "history"` (CWD-independent); test no longer reloads modules — uses `Settings(dev_mode=...)` + `create_app(settings=...)` directly. |

---

## 8. Dependency Graph

### Task Dependencies

| Task | Depends On | Blocks | Files Owned |
|------|-----------|--------|-------------|
| T2 manifest + datasheet + schema | — | T3, T5, T6, T7 | `eval/__init__.py`, `eval/_schema.py`, `eval/manifest.jsonl`, `eval/datasheet.md`, `tests/test_eval_manifest_schema.py` |
| T3 metrics | T2 | T5 | `eval/metrics.py`, `tests/test_eval_metrics.py` |
| T5 eval harness | T2, T3 | T7, T12 | `eval/harness.py`, `eval/history/.gitkeep`, `tests/test_eval_harness_cli.py` |
| T6 eval dashboard | T2 | T7 | `eval/dashboard.py`, `eval/templates/dashboard.html`, `tests/test_eval_dashboard_render.py` |
| T7 `/eval` route | T6 | — | `app/api/eval.py`, `app/main.py` (modify), `tests/test_eval_dashboard_route.py` |
| T12 eval harness tests | T5 | (post-merge T14) | `tests/test_eval_harness.py`, `tests/test_eval_full.py` |

### Execution Waves

```
Wave 1 (1 task):           [T2]                        ← root
Wave 2 (2 parallel):       [T3, T6]                    ← depend on T2
Wave 3 (2 parallel):       [T5, T7]                    ← T5 deps T2,T3; T7 deps T6
Wave 4 (1 task):           [T12]                       ← depends on T5
```

**Critical path:** T2 → T3 → T5 → T12 (4 waves).
**Concurrency cap:** 2 (well under the 6-task ceiling).

### Wave ownership-disjointness audit

- **Wave 1 (T2).** `eval/__init__.py`, `eval/_schema.py`, `eval/manifest.jsonl`, `eval/datasheet.md`. Trivially disjoint. ✓
- **Wave 2 (T3, T6).** `eval/metrics.py` (T3) ⨯ `eval/dashboard.py`, `eval/templates/dashboard.html` (T6). Disjoint. ✓
- **Wave 3 (T5, T7).** `eval/harness.py`, `eval/history/.gitkeep` (T5) ⨯ `app/api/eval.py`, `app/main.py`, `tests/test_eval_dashboard_route.py` (T7). Disjoint. ✓
- **Wave 4 (T12).** Single task, no overlap. ✓

### Execution Strategy

> **For Claude:** Use `parallel-plan-executor` to execute this plan. The executor dispatches every task in a wave concurrently (up to 6 at a time) and holds a barrier between waves. After the last wave lands, push the branch and notify the user; the post-merge close-out (T14, T15, T17) is owned by the user.

**Wave 1** — Dispatch T2 alone.
**Wave 2** — Dispatch T3, T6 concurrently in one message. Barrier; verify 2 commits.
**Wave 3** — Dispatch T5, T7 concurrently in one message. Barrier; verify 2 commits.
**Wave 4** — Dispatch T12 alone. Verify commit.

**After Wave 4 lands:** push `feat/e8-eval-pipeline`. Open PR or hand off to the user for merge coordination with `feat/e8-backend` (data+infra split).
