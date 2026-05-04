import json
from collections import deque
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.vision.tiebreak_gpt4o import GPT4oTiebreakRunner

RECORDING = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/tiebreak/brand_name.json")


@pytest.mark.asyncio
@respx.mock
async def test_tiebreak_run_against_recording():
    payload = json.loads(RECORDING.read_text())
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=Response(200, json=payload)
    )
    ring = deque(maxlen=200)
    runner = GPT4oTiebreakRunner(
        ring_buffer=ring,
        batch_id="B-001",
        label_id="L-001",
        api_key="sk-test",
        model_snapshot="gpt-4o-2024-08-06",
        prompt_version="v1",
    )
    result = await runner.run(crop=b"\x89PNG", prompt="brand_name")
    assert result["brand_name"] == "ACME BOURBON"
    assert len(ring) == 1
    assert ring[0].stage == "vision.gpt4o_tiebreak"
    assert ring[0].provider == "openai"
    assert ring[0].model == "gpt-4o-2024-08-06"
    assert ring[0].prompt_version == "v1"
