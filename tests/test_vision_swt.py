import asyncio
from collections import deque

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from app.vision.swt import StrokeWidthReport, SWTRunner


def _synth_text_png(stroke_thickness: int) -> bytes:
    """Generate a 100x40 PNG with text drawn at the specified stroke thickness."""
    img = Image.new("L", (100, 40), color=255)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    # Stroke parameter not directly available on default font;
    # simulate by overdrawing thickness times with offsets.
    for dx in range(stroke_thickness):
        for dy in range(stroke_thickness):
            draw.text((10 + dx, 10 + dy), "WARNING", fill=0, font=font)
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_thick_stroke_classified_bold():
    ring = deque(maxlen=200)
    runner = SWTRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    report = await runner.run(crop=_synth_text_png(stroke_thickness=3))
    assert isinstance(report, StrokeWidthReport)
    assert report.is_bold is True


@pytest.mark.asyncio
async def test_thin_stroke_classified_not_bold():
    ring = deque(maxlen=200)
    runner = SWTRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    report = await runner.run(crop=_synth_text_png(stroke_thickness=1))
    assert report.is_bold is False


@pytest.mark.asyncio
async def test_run_writes_call_record():
    ring = deque(maxlen=200)
    runner = SWTRunner(ring_buffer=ring, batch_id="B-001", label_id="L-001")
    await runner.run(crop=_synth_text_png(stroke_thickness=2))
    assert len(ring) == 1
    assert ring[0].stage == "vision.swt"
