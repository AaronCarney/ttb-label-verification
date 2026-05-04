import asyncio
from collections import deque
from unittest.mock import MagicMock

import pytest

from app.vision.paddle_runner import Candidate, PaddleRunner


@pytest.mark.asyncio
async def test_run_records_call(monkeypatch):
    ring = deque(maxlen=200)
    runner = PaddleRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    fake_ocr = MagicMock(return_value=[{"text": "ACME", "bbox": [0, 0, 10, 10], "score": 0.95}])
    monkeypatch.setattr(runner, "_ocr", fake_ocr)
    result = await runner.run(crop=b"\x89PNG\r\n\x1a\n")
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], Candidate)
    assert result[0].text == "ACME"
    assert len(ring) == 1
    assert ring[0].stage == "vision.paddleocr"
    assert ring[0].provider == "local.paddleocr"


def test_lazy_paddleocr_import():
    """PaddleRunner must NOT import paddleocr at module top-level.

    Runs the import in a fresh interpreter so it tests the actual contract
    (a clean process importing paddle_runner does not pull paddleocr) and
    has zero side effects on the parent test session — importlib.reload
    in-process mutates module class attributes, stranding sibling tests'
    top-level imports of ``Candidate`` / ``PaddleRunner`` and breaking
    isinstance checks under random test ordering (pytest-randomly).
    """
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import app.vision.paddle_runner; "
            "assert 'paddleocr' not in sys.modules, 'paddleocr imported as side effect'; "
            "print('ok')",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert result.stdout.strip() == "ok"
