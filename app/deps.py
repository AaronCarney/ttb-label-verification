"""DI container — selects VisionExtractor and Orchestrator per env."""
from __future__ import annotations

import subprocess
from collections import deque
from typing import Any, Literal

from app.config import Settings
from app.vision.base import VisionExtractor
from app.vision.cloud import CloudVisionExtractor
from app.vision.local import LocalVisionExtractor


_NVIDIA_SMI_TIMEOUT_S = 2.0


def _autodetect() -> Literal["cloud", "local"]:
    """Per D-015: probe nvidia-smi; CUDA-present ⇒ local, otherwise cloud."""
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            check=False,
            capture_output=True,
            timeout=_NVIDIA_SMI_TIMEOUT_S,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "cloud"
    return "local" if result.returncode == 0 else "cloud"


def build_vision_extractor(settings: Settings) -> VisionExtractor:
    mode = settings.vision_mode
    if mode == "auto":
        mode = _autodetect()
    ring: deque = deque(maxlen=200)
    if mode == "cloud":
        return CloudVisionExtractor(
            settings=settings,
            ring_buffer=ring,
            api_key=settings.openai_api_key or "",
        )
    if mode == "local":
        return LocalVisionExtractor(settings=settings, ring_buffer=ring)
    raise ValueError(f"Unknown vision_mode: {mode!r}")


# Orchestrator placeholders preserved — E4 territory.
class _PlaceholderOpenAIOrchestrator:
    """``Orchestrator`` ABC placeholder. Real implementation lands at E4."""

    backend = "openai"

    async def refine(self, payload: Any) -> Any:
        raise NotImplementedError("seam not wired in E1 (E4)")


class _PlaceholderAnthropicOrchestrator:
    backend = "anthropic"

    async def refine(self, payload: Any) -> Any:
        raise NotImplementedError("seam not wired in E1 (E4)")


def build_orchestrator(
    settings: Settings,
) -> _PlaceholderOpenAIOrchestrator | _PlaceholderAnthropicOrchestrator:
    if settings.orchestrator_backend == "anthropic":
        return _PlaceholderAnthropicOrchestrator()
    return _PlaceholderOpenAIOrchestrator()
