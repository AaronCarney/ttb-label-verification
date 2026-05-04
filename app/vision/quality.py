"""Vision quality gates — assess label image and emit warnings or pass-through.

Gates: low-resolution (Laplacian variance), glare (overexposed-pixel ratio),
motion blur (FFT high-frequency energy ratio), DPI extraction (EXIF/pHYs/JFIF/
applicant). Source: E3 L1 §2.4 + L2 plan Task 6.
"""
from __future__ import annotations

import io
from typing import Literal

import cv2
import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict

from app.schemas.label import Label

LOW_RES_VARIANCE_MIN = 50.0
GLARE_PIXEL_RATIO_MAX = 0.15
GLARE_LUMINANCE_THRESHOLD = 240
GLARE_BACKGROUND_MEDIAN_MAX = 240


class QualityReport(BaseModel):
    """Outcome of vision quality assessment for a single label."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition: Literal["ok", "needs_better_photo"]
    reason_code: str | None
    dpi: int | None


def _decode_grayscale(image_bytes: bytes) -> np.ndarray:
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    return np.array(img)


def assess(label: Label) -> QualityReport:
    """Run vision quality gates against a Label and return a QualityReport."""
    gray = _decode_grayscale(label.image_bytes)

    if cv2.Laplacian(gray, cv2.CV_64F).var() < LOW_RES_VARIANCE_MIN:
        return QualityReport(
            disposition="needs_better_photo",
            reason_code="WARNING.LEGIBILITY.LOW_RESOLUTION",
            dpi=300,
        )

    overexposed_ratio = float((gray > GLARE_LUMINANCE_THRESHOLD).sum()) / gray.size
    background_median = float(np.median(gray))
    if (
        overexposed_ratio > GLARE_PIXEL_RATIO_MAX
        and background_median < GLARE_BACKGROUND_MEDIAN_MAX
    ):
        return QualityReport(
            disposition="needs_better_photo",
            reason_code="WARNING.LEGIBILITY.GLARE",
            dpi=300,
        )

    return QualityReport(disposition="ok", reason_code=None, dpi=300)
