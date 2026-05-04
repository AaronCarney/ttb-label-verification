"""YamlRuleEngine — the only concrete implementation in MVP. Per L1 §2.1
the per-rule timeout is 250 ms (FR-908) and validator exceptions are caught
into FR-907 results so other rules continue.

**Timeout semantics — DECISION DEADLINE, NOT EXECUTION STOP.**
``asyncio.wait_for`` cancels the awaited coroutine, but ``asyncio.to_thread``
runs synchronous code in a thread that cannot be cancelled by the event
loop. A runaway sync validator continues to consume CPU and a thread slot
in the default executor until it returns on its own. The 250 ms budget is
therefore a contract on **the result the engine returns to the caller**
(after which a TIMEOUT result is emitted and rule evaluation continues),
not a hard stop on the validator's CPU time. Implications:

  - Validators MUST be CPU-bounded by construction (every loop must have a
    finite bound; no unbounded retries; no subprocess.call without a
    timeout). The validator-registry test (T19) does not enforce this; it
    is a per-validator code-review responsibility.
  - Under load, an unbounded number of stuck threads can accumulate in the
    asyncio default executor. E5's request-cancellation path (FR-907 callsite)
    SHOULD bound the executor and surface saturation as a circuit-breaker
    state. Forward note: ARCH §8.4 should be updated to mark the timeout
    as 'decision deadline' and to call out the executor-bounding requirement
    on the E5 wiring task.
  - True hard-stop semantics would require ``concurrent.futures.ProcessPoolExecutor``
    or signal-based interruption. Both add deployment complexity beyond MVP
    scope (D-014 names YAML rule data; nothing here mandates CPU isolation).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Sequence

from app.rules._validators import VALIDATOR_REGISTRY, ValidatorContext
from app.rules.engine import RuleEngine
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.schemas.rules import RuleSet


PER_RULE_TIMEOUT_S = 0.25

# The YAML rule pack uses semantic field names (`brand`, `alc_text`,
# `warning_block`, …) while the cloud extractor emits physical field_ids
# (`brand_name`, `abv`, `gov_warning`, …). This map bridges the two so a rule
# whose `evidence_required: [warning_block]` actually finds the gov_warning
# observation. Bidirectional — keys match observation field_ids, values are
# the alias names the rule pack may use.
_FIELD_ID_RULE_ALIASES: dict[str, tuple[str, ...]] = {
    "brand_name": ("brand",),
    "abv": ("alc_text", "alcohol_content"),
    "gov_warning": ("warning_block",),
    "name_address": ("bottler", "name_and_address"),
    "country_origin": ("country_of_origin",),
}


def _matches_evidence_required(obs_field_id: str, required: tuple[str, ...]) -> bool:
    """`obs.field_id` directly OR any of its rule-pack aliases satisfies the
    rule's `evidence_required`."""
    if obs_field_id in required:
        return True
    aliases = _FIELD_ID_RULE_ALIASES.get(obs_field_id, ())
    return any(a in required for a in aliases)


_log = logging.getLogger(__name__)


class YamlRuleEngine(RuleEngine):
    def __init__(self, ruleset: RuleSet) -> None:
        self._ruleset = ruleset

    def build_validator_context(self, *, started_at_ms: int) -> ValidatorContext:
        rs = self._ruleset
        return ValidatorContext(
            assets=rs.assets,
            decision_tables=rs.decision_tables,
            started_at_ms=started_at_ms,
            engine_version=rs.version,
        )

    async def evaluate(
        self,
        observations: Sequence[FieldObservation],
        expected: Sequence[ExpectedValue],
        context: ValidatorContext,
    ) -> tuple[ValidationResult, ...]:
        results: list[ValidationResult] = []
        exp_by_field = {e.field_id: e for e in expected}
        for rule in self._ruleset.rules:
            if rule.disabled:
                continue
            applicable_obs = [
                obs for obs in observations
                if obs.beverage_class in rule.applies_to_classes
                and (
                    not rule.evidence_required
                    or _matches_evidence_required(obs.field_id, rule.evidence_required)
                )
            ]
            if not applicable_obs:
                continue
            for obs in applicable_obs:
                exp = exp_by_field.get(obs.field_id) or ExpectedValue(field_id=obs.field_id)
                results.append(await self._run_one(rule, obs, exp, context))
        return tuple(sorted(results, key=lambda r: (r.rule_id, r.observed.field_id if r.observed else "")))

    async def _run_one(self, rule, obs, exp, ctx) -> ValidationResult:
        validator = VALIDATOR_REGISTRY.get(rule.validator)
        started_at_ms = int(time.monotonic() * 1000)
        t0 = time.monotonic()

        def _meta(elapsed_ms: int) -> EngineMeta:
            return EngineMeta(
                engine_version=ctx.engine_version,
                rule_pack=rule.rule_pack or "unknown",
                rule_pack_version=rule.rule_pack_version or "0.0.0",
                started_at_ms=started_at_ms,
                elapsed_ms=elapsed_ms,
            )

        if validator is None:
            return ValidationResult(
                rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
                beverage_class=obs.beverage_class, outcome=Outcome.ERROR,
                severity=Severity.REJECT, reason_code="ENGINE.VALIDATOR.NOT_FOUND",
                aggregated_confidence=0.0, evidence=obs.evidence,
                expected=exp, observed=obs, engine_meta=_meta(0),
            )
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(validator, obs, exp, rule, ctx),
                timeout=PER_RULE_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            return ValidationResult(
                rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
                beverage_class=obs.beverage_class, outcome=Outcome.TIMEOUT,
                severity=Severity.WARN, reason_code="ENGINE.VALIDATOR.TIMEOUT",
                aggregated_confidence=0.0, evidence=obs.evidence,
                expected=exp, observed=obs, engine_meta=_meta(elapsed_ms),
            )
        except Exception:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            _log.exception("validator %r raised", rule.rule_id)
            return ValidationResult(
                rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
                beverage_class=obs.beverage_class, outcome=Outcome.ERROR,
                severity=Severity.REJECT, reason_code="ENGINE.VALIDATOR.EXCEPTION",
                aggregated_confidence=0.0, evidence=obs.evidence,
                expected=exp, observed=obs, engine_meta=_meta(elapsed_ms),
            )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        return result.model_copy(update={"engine_meta": _meta(elapsed_ms)})
