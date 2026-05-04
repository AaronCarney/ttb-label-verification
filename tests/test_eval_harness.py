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
