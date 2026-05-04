"""Stroke-width measurement for the §16.22(a)(2) bold-heading check.

Restores a leaner version of the historical SWT runner (commit 2e0e738; deleted
in 6461496 when the local OCR profile was dropped). The measurement is
deterministic, runs on `label.image_bytes` after the cloud layout call returns
a bbox, and produces a real `is_bold` signal independent of LLM judgment. See
README §"Bold detection" for the design rationale.

Algorithm (Otsu + distance-transform + width:height ratio):

  1. Open the heading bbox crop in grayscale.
  2. Otsu's threshold → binary foreground mask of stroke pixels.
  3. Connected components: per-component bounding box gives character height.
  4. Distance transform: per foreground pixel, distance to nearest background;
     mean of positive distances * 2 ≈ mean stroke width per component.
  5. Aggregate: mean(stroke_width) / mean(char_height). Bold when ratio
     exceeds WIDTH_HEIGHT_RATIO_BOLD_MIN.

This is uncalibrated against a labeled corpus — the threshold is borrowed from
the deleted SWT module (0.30) and works on the demo fixtures. A tighter cut
would land in the same eval-corpus sweep that calibrates BRISQUE/NIQE and
brand-match thresholds (PRD §3.2 deferred).
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image


WIDTH_HEIGHT_RATIO_BOLD_MIN = 0.30
"""Stroke-width-to-character-height ratio above which the heading is bold.
Calibrated against the historical SWT module — empirical re-tune is deferred."""


@dataclass(frozen=True)
class HeadingMeasurement:
    """Measurement-grade signal for §16.22(a)(2). `confident` is False when the
    crop was empty or too small to produce a meaningful component count, in
    which case downstream code should fall back to the LLM's `heading_bold`."""

    is_bold: bool
    mean_stroke_width: float
    mean_character_height: float
    width_height_ratio: float
    confident: bool


def measure_heading_bold(
    image_bytes: bytes,
    bbox: tuple[int, int, int, int] | None,
) -> HeadingMeasurement:
    """Run the SWT-style measurement on the heading region.

    `bbox` is `(x0, y0, x1, y1)` in pixel coordinates produced by the layout
    call. A `None` or zero-area bbox returns `confident=False` so the caller
    keeps the model's self-reported value.
    """
    if bbox is None:
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    x0, y0, x1, y1 = bbox
    if x1 <= x0 or y1 <= y0:
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    try:
        full = Image.open(BytesIO(image_bytes)).convert("L")
        crop = full.crop((x0, y0, x1, y1))
    except Exception:  # noqa: BLE001 — defensive: malformed PNG / OOB bbox
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    if crop.width < 8 or crop.height < 8:
        # A crop this small cannot host enough connected components for a
        # reliable stroke-width estimate.
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    gray = np.asarray(crop)
    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

    widths: list[float] = []
    heights: list[float] = []
    for i in range(1, n_labels):  # skip background label 0
        x, y, w, h, _area = stats[i]
        comp_dist = dist[y : y + h, x : x + w]
        comp_pixels = comp_dist[comp_dist > 0]
        if comp_pixels.size == 0:
            continue
        widths.append(float(comp_pixels.mean()) * 2.0)
        heights.append(float(h))

    if not widths or not heights:
        return HeadingMeasurement(False, 0.0, 0.0, 0.0, confident=False)

    mean_w = float(np.mean(widths))
    mean_h = float(np.mean(heights))
    ratio = mean_w / mean_h if mean_h > 0 else 0.0
    return HeadingMeasurement(
        is_bold=ratio > WIDTH_HEIGHT_RATIO_BOLD_MIN,
        mean_stroke_width=mean_w,
        mean_character_height=mean_h,
        width_height_ratio=ratio,
        confident=True,
    )
