import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.schemas.label import Dimensions, Label
from app.vision.quality import QualityReport, assess

FIXTURE = Path("fixtures/01-spirits-clean/label.png")


def _png_bytes(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def _label(image_bytes: bytes, dpi: int | None = 300) -> Label:
    return Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=image_bytes,
        content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=dpi),
    )


def test_clean_fixture_passes():
    report = assess(_label(FIXTURE.read_bytes()))
    assert report.disposition == "ok"
    assert report.reason_code is None


def test_low_resolution_triggers_warning():
    rng = np.random.default_rng(0)
    arr = (rng.random((64, 64)) * 5 + 125).astype(np.uint8)
    report = assess(_label(_png_bytes(arr)))
    assert report.disposition == "needs_better_photo"
    assert report.reason_code == "WARNING.LEGIBILITY.LOW_RESOLUTION"


def test_glare_triggers_warning():
    rng = np.random.default_rng(1)
    arr = (rng.random((200, 200)) * 100 + 50).astype(np.uint8)
    arr[:100, :100] = 255  # 25% overexposed (>15%)
    report = assess(_label(_png_bytes(arr)))
    assert report.disposition == "needs_better_photo"
    assert report.reason_code == "WARNING.LEGIBILITY.GLARE"
