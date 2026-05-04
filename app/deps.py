"""DI container — selects VisionExtractor and Orchestrator per env."""
from __future__ import annotations

import subprocess
from collections import deque
from typing import Literal

from app.config import Settings
from app.orchestrator.base import Orchestrator
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.orchestrator.anthropic_strict import AnthropicStrictOrchestrator
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


def build_orchestrator(settings: Settings) -> Orchestrator:
    backend = settings.orchestrator_backend
    ring: deque = deque(maxlen=200)
    if backend == "openai":
        return OpenAIStrictOrchestrator(
            settings=settings, ring_buffer=ring, api_key=settings.openai_api_key or ""
        )
    if backend == "anthropic":
        return AnthropicStrictOrchestrator(
            settings=settings, ring_buffer=ring, api_key=settings.anthropic_api_key or "",
        )
    raise ValueError(f"Unknown orchestrator_backend: {backend!r}")
