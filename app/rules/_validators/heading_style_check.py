"""heading_style_check: §16.22(a)(2) caps + bold heading enforcement."""
from __future__ import annotations

from app.rules._validators import ValidatorContext, register
from app.rules._validators._helpers import _build_meta, _conf
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import Outcome, ValidationResult
from app.schemas.rules import RuleDefinition


@register("heading_style_check")
def heading_style_check(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    payload = obs.observed_value or {}
    target = rule.parameters.get("target_phrase", "GOVERNMENT WARNING")
    required_case = rule.parameters.get("required_case", "upper")
    required_weight = rule.parameters.get("required_weight", "bold")
    text = payload.get("heading_text", "")
    styles = payload.get("heading_styles", {})
    ok = (
        text.upper() == target.upper()
        and styles.get("case") == required_case
        and styles.get("weight") == required_weight
    )
    return ValidationResult(
        rule_id=rule.rule_id,
        cfr_citation=rule.cfr_citation,
        beverage_class=obs.beverage_class,
        outcome=Outcome.PASS if ok else Outcome.FAIL,
        severity=rule.severity,
        reason_code=None if ok else rule.reason_code,
        aggregated_confidence=_conf(obs),
        evidence=obs.evidence,
        expected=exp,
        observed=obs,
        engine_meta=_build_meta(rule, ctx),
    )
