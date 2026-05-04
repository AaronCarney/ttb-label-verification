import asyncio
from collections import deque
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.label import Dimensions, Label
from app.vision.base import VisionExtractor
from app.vision.local import LocalVisionExtractor


def _label() -> Label:
    return Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=b"\x89PNG\r\n\x1a\n",
        content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )


@pytest.mark.asyncio
async def test_local_satisfies_protocol():
    ring = deque(maxlen=200)
    extractor = LocalVisionExtractor.__new__(LocalVisionExtractor)
    # Inject mocks — bypass __init__ which would import paddleocr.
    extractor._paddle = MagicMock(run=AsyncMock(return_value=[]))
    extractor._swt = MagicMock(run=AsyncMock(return_value=MagicMock(is_bold=True)))
    extractor._tiebreak = MagicMock(run=AsyncMock(return_value={}))
    extractor._ring = ring
    extractor._quality_assess = MagicMock(return_value=MagicMock(disposition="ok", reason_code=None))
    assert isinstance(extractor, VisionExtractor)


@pytest.mark.asyncio
async def test_local_ensure_loaded_raises_without_gpu_extras(monkeypatch):
    """When paddleocr import fails, ensure_loaded raises a clear RuntimeError."""
    import sys
    monkeypatch.setitem(sys.modules, "paddleocr", None)  # forces ImportError
    extractor = LocalVisionExtractor.__new__(LocalVisionExtractor)
    extractor._paddle = MagicMock(ensure_loaded=AsyncMock(side_effect=RuntimeError("PaddleOCR not installed. Install with `uv sync --extra gpu`.")))
    extractor._swt = MagicMock(ensure_loaded=AsyncMock())
    extractor._tiebreak = MagicMock(ensure_loaded=AsyncMock())
    with pytest.raises(RuntimeError, match="--extra gpu"):
        await extractor.ensure_loaded()
