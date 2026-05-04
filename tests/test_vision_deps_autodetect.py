import subprocess
from unittest.mock import patch

import pytest

from app.config import Settings
from app.deps import _autodetect, build_vision_extractor
from app.vision.cloud import CloudVisionExtractor
from app.vision.local import LocalVisionExtractor


def test_autodetect_cuda_present():
    with patch("app.deps.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["nvidia-smi"], returncode=0, stdout=b"GPU 0: ...", stderr=b""
        )
        mode = _autodetect()
        assert mode == "local"


def test_autodetect_cuda_absent():
    with patch("app.deps.subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["nvidia-smi"], returncode=127, stdout=b"", stderr=b"command not found"
        )
        mode = _autodetect()
        assert mode == "cloud"


def test_autodetect_subprocess_timeout_falls_back_cloud():
    with patch("app.deps.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["nvidia-smi"], timeout=2)
        mode = _autodetect()
        assert mode == "cloud"


def test_build_vision_extractor_cloud(monkeypatch):
    monkeypatch.setenv("VISION_MODE", "cloud")
    settings = Settings()
    extractor = build_vision_extractor(settings)
    assert isinstance(extractor, CloudVisionExtractor)


def test_build_vision_extractor_local(monkeypatch):
    monkeypatch.setenv("VISION_MODE", "local")
    settings = Settings()
    extractor = build_vision_extractor(settings)
    assert isinstance(extractor, LocalVisionExtractor)
