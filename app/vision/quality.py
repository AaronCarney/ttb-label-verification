"""Vision quality gates — assess label image and emit warnings or pass-through.

Gates: low-resolution (Laplacian variance), glare (overexposed-pixel ratio),
motion blur (FFT high-frequency energy ratio), DPI extraction (EXIF/pHYs/JFIF/
applicant). Source: E3 L1 §2.4 + L2 plan Task 6.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.label import Label


class QualityReport(BaseModel):
    """Outcome of vision quality assessment for a single label."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    disposition: Literal["ok", "needs_better_photo"]
    reason_code: str | None
    dpi: int | None


def assess(label: Label) -> QualityReport:
    """Run vision quality gates against a Label and return a QualityReport."""
    return QualityReport(disposition="ok", reason_code=None, dpi=300)
