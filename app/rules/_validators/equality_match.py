"""Equality-style validators. Two registered names:

  equality_match    — single-value exact / case-insensitive / normalized
  enumerated_match  — lookup against `rule.parameters['allowed_values']`

Per L1 §4 exit-gate item 10, this file does not contain citation literals.

Shared helpers (`_build_meta`, `_conf`) live in `_helpers.py` so every
validator file can import them without depending on this module's load
order. `_normalize` stays here because it is genuinely equality-internal.
"""
from __future__ import annotations

import unicodedata

from app.rules._validators import ValidatorContext, register
from app.rules._validators._helpers import _build_meta, _conf
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import Outcome, ValidationResult
from app.schemas.rules import MatchPolicy, RuleDefinition


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip().casefold()


@register("equality_match")
def equality_match(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    observed = obs.observed_value
    expected = exp.value
    matched = False
    if observed is not None and expected is not None:
        if rule.match_policy is MatchPolicy.NORMALIZED:
            matched = _normalize(str(observed)) == _normalize(str(expected))
        elif rule.match_policy is MatchPolicy.EXACT:
            matched = str(observed) == str(expected)
        else:
            matched = _normalize(str(observed)) == _normalize(str(expected))
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


@register("enumerated_match")
def enumerated_match(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    allowed: list[str] = rule.parameters.get("allowed_values", [])
    observed = obs.observed_value
    matched = (
        observed is not None
        and any(_normalize(str(observed)) == _normalize(str(v)) for v in allowed)
    )
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
