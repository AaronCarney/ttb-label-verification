"""Shared pytest fixtures for the TTB Label Verification test suite."""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from app.schemas.label import Label


@pytest.fixture
def wire_fixtures_dir() -> Path:
    return Path(__file__).parent / "wire_fixtures"


@pytest.fixture
def synthetic_jpeg_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _redact_authorization_headers(payload: dict) -> dict:
    """Strip Authorization headers from a recording payload before write.
    Per L1 §7 risk: prevents leaked API keys in committed recordings."""
    import copy
    out = copy.deepcopy(payload)
    headers = out.get("headers")
    if isinstance(headers, dict):
        for key in list(headers.keys()):
            if key.lower() == "authorization" or key.lower() == "x-api-key":
                headers[key] = "REDACTED"
    return out


def _stub_label(
    *,
    label_id: str = "lbl-test",
    batch_id: str = "B-test",
    image_bytes: bytes = b"\x89PNG\r\n\x1a\n",
    content_type: str = "image/png",
    face_tag: str = "front",
    dimensions=None,
) -> Label:
    return Label(
        label_id=label_id,
        batch_id=batch_id,
        image_bytes=image_bytes,
        content_type=content_type,
        face_tag=face_tag,
        dimensions=dimensions,
    )
