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
            rid = r["rule_id"] if isinstance(r, dict) else r.rule_id
            result = r["result"] if isinstance(r, dict) else r.result
            if rid in expected_by_id:
                rule_pairs[rid] = (result, expected_by_id[rid])
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
