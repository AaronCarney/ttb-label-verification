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
