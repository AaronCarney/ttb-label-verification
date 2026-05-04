"""Pure orchestrator-trigger predicate. Source: FR-300 / L1 §7 risk #2.

Exact predicate: any ValidationResult.reason_code == "BRAND.NAME.NEEDS_REVIEW".
Not heuristic. New trigger codes are added by extending the set; the test
in tests/test_triggers.py guards against silent regression.
"""
from __future__ import annotations

from typing import Iterable

from app.schemas.rejection import ValidationResult

_ORCHESTRATOR_TRIGGER_CODES: frozenset[str] = frozenset({"BRAND.NAME.NEEDS_REVIEW"})


def should_invoke_orchestrator(results: Iterable[ValidationResult]) -> bool:
    return any(vr.reason_code in _ORCHESTRATOR_TRIGGER_CODES for vr in results)
