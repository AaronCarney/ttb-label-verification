"""PaddleOCR sub-runner. Source: E3 L1 §2.3.

Lazy-imports paddleocr inside ensure_loaded() so the cloud-only profile
doesn't pay the import cost (and keeps app/vision/paddle_runner.py importable
even when paddleocr is missing).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import time
from typing import Any


@dataclass(frozen=True)
class Candidate:
    text: str
    bbox: tuple[int, int, int, int]
    score: float


class PaddleRunner:
    def __init__(self, ring_buffer: deque, batch_id: str, label_id: str) -> None:
        self._ring = ring_buffer
        self._batch_id = batch_id
        self._label_id = label_id
        self._ocr_engine: Any = None  # populated by ensure_loaded()

    async def ensure_loaded(self) -> None:
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR  # lazy import
            except ImportError as e:
                raise RuntimeError(
                    "PaddleOCR not installed. Install with `uv sync --extra gpu`."
                ) from e
            self._ocr_engine = PaddleOCR(use_textline_orientation=False, lang="en")

    def _ocr(self, crop: bytes) -> list[dict]:
        # Real impl shells out to self._ocr_engine.ocr(); test patches this method.
        raise NotImplementedError

    async def run(self, crop: bytes) -> list[Candidate]:
        from app.schemas.calls import CallRecord  # local import to keep this file slim

        t0 = time.monotonic()
        raw = self._ocr(crop)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        candidates = [
            Candidate(text=r["text"], bbox=tuple(r["bbox"]), score=float(r["score"]))
            for r in raw
        ]
        self._ring.append(
            CallRecord(
                ts=datetime.now(timezone.utc),
                batch_id=self._batch_id,
                label_id=self._label_id,
                stage="vision.paddleocr",
                request={"crop_size": len(crop)},
                response={"n_candidates": len(candidates)},
                latency_ms=elapsed_ms,
                provider="local.paddleocr",
                output_hash=hashlib.sha256(repr(candidates).encode()).hexdigest()[:16],
            )
        )
        return candidates
