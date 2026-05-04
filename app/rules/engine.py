"""RuleEngine ABC. Single async method per ARCH §8.4.

Return type is `tuple[ValidationResult, ...]` — a deliberate tightening of
L1 §2.1 line 22 / ARCH §3 (which both name `list[ValidationResult]`) for
end-to-end immutability that matches §6.6's frozen RuleSet discipline.
ARCH/L1 should be reconciled to tuple at the next doc pass; do NOT relax
this signature back to a list without updating the L1/ARCH contract first.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from app.rules._validators import ValidatorContext
from app.schemas.expected import ExpectedValue
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import ValidationResult


class RuleEngine(ABC):
    @abstractmethod
    async def evaluate(
        self,
        observations: Sequence[FieldObservation],
        expected: Sequence[ExpectedValue],
        context: ValidatorContext,
    ) -> tuple[ValidationResult, ...]: ...

    @abstractmethod
    def build_validator_context(self, *, started_at_ms: int) -> ValidatorContext:
        """Construct a per-evaluation ``ValidatorContext`` for this engine.

        Each subclass sources ``assets``, ``decision_tables``, and
        ``engine_version`` from whatever it has on hand; the caller (the
        Evaluator) supplies the per-evaluation wall-clock reference. Pulling
        construction onto the abstraction means tests (FakeRuleEngine) can
        return a stub without reaching into private state.
        """
        ...
