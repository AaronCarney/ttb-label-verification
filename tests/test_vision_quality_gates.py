from pathlib import Path

import pytest

from app.schemas.label import Dimensions, Label
from app.vision.quality import QualityReport, assess

FIXTURE = Path("fixtures/01-spirits-clean/label.png")


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
