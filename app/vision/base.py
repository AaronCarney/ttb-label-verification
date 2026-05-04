"""VisionExtractor Protocol + sub-runner shape declarations.

Source: E3 L1 §2.1. The Protocol is runtime_checkable so substitutability
tests can assert isinstance() without instantiating the heavy sub-runners.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.extracted import FieldObservation
from app.schemas.label import Label


@runtime_checkable
class VisionExtractor(Protocol):
    """D-004 #1 seam. Two concrete impls land in E3: cloud + local."""

    async def extract(self, label: Label) -> list[FieldObservation]: ...

    async def ensure_loaded(self) -> None:
        """Warm-up hook. Cloud impl: no-op. Local impl: load model weights."""
        ...
