"""regex_match validator: tests observed string against rule.parameters['pattern']."""
from __future__ import annotations

import re

from app.rules._validators import ValidatorContext, register
from app.rules._validators.equality_match import _build_meta, _conf
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import Outcome, ValidationResult
from app.schemas.rules import RuleDefinition


@register("regex_match")
def regex_match(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    pattern: str = rule.parameters.get("pattern", "")
    flags = re.IGNORECASE if rule.parameters.get("ignore_case", False) else 0
    text = "" if obs.observed_value is None else str(obs.observed_value)
    matched = bool(pattern) and re.match(pattern, text, flags) is not None
    return ValidationResult(
        rule_id=rule.rule_id,
        cfr_citation=rule.cfr_citation,
        beverage_class=obs.beverage_class,
        outcome=Outcome.PASS if matched else Outcome.FAIL,
        severity=rule.severity,
        reason_code=None if matched else rule.reason_code,
        aggregated_confidence=_conf(obs),
        evidence=obs.evidence,
        expected=exp,
        observed=obs,
        engine_meta=_build_meta(rule, ctx),
    )
