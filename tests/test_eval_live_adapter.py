# tests/test_eval_live_adapter.py
"""Live evaluator adapter — verifies _live_evaluator returns the harness contract.

Gated by @pytest.mark.slow + OPENAI_API_KEY because this hits the real Evaluator
(vision + orchestrator). Skipped in default CI runs.
"""
from __future__ import annotations

import os

import pytest

from eval._schema import ExpectedRule, ManifestEntry, Provenance


@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY required for live evaluator",
)
def test_live_evaluator_returns_4tuple_for_fixture_01():
    from eval.harness import _live_evaluator

    entry = ManifestEntry(
        label_id="FIX-01-SPIRITS-CLEAN",
        application_ref="fixtures/01-spirits-clean/application.json",
        image_ref="fixtures/01-spirits-clean/label.png",
        expected_disposition="pass",
        expected_per_rule=[ExpectedRule(rule_id="FR-300-class-type", result="pass")],
        provenance=Provenance(source="synthetic-acme-distilling"),
        class_balance_tag="spirits",
        borderline_band=False,
    )

    result = _live_evaluator(entry)

    assert isinstance(result, tuple)
    assert len(result) == 4
    p_disp, p_rules, latency_s, confidence = result
    assert isinstance(p_disp, str)
    assert p_disp in {"pass", "fail", "needs_review"}
    assert isinstance(p_rules, list)
    assert isinstance(latency_s, float)
    assert latency_s >= 0.0
    assert isinstance(confidence, float)
    assert 0.0 <= confidence <= 1.0
