"""Label envelope — what the Vision Extractor consumes (E3).

Carries image bytes, the content-type discriminator, optional dimensions
(applicant-supplied or extracted from EXIF), and the face_tag that distinguishes
front/back/neck/side panels. Source: E3 L1 §2.1.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Dimensions(BaseModel):
    """Physical dimensions of the label image. Source: E3 L1 §2.1."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width_px: int = Field(ge=1)
    height_px: int = Field(ge=1)
    dpi: int | None = Field(default=None, ge=1)


class Label(BaseModel):
    """Label envelope consumed by VisionExtractor.extract(). Source: E3 L1 §2.1."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label_id: str
    batch_id: str
    image_bytes: bytes
    content_type: Literal["image/jpeg", "image/png"]
    face_tag: Literal["front", "back", "neck", "side"]
    dimensions: Dimensions | None = None
