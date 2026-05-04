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
