import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.config import Settings
from app.schemas.label import Dimensions, Label
from app.vision.cloud import CloudVisionExtractor

RECORDINGS_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/01-spirits-clean")
FIXTURE = Path("fixtures/01-spirits-clean/label.png")
EXPECTED_FIELD_IDS = {
    "brand_name", "class_type", "abv", "net_contents",
    "gov_warning", "heading_typography", "name_address", "country_origin",
}


@pytest.mark.asyncio
async def test_cloud_extracts_fr_001_to_008(monkeypatch):
    settings = Settings()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    ring = deque(maxlen=200)
    extractor = CloudVisionExtractor(settings=settings, ring_buffer=ring, api_key="sk-test")
    label = Label(
        label_id="L-001",
        batch_id="B-001",
        image_bytes=FIXTURE.read_bytes(),
        content_type="image/png",
        face_tag="front",
        dimensions=Dimensions(width_px=200, height_px=200, dpi=300),
    )
    # respx 0.23.1 deduplicates same-URL/method routes (only the last mount
    # survives), so the planned per-recording mount-with-fall-through pattern
    # collapses. Equivalent: one dispatcher handler keyed on the request body's
    # `response_format.json_schema.name` (still discriminates by recording).
    recordings = {p.stem: json.loads(p.read_text()) for p in RECORDINGS_DIR.glob("*.json")}

    with respx.mock(base_url="https://api.openai.com") as mock_router:
        def _dispatch(request):
            body = json.loads(request.content)
            name = body.get("response_format", {}).get("json_schema", {}).get("name")
            payload = recordings.get(name)
            if payload is None:
                return Response(404, json={"error": f"no recording for {name!r}"})
            return Response(200, json=payload)

        mock_router.post("/v1/chat/completions").mock(side_effect=_dispatch)

        observations = await extractor.extract(label)
    field_ids = {obs.field_id for obs in observations}
    assert field_ids == EXPECTED_FIELD_IDS
    assert len(ring) == 9  # 1 layout + 8 per-field calls
