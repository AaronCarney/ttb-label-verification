# eval/harness.py
"""Eval harness — runs the manifest through the Application Service.

CLI:  python -m eval.harness --subset {smoke,full} [--history-dir eval/history]

Programmatic:  run_subset(subset, manifest_path, history_dir, evaluator)
  where `evaluator` takes a ManifestEntry and returns
  (predicted_disposition, predicted_per_rule, latency_s, confidence).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
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

_EVALUATOR_SINGLETON = None  # lazy-init module-level Evaluator (T14)


def _load_manifest(path: Path) -> list[ManifestEntry]:
    return [ManifestEntry.model_validate_json(line)
            for line in path.read_text().splitlines() if line.strip()]


_EVAL_SLA_SECONDS = 60.0  # eval-time SLA (default 5s is too tight for live OpenAI)


def _get_evaluator():
    """Lazy module-level Evaluator so a harness run reuses one wiring."""
    global _EVALUATOR_SINGLETON
    if _EVALUATOR_SINGLETON is None:
        from app.config import Settings
        from app.deps import build_evaluator
        # Force cloud vision: local Paddle/SWT path isn't validated for eval and
        # nvidia-smi auto-detect can route to it on CUDA-present hosts.
        settings = Settings(vision_mode="cloud")
        _EVALUATOR_SINGLETON = build_evaluator(settings)
        # Stretch the per-eval SLA — live OpenAI calls routinely exceed the
        # production 5 s budget on cold paths.
        _EVALUATOR_SINGLETON._sla_seconds = _EVAL_SLA_SECONDS
    return _EVALUATOR_SINGLETON


def _build_application_from_entry(entry: ManifestEntry):
    """Construct an `Application` from `<image_dir>/expected.json`.

    The manifest's `application_ref` points at a non-existent `application.json`;
    the real fixture layout is `<dir>/{expected.json, label.png, notes.md}`. We
    derive the fixture dir from `image_ref` and parse `expected.json` (a list of
    ExpectedValue dicts; may be empty).
    """
    from app.schemas.application import Application
    from app.schemas.expected import ExpectedValue

    fixture_dir = Path(entry.image_ref).parent
    expected_path = fixture_dir / "expected.json"
    raw = json.loads(expected_path.read_text()) if expected_path.is_file() else []
    expected_values = tuple(ExpectedValue(**item) for item in raw)
    return Application(
        application_id=f"app-{entry.label_id.lower()}",
        evaluation_id=str(uuid.uuid4()),
        expected_values=expected_values,
    )


def _build_label_from_entry(entry: ManifestEntry):
    """Construct a `Label` envelope by reading `entry.image_ref` bytes."""
    from app.schemas.label import Label

    image_path = Path(entry.image_ref)
    image_bytes = image_path.read_bytes()
    suffix = image_path.suffix.lower()
    content_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    return Label(
        label_id=entry.label_id,
        batch_id=f"eval-{entry.label_id}",
        image_bytes=image_bytes,
        content_type=content_type,
        face_tag="front",
    )


def _per_rule_from_envelope(envelope) -> list[dict]:
    """Map `audit_trail.per_rule_trace[]` → `[{rule_id, result}]`.

    `not_applicable` collapses to `pass` for harness comparison (the manifest
    only carries pass/fail/needs_review).
    """
    out: list[dict] = []
    for entry in envelope.audit_trail.per_rule_trace:
        result = "pass" if entry.disposition == "not_applicable" else entry.disposition
        out.append({"rule_id": entry.rule_id, "result": result})
    return out


def _live_evaluator(entry: ManifestEntry) -> tuple[str, list, float, float]:
    """Live `Evaluator` adapter — runs the manifest entry through the real
    Application Service (vision + rules + orchestrator) and projects the
    `DispositionEnvelope` onto the harness contract.

    Returns: (disposition, per_rule_results, latency_s, confidence)
    """
    evaluator = _get_evaluator()
    application = _build_application_from_entry(entry)
    label = _build_label_from_entry(entry)

    t0 = time.monotonic()
    envelope = asyncio.run(evaluator.evaluate(application, label))
    latency_s = time.monotonic() - t0

    disposition = str(envelope.disposition)
    per_rule = _per_rule_from_envelope(envelope)
    confidence = float(envelope.disposition_confidence.numeric)
    return disposition, per_rule, latency_s, confidence


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
        # Skip entries whose underlying fixture is missing on disk. Manifest
        # carries forward-looking refs (e.g. fixtures/_corpus/<cola-id>/) that
        # T15 fills in; we don't want a single missing PNG to kill the run.
        if not Path(entry.image_ref).is_file():
            print(f"skip {entry.label_id}: image not found at {entry.image_ref}",
                  file=sys.stderr)
            continue
        try:
            p_disp, p_rules, latency, confidence = evaluator(entry)
        except FileNotFoundError as e:
            print(f"skip {entry.label_id}: fixture missing ({e})", file=sys.stderr)
            continue
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
        n_labels=len(pred_disp),
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
