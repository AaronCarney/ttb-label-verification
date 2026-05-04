"""Full FR-900 series Evaluator-layer coverage."""
import asyncio

import pytest

from app.config import Settings
from app.schemas.application import Application
from app.schemas.expected import BeverageClass
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.services.evaluator import Evaluator
from app.vision.quality import QualityReport
from tests._fakes.orchestrator import FakeOrchestrator
from tests._fakes.rules import FakeRuleEngine
from tests._fakes.vision import FakeVisionExtractor
from tests.conftest import _stub_label  # Conventions §_stub_label()


@pytest.fixture(autouse=True)
def _bypass_legibility(monkeypatch):
    """Bypass quality gate so rule routing under test isn't masked by FR-505/603 short-circuit."""
    monkeypatch.setattr(
        "app.services.evaluator.assess_quality",
        lambda lbl: QualityReport(disposition="ok", reason_code=None, dpi=300),
    )


def _em():
    return EngineMeta(engine_version="t", rule_pack_version="t", rule_pack="t", started_at_ms=0, elapsed_ms=0)


def _stub_app():
    return Application(application_id="A-001", evaluation_id="EV-001")


@pytest.mark.asyncio
async def test_fr902_conflicting_rules():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="R-A", cfr_citation="27 CFR §1", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.PASS, severity=Severity.INFO, aggregated_confidence=0.95, engine_meta=_em()),
        ValidationResult(rule_id="R-B", cfr_citation="27 CFR §2", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.FAIL, severity=Severity.REJECT, reason_code="X.CONFLICT.DETECTED",
                         aggregated_confidence=0.95, engine_meta=_em()),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "fail"


@pytest.mark.asyncio
@pytest.mark.parametrize("reason_code, outcome, fr_label", [
    ("ENGINE.OBSERVATION.AMBIGUOUS",                  Outcome.INSUFFICIENT_EVIDENCE, "FR-903"),
    ("CLASS_TYPE.INPUT.UNKNOWN",                      Outcome.INSUFFICIENT_EVIDENCE, "FR-904"),
    ("CLASS_TYPE.MATCH.APPLICATION_LABEL_DISAGREE",   Outcome.INSUFFICIENT_EVIDENCE, "FR-905"),
    ("ENGINE.MEASUREMENT.MISSING_DPI",                Outcome.INSUFFICIENT_EVIDENCE, "FR-910"),
])
async def test_fr_900_series_routes_to_needs_review(reason_code, outcome, fr_label):
    """FR-903 / FR-904 / FR-905 / FR-910: YAML-registry reason codes route to needs_review."""
    rules = FakeRuleEngine(results=(
        ValidationResult(
            rule_id=f"R-{fr_label}", cfr_citation="27 CFR §x",
            beverage_class=BeverageClass.SPIRITS,
            outcome=outcome, severity=Severity.WARN,
            reason_code=reason_code,
            aggregated_confidence=0.4, engine_meta=_em(),
        ),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules,
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review", f"{fr_label} did not route to needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert reason_code in rule_ids, (
        f"{fr_label}: YAML-registry reason_code {reason_code} not surfaced in "
        f"per_rule_trace ({rule_ids}) — production path emits this string verbatim"
    )


@pytest.mark.asyncio
async def test_fr907_validator_exception():
    class FailingRules(FakeRuleEngine):
        async def evaluate(self, *a, **kw):
            raise RuntimeError("validator boom")

    e = Evaluator(vision=FakeVisionExtractor(observations=[]),
                  rules=FailingRules(results=()),
                  orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"


@pytest.mark.asyncio
async def test_fr908_per_rule_timeout_outcome_routes_to_needs_review():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="R-slow", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.TIMEOUT, severity=Severity.INFO,
                         reason_code="ENGINE.SLA.RULE_TIMEOUT",
                         aggregated_confidence=0.0, engine_meta=_em()),
        ValidationResult(rule_id="R-ok", cfr_citation="27 CFR §y", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.PASS, severity=Severity.INFO,
                         aggregated_confidence=0.95, engine_meta=_em()),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"


@pytest.mark.asyncio
async def test_fr909_whole_eval_timeout():
    class SlowRules(FakeRuleEngine):
        async def evaluate(self, *a, **kw):
            await asyncio.sleep(10)
            return ()

    e = Evaluator(vision=FakeVisionExtractor(observations=[]),
                  rules=SlowRules(results=()),
                  orchestrator=FakeOrchestrator(), settings=Settings())
    e._sla_seconds = 0.1
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert "ENGINE.SLA.TIMEOUT" in rule_ids


@pytest.mark.asyncio
async def test_fr911_reference_data_unavailable():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="R-cpi", cfr_citation="27 CFR §x", beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.ERROR, severity=Severity.INFO,
                         reason_code="ENGINE.REFERENCE_DATA.UNAVAILABLE",
                         aggregated_confidence=0.0, engine_meta=_em()),
    ))
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=FakeOrchestrator(), settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"


@pytest.mark.asyncio
async def test_fr912_model_unavailable():
    rules = FakeRuleEngine(results=(
        ValidationResult(rule_id="X.brand.present", cfr_citation="27 CFR §5.42",
                         beverage_class=BeverageClass.SPIRITS,
                         outcome=Outcome.INSUFFICIENT_EVIDENCE, severity=Severity.WARN,
                         reason_code="BRAND.NAME.NEEDS_REVIEW",
                         aggregated_confidence=0.6, engine_meta=_em()),
    ))
    orch = FakeOrchestrator(refined_outputs=[], raise_on_call=1)
    e = Evaluator(vision=FakeVisionExtractor(observations=[]), rules=rules, orchestrator=orch, settings=Settings())
    envelope = await e.evaluate(application=_stub_app(), label=_stub_label())
    assert envelope.disposition == "needs_review"
    rule_ids = {entry.rule_id for entry in envelope.audit_trail.per_rule_trace}
    assert any("ENGINE.MODEL" in c for c in rule_ids)
