"""RuleEngine ABC. Single async method per ARCH §8.4."""
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
