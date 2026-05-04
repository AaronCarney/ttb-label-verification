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


_session_cache_singleton: "SessionCache | None" = None


def _get_session_cache() -> "SessionCache":
    """Process-wide singleton so NFR-DET-001 cache survives across requests.
    Fresh-per-request would defeat the cache: identical (app, image) inputs
    must hit the same SessionCache instance to be deduplicated."""
    global _session_cache_singleton
    if _session_cache_singleton is None:
        from app.services.cache import SessionCache
        _session_cache_singleton = SessionCache(maxsize=128)
    return _session_cache_singleton


def reset_session_cache() -> None:
    """Test-only: drop the singleton so a fresh cache is constructed on next
    build_evaluator call. Use in tests that need cache-empty preconditions."""
    global _session_cache_singleton
    _session_cache_singleton = None


def build_evaluator(settings: "Settings") -> "Evaluator":
    """Construct an Evaluator wired to all four real dependencies."""
    from app.rules import build_rule_engine
    from app.services.evaluator import Evaluator
    vision = build_vision_extractor(settings)
    rules = build_rule_engine(settings)
    orchestrator = build_orchestrator(settings)
    cache = _get_session_cache()
    return Evaluator(vision=vision, rules=rules, orchestrator=orchestrator, settings=settings, cache=cache)
