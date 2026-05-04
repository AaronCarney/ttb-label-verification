"""L1 §10.3 honest-failure-mode invariant."""
import pytest

from app.schemas.expected import BeverageClass
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.disposition import compute_disposition


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


def _vr(outcome):
    return ValidationResult(rule_id="R", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                            outcome=outcome, severity=Severity.INFO, aggregated_confidence=0.9, engine_meta=_em())


@pytest.mark.parametrize("outcomes, expected", [
    ((Outcome.PASS, Outcome.PASS), "pass"),
    ((Outcome.PASS, Outcome.NOT_APPLICABLE), "pass"),
    ((Outcome.PASS, Outcome.FAIL), "fail"),
    ((Outcome.FAIL, Outcome.NOT_APPLICABLE), "fail"),
    ((Outcome.PASS, Outcome.INSUFFICIENT_EVIDENCE), "needs_review"),
    ((Outcome.PASS, Outcome.TIMEOUT), "needs_review"),
    ((Outcome.PASS, Outcome.ERROR), "needs_review"),
    ((Outcome.FAIL, Outcome.TIMEOUT), "fail"),  # fail wins
])
def test_disposition_rule(outcomes, expected):
    assert compute_disposition(tuple(_vr(o) for o in outcomes)) == expected


def test_empty_results_route_to_needs_review():
    assert compute_disposition(()) == "needs_review"
