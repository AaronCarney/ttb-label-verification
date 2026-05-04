"""Equality-style validators. Two registered names:

  equality_match    — single-value exact / case-insensitive / normalized
  enumerated_match  — lookup against `rule.parameters['allowed_values']`

Per L1 §4 exit-gate item 10, this file does not contain citation literals.
"""
from __future__ import annotations

import unicodedata

from app.rules._validators import ValidatorContext, register
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import EngineMeta, Outcome, ValidationResult
from app.schemas.rules import MatchPolicy, RuleDefinition


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip().casefold()


def _build_meta(rule: RuleDefinition, ctx: ValidatorContext, elapsed_ms: int = 0) -> EngineMeta:
    return EngineMeta(
        engine_version=ctx.engine_version,
        rule_pack=rule.rule_pack or "unknown",
        rule_pack_version=rule.rule_pack_version or "0.0.0",
        started_at_ms=ctx.started_at_ms,
        elapsed_ms=elapsed_ms,
    )


def _conf(obs: FieldObservation) -> float:
    if not obs.evidence:
        return 0.0
    return min(ev.confidence for ev in obs.evidence)


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
