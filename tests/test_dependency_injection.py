"""DI container: VisionExtractor / Orchestrator placeholder providers.

Per L1 §4 AC #8: providers raise NotImplementedError("seam not wired in E1")
on any path that would invoke ``VisionExtractor.extract()`` or
``Orchestrator.refine()``.
"""
from __future__ import annotations

import os

import pytest


def _settings_with(**overrides: str | None):
    from app.config import Settings

    original = {k: os.environ.get(k) for k in overrides}
    try:
        for k, v in overrides.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        return Settings()
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_vision_extractor_provider_returns_object_when_called() -> None:
    from app.deps import build_vision_extractor

    s = _settings_with(OPENAI_API_KEY="sk", VISION_MODE="cloud")
    extractor = build_vision_extractor(s)
    assert extractor is not None


def test_vision_extractor_provider_dispatches_on_mode() -> None:
    """E3 D-015: build_vision_extractor returns a real extractor selected by mode."""
    from app.deps import build_vision_extractor
    from app.vision.cloud import CloudVisionExtractor
    from app.vision.local import LocalVisionExtractor

    s_cloud = _settings_with(OPENAI_API_KEY="sk", VISION_MODE="cloud")
    s_local = _settings_with(OPENAI_API_KEY="sk", VISION_MODE="local")
    assert isinstance(build_vision_extractor(s_cloud), CloudVisionExtractor)
    assert isinstance(build_vision_extractor(s_local), LocalVisionExtractor)


def test_orchestrator_provider_dispatches_on_backend() -> None:
    from app.deps import build_orchestrator

    s_o = _settings_with(OPENAI_API_KEY="sk", ORCHESTRATOR_BACKEND="openai")
    s_a = _settings_with(ANTHROPIC_API_KEY="sk", ORCHESTRATOR_BACKEND="anthropic")
    o_open = build_orchestrator(s_o)
    o_anth = build_orchestrator(s_a)
    assert type(o_open).__name__ != type(o_anth).__name__
