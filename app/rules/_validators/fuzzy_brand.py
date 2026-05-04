"""fuzzy_brand validator (FR-240). Two-stage policy from ARCH §6.11:

  Stage A — normalized exact. Pass immediately if equal; record kind=normalized.
  Stage B — Jaro-Winkler fuzzy.
    score >= pass_threshold       → PASS  (kind=fuzzy, score recorded)
    needs_review_threshold <= s < pass_threshold → FAIL with severity=warn,
                                  reason_code=BRAND.NAME.NEEDS_REVIEW
                                  (the E5-consumed orchestration trigger)
    score < needs_review_threshold → FAIL with reason_code=BRAND.NAME.MISMATCH
"""
from __future__ import annotations

from app.rules._validators import ValidatorContext, register
from app.rules._validators.equality_match import _build_meta, _conf
from app.rules.brand_match import stage_a_normalized, stage_b_fuzzy
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import Outcome, Severity, ValidationResult
from app.schemas.rules import RuleDefinition


@register("fuzzy_brand")
def fuzzy_brand(
    obs: FieldObservation,
    exp: ExpectedValue,
    rule: RuleDefinition,
    ctx: ValidatorContext,
) -> ValidationResult:
    observed = "" if obs.observed_value is None else str(obs.observed_value)
    expected = "" if exp.value is None else str(exp.value)
    meta = _build_meta(rule, ctx)

    if stage_a_normalized(observed, expected):
        return ValidationResult(
            rule_id=rule.rule_id,
            cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class,
            outcome=Outcome.PASS,
            severity=rule.severity,
            reason_code=None,
            aggregated_confidence=_conf(obs),
            evidence=obs.evidence,
            expected=exp,
            observed=obs,
            engine_meta=meta,
        )

    score = stage_b_fuzzy(observed, expected)
    pass_th = float(rule.parameters.get("pass_threshold", 0.92))
    nr_th = float(rule.parameters.get("needs_review_threshold", 0.85))
    nr_code = rule.parameters.get("needs_review_reason_code", "BRAND.NAME.NEEDS_REVIEW")

    if score >= pass_th:
        return ValidationResult(
            rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class, outcome=Outcome.PASS,
            severity=rule.severity, reason_code=None,
            aggregated_confidence=_conf(obs), evidence=obs.evidence,
            expected=exp, observed=obs, engine_meta=meta,
        )
    if score >= nr_th:
        return ValidationResult(
            rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
            beverage_class=obs.beverage_class, outcome=Outcome.FAIL,
            severity=Severity.WARN, reason_code=nr_code,
            aggregated_confidence=_conf(obs), evidence=obs.evidence,
            expected=exp, observed=obs, engine_meta=meta,
        )
    return ValidationResult(
        rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
        beverage_class=obs.beverage_class, outcome=Outcome.FAIL,
        severity=rule.severity, reason_code=rule.reason_code,
        aggregated_confidence=_conf(obs), evidence=obs.evidence,
        expected=exp, observed=obs, engine_meta=meta,
    )
