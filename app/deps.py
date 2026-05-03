"""DI container — selects ``VisionExtractor`` and ``Orchestrator`` per env.

E1 ships **placeholder** providers that satisfy the protocol shape but raise
``NotImplementedError`` on any method call that would touch the real seam.
Real implementations land at E3 (vision) and E4 (orchestrator).
"""
from __future__ import annotations

from typing import Any

from app.config import Settings


class _PlaceholderVisionExtractor:
    """Conforms to the ``VisionExtractor`` Protocol shape (extract method);
    raises on invocation. Real implementations land in E3.
    """

    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def extract(self, label: Any) -> list[Any]:
        raise NotImplementedError("seam not wired in E1 (E3)")


class _PlaceholderOpenAIOrchestrator:
    """``Orchestrator`` ABC placeholder. Real implementation lands at E4."""

    backend = "openai"

    async def refine(self, payload: Any) -> Any:
        raise NotImplementedError("seam not wired in E1 (E4)")


class _PlaceholderAnthropicOrchestrator:
    backend = "anthropic"

    async def refine(self, payload: Any) -> Any:
        raise NotImplementedError("seam not wired in E1 (E4)")


def build_vision_extractor(settings: Settings) -> _PlaceholderVisionExtractor:
    return _PlaceholderVisionExtractor(mode=settings.vision_mode)


def build_orchestrator(
    settings: Settings,
) -> _PlaceholderOpenAIOrchestrator | _PlaceholderAnthropicOrchestrator:
    if settings.orchestrator_backend == "anthropic":
        return _PlaceholderAnthropicOrchestrator()
    return _PlaceholderOpenAIOrchestrator()
