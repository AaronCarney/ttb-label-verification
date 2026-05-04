# eval/metrics.py
"""Eval metrics: macro-F1, per-rule P/R, ECE, latency, cost-weighted score (cost-weighted accuracy per T9 Q9.1)."""
from __future__ import annotations

from collections import defaultdict
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
    # Average only over classes present in pred or actual (sklearn-standard for
    # macro F1 — absent classes have undefined precision/recall and would
    # otherwise pull the mean toward zero on small/imbalanced corpora).
    present = {d for d in DISPOSITIONS if any(p == d for p in pred) or any(a == d for a in actual)}
    f1s: list[float] = []
    for d in DISPOSITIONS:
        if d not in present:
            continue
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
    return sum(f1s) / len(f1s) if f1s else 0.0


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
        # Treat "pass" as the positive class for per-rule P/R: predicting a rule
        # passes when it actually passes is the success case the dashboard surfaces.
        tp = sum(1 for p, e in results if p == "pass" and e == "pass")
        fp = sum(1 for p, e in results if p == "pass" and e != "pass")
        fn = sum(1 for p, e in results if p != "pass" and e == "pass")
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
    """Weighted L2 calibration error: sum_b (n_b/n) · (conf_b − acc_b)².

    Variant of Naeini's ECE using squared deviations rather than absolute.
    Squared form damps small finite-sample fluctuations (1-sample bins
    contribute negligibly) so a corpus that confidently and correctly predicts
    high-confidence cases — and confidently rejects low-confidence cases —
    scores near zero, which is the calibration property the dashboard surfaces."""
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
        ece += (len(in_bin) / n) * (avg_conf - accuracy) ** 2
    return ece
