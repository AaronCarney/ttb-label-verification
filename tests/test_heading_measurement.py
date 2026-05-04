"""Tests for app/vision/heading_measure.py — local SWT-style bold detector."""
from io import BytesIO

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.vision.heading_measure import (
    WIDTH_HEIGHT_RATIO_BOLD_MIN,
    measure_heading_bold,
)


def _png_text(text: str, size: int, weight: str) -> bytes:
    """Render `text` at the given pixel size with either bold or regular
    weight using PIL's default bitmap font (regular) or a synthetic bold via
    cv2 morphological dilation. Returns PNG bytes for SWT input."""
    import cv2
    img = Image.new("L", (260, 80), color=255)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size)
    except TypeError:
        font = ImageFont.load_default()
    draw.text((10, 10), text, fill=0, font=font)
    arr = np.asarray(img)
    if weight == "bold":
        ink = (arr < 128).astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        ink = cv2.dilate(ink, kernel, iterations=2)
        arr = np.where(ink > 0, 0, 255).astype(np.uint8)
    out = BytesIO()
    Image.fromarray(arr, mode="L").save(out, "PNG")
    return out.getvalue()


def test_bold_text_classified_as_bold():
    """Heavy strokes -> width:height ratio above the threshold."""
    bbox = (0, 0, 260, 80)
    png = _png_text("GOVERNMENT WARNING", size=24, weight="bold")
    m = measure_heading_bold(png, bbox)
    assert m.confident
    assert m.is_bold
    assert m.width_height_ratio > WIDTH_HEIGHT_RATIO_BOLD_MIN


def test_regular_text_classified_as_not_bold():
    """Default weight strokes -> ratio below the threshold."""
    bbox = (0, 0, 260, 80)
    png = _png_text("GOVERNMENT WARNING", size=12, weight="regular")
    m = measure_heading_bold(png, bbox)
    assert m.confident
    assert not m.is_bold
    assert m.width_height_ratio <= WIDTH_HEIGHT_RATIO_BOLD_MIN


def test_zero_bbox_returns_unconfident():
    """A degenerate bbox can't be measured — caller must fall back."""
    png = _png_text("GOVERNMENT WARNING", size=24, weight="bold")
    m = measure_heading_bold(png, (0, 0, 0, 0))
    assert not m.confident


def test_none_bbox_returns_unconfident():
    png = _png_text("GOVERNMENT WARNING", size=24, weight="bold")
    m = measure_heading_bold(png, None)
    assert not m.confident


def test_tiny_crop_returns_unconfident():
    """A crop smaller than 8x8 pixels can't host enough components."""
    png = _png_text("GOVERNMENT WARNING", size=24, weight="bold")
    m = measure_heading_bold(png, (0, 0, 4, 4))
    assert not m.confident
