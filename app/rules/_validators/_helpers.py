"""Shared helpers for validator implementations.

These were originally co-located in `equality_match.py` and imported by every
sibling validator, which created a silent load-order coupling: every validator
file depended on `equality_match` being importable first. Moving them to a
private `_helpers` module makes the relationship explicit and matches Python
conventions for internal package utilities (underscore prefix on the module).

`equality_match.py` retains `_normalize` because it is genuinely equality-
internal (only `equality_match` and `enumerated_match` use NFKC + casefold
comparison).

T19's orphan-validator check (`test_every_validator_module_registers_at_least_one_name`)
walks `app/rules/_validators/*.py` and asserts each file registers ≥ 1 name.
That check skips any module whose name starts with `_` (including `__init__.py`
and `_helpers.py`) so private utility modules do not falsely trip the gate.
"""
from __future__ import annotations

from app.rules._validators import ValidatorContext
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import EngineMeta
from app.schemas.rules import RuleDefinition


def _build_meta(rule: RuleDefinition, ctx: ValidatorContext, elapsed_ms: int = 0) -> EngineMeta:
    """Construct EngineMeta from rule + per-evaluation context.

    `elapsed_ms` defaults to 0; the engine overrides it on every return path
    with the actual per-rule monotonic delta (yaml_engine._run_one).
    """
    return EngineMeta(
        engine_version=ctx.engine_version,
        rule_pack=rule.rule_pack or "unknown",
        rule_pack_version=rule.rule_pack_version or "0.0.0",
        started_at_ms=ctx.started_at_ms,
        elapsed_ms=elapsed_ms,
    )


def _conf(obs: FieldObservation) -> float:
    """Aggregated confidence = min over evidence items, 0.0 if no evidence."""
    if not obs.evidence:
        return 0.0
    return min(ev.confidence for ev in obs.evidence)
