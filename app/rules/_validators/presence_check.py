"""Presence-style validators.

  presence_check        — fail when observed_value is None or whitespace-only.
  conditional_presence  — same, but skip when the precondition in
                          rule.parameters['required_when'] (a key into
                          expected.parameters) is falsy.
"""
from __future__ import annotations

from app.rules._validators import ValidatorContext, register
from app.rules._validators.equality_match import _build_meta, _conf
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import Outcome, ValidationResult
from app.schemas.rules import RuleDefinition


def _is_present(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, str) and not v.strip():
        return False
    return True


def _result(rule, ctx, obs, exp, present: bool) -> ValidationResult:
    return ValidationResult(
        rule_id=rule.rule_id,
        cfr_citation=rule.cfr_citation,
        beverage_class=obs.beverage_class,
        outcome=Outcome.PASS if present else Outcome.FAIL,
        severity=rule.severity,
        reason_code=None if present else rule.reason_code,
        aggregated_confidence=_conf(obs),
        evidence=obs.evidence,
        expected=exp,
        observed=obs,
        engine_meta=_build_meta(rule, ctx),
    )


@register("presence_check")
def presence_check(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    return _result(rule, ctx, obs, exp, _is_present(obs.observed_value))


@register("conditional_presence")
def conditional_presence(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    key = rule.parameters.get("required_when")
    required = bool(exp.parameters.get(key, False)) if key else True
    if not required:
        return ValidationResult(
            rule_id=rule.rule_id,
            cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class,
            outcome=Outcome.NOT_APPLICABLE,
            severity=rule.severity,
            reason_code=None,
            aggregated_confidence=_conf(obs),
            evidence=obs.evidence,
            expected=exp,
            observed=obs,
            engine_meta=_build_meta(rule, ctx),
        )
    return _result(rule, ctx, obs, exp, _is_present(obs.observed_value))
