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
