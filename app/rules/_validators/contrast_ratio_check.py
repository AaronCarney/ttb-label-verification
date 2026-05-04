"""contrast_ratio_check (FR-203 Stretch). MVP-scope stub: read the contrast
ratio from observation payload; full WCAG calculation lands with E3 vision.
"""
from __future__ import annotations

from app.rules._validators import ValidatorContext, register
from app.rules._validators._helpers import _build_meta, _conf
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import Outcome, ValidationResult
from app.schemas.rules import RuleDefinition


@register("contrast_ratio_check")
def contrast_ratio_check(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    threshold = float(rule.parameters.get("min_contrast_ratio", 4.5))
    payload = obs.observed_value or {}
    ratio = payload.get("contrast_ratio")
    ok = ratio is not None and float(ratio) >= threshold
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
