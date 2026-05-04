"""Stroke-Width-Transform bold-detector sub-runner. Source: E3 L1 §2.3, FR-202.

Decodes a crop, thresholds via Otsu, computes per-component stroke width via
distance-transform, and aggregates a width:height ratio used as a bold signal.
"""
from __future__ import annotations

import hashlib
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO

import cv2
import numpy as np
from PIL import Image

WIDTH_HEIGHT_RATIO_BOLD_MIN = 0.30


@dataclass(frozen=True)
class StrokeWidthReport:
    is_bold: bool
    mean_stroke_width: float
    mean_character_height: float
    width_height_ratio: float


class SWTRunner:
    def __init__(self, ring_buffer: deque, batch_id: str, label_id: str) -> None:
        self._ring = ring_buffer
        self._batch_id = batch_id
        self._label_id = label_id

    async def run(self, crop: bytes) -> StrokeWidthReport:
        from app.schemas.calls import CallRecord  # local import keeps file slim

        t0 = time.monotonic()
        gray = np.asarray(Image.open(BytesIO(crop)).convert("L"))
        _, binary = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        n_labels, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)

        widths: list[float] = []
        heights: list[float] = []
        for i in range(1, n_labels):  # skip background (0)
            x, y, w, h, _area = stats[i]
            comp_dist = dist[y : y + h, x : x + w]
            comp_pixels = comp_dist[comp_dist > 0]
            if comp_pixels.size == 0:
                continue
            widths.append(float(comp_pixels.mean()) * 2.0)
            heights.append(float(h))

        if widths and heights:
            mean_stroke_width = float(np.mean(widths))
            mean_character_height = float(np.mean(heights))
            ratio = mean_stroke_width / mean_character_height
        else:
            mean_stroke_width = 0.0
            mean_character_height = 0.0
            ratio = 0.0

        report = StrokeWidthReport(
            is_bold=ratio > WIDTH_HEIGHT_RATIO_BOLD_MIN,
            mean_stroke_width=mean_stroke_width,
            mean_character_height=mean_character_height,
            width_height_ratio=ratio,
        )

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        self._ring.append(
            CallRecord(
                ts=datetime.now(timezone.utc),
                batch_id=self._batch_id,
                label_id=self._label_id,
                stage="vision.swt",
                request={"crop_size": len(crop)},
                response=asdict(report),
                latency_ms=elapsed_ms,
                provider="local.paddleocr",
                output_hash=hashlib.sha256(repr(report).encode()).hexdigest()[:16],
            )
        )
        return report
