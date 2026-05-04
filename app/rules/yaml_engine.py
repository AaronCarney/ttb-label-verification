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
import time
from typing import Sequence

from app.rules._validators import VALIDATOR_REGISTRY, ValidatorContext
from app.rules.engine import RuleEngine
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import EngineMeta, Outcome, Severity, ValidationResult
from app.schemas.rules import RuleSet


PER_RULE_TIMEOUT_S = 0.25


class YamlRuleEngine(RuleEngine):
    def __init__(self, ruleset: RuleSet) -> None:
        self._ruleset = ruleset

    async def evaluate(
        self,
        observations: Sequence[FieldObservation],
        expected: Sequence[ExpectedValue],
        context: ValidatorContext,
    ) -> tuple[ValidationResult, ...]:
        results: list[ValidationResult] = []
        exp_by_field = {e.field_id: e for e in expected}
        obs_by_field = {o.field_id: o for o in observations}
        for rule in self._ruleset.rules:
            if rule.disabled:
                continue
            applicable_obs = [
                obs for obs in observations
                if obs.beverage_class in rule.applies_to_classes
            ]
            if not applicable_obs:
                continue
            for obs in applicable_obs:
                exp = exp_by_field.get(obs.field_id) or ExpectedValue(field_id=obs.field_id)
                results.append(await self._run_one(rule, obs, exp, context))
        return tuple(sorted(results, key=lambda r: (r.rule_id, r.observed.field_id if r.observed else "")))

    async def _run_one(self, rule, obs, exp, ctx) -> ValidationResult:
        validator = VALIDATOR_REGISTRY.get(rule.validator)
        meta = EngineMeta(
            engine_version=ctx.engine_version,
            rule_pack=rule.rule_pack or "unknown",
            rule_pack_version=rule.rule_pack_version or "0.0.0",
            started_at_ms=int(time.monotonic() * 1000),
            elapsed_ms=0,
        )
        if validator is None:
            return ValidationResult(
                rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
                beverage_class=obs.beverage_class, outcome=Outcome.ERROR,
                severity=Severity.REJECT, reason_code="ENGINE.VALIDATOR.EXCEPTION",
                aggregated_confidence=0.0, evidence=obs.evidence,
                expected=exp, observed=obs, engine_meta=meta,
            )
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(validator, obs, exp, rule, ctx),
                timeout=PER_RULE_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            return ValidationResult(
                rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
                beverage_class=obs.beverage_class, outcome=Outcome.TIMEOUT,
                severity=Severity.WARN, reason_code="ENGINE.VALIDATOR.TIMEOUT",
                aggregated_confidence=0.0, evidence=obs.evidence,
                expected=exp, observed=obs, engine_meta=meta,
            )
        except Exception:
            return ValidationResult(
                rule_id=rule.rule_id, cfr_citation=rule.cfr_citation,
                beverage_class=obs.beverage_class, outcome=Outcome.ERROR,
                severity=Severity.REJECT, reason_code="ENGINE.VALIDATOR.EXCEPTION",
                aggregated_confidence=0.0, evidence=obs.evidence,
                expected=exp, observed=obs, engine_meta=meta,
            )
