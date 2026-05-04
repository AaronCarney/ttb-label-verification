import json
from collections import deque
from pathlib import Path

import httpx  # used by Cycle B's httpx.ConnectError + Cycle C's malformed-payload paths
import pytest
import respx
from httpx import Response

from app.config import Settings
from app.orchestrator.openai_strict import OpenAIStrictOrchestrator
from app.schemas.application import Application
from app.schemas.extracted import FieldObservation
from app.schemas.rejection import ValidationResult


REC_DIR = Path("tests/recordings/openai/gpt-4o-2024-08-06/v1/orchestrator")


def _mount_recordings(router, fixture_id: str) -> None:
    """Single handler dispatches by json_schema.name to the right recording."""
    recordings: dict[str, dict] = {}
    for task in ("brand_disambig", "reasoning_enrich", "ocr_reconcile"):
        path = REC_DIR / task / f"{fixture_id}.json"
        recordings[task] = json.loads(path.read_text())

    def _handler(request):
        body = json.loads(request.content)
        name = body.get("response_format", {}).get("json_schema", {}).get("name")
        if name in recordings:
            return Response(200, json=recordings[name])
        return Response(400, json={"error": f"unknown task {name}"})

    router.post("/v1/chat/completions").mock(side_effect=_handler)


def _stub_inputs():
    """Minimal stub Application/observations/validation_results for the test."""
    app_ = Application(application_id="A-001", evaluation_id="EV-001")
    obs: list[FieldObservation] = []
    vr: list[ValidationResult] = []
    return app_, obs, vr


@pytest.mark.asyncio
async def test_refine_against_fixture_01():
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    app_, obs, vr = _stub_inputs()
    with respx.mock(base_url="https://api.openai.com") as router:
        _mount_recordings(router, "01-spirits-clean")
        refined = await orch.refine(app_, obs, vr)
    task_names = {t.task for t in refined.tasks}
    assert task_names == {"brand_disambig", "reasoning_enrich", "ocr_reconcile"}
    assert len(ring) == 3
    assert all(r.provider == "openai" for r in ring)
    assert all(r.stage.startswith("orch.") for r in ring)


# Cycle B: FR-304 fallback tests
@pytest.mark.asyncio
async def test_refine_fr304_fallback_on_connect_error():
    """Transport-level failure (httpx.RequestError subclass) → ENGINE.MODEL.UNAVAILABLE."""
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    app_, obs, vr = _stub_inputs()
    with respx.mock(base_url="https://api.openai.com") as router:
        router.post("/v1/chat/completions").mock(side_effect=httpx.ConnectError("boom"))
        refined = await orch.refine(app_, obs, vr)
    qualifiers = {t.qualifier for t in refined.tasks}
    assert qualifiers == {"ENGINE.MODEL.UNAVAILABLE"}
    assert len(ring) == 3
    assert all(r.response.get("error") == "ENGINE.MODEL.UNAVAILABLE" for r in ring)
    assert all(isinstance(r.latency_ms, int) and r.latency_ms >= 0 for r in ring)
    assert any(r.latency_ms > 0 for r in ring), (
        "FR-304 latency capture regressed to literal 0 — "
        "verify t0 = time.monotonic() is captured BEFORE the try block in _call_task"
    )


@pytest.mark.asyncio
async def test_refine_fr304_fallback_on_5xx():
    """Protocol-level failure (httpx.HTTPStatusError raised by raise_for_status)
    must also route through FR-304. Catch widening: `except httpx.HTTPError`
    covers both RequestError and HTTPStatusError."""
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    app_, obs, vr = _stub_inputs()
    with respx.mock(base_url="https://api.openai.com") as router:
        router.post("/v1/chat/completions").mock(return_value=Response(500, json={"error": "internal"}))
        refined = await orch.refine(app_, obs, vr)
    qualifiers = {t.qualifier for t in refined.tasks}
    assert qualifiers == {"ENGINE.MODEL.UNAVAILABLE"}
    assert len(ring) == 3


# Cycle C: strict-retry on malformed structured output
@pytest.mark.asyncio
async def test_refine_retries_once_on_malformed():
    settings = Settings()
    ring: deque = deque(maxlen=200)
    orch = OpenAIStrictOrchestrator(settings=settings, ring_buffer=ring, api_key="sk-test")
    app_, obs, vr = _stub_inputs()

    bad_payload = {
        "id": "chatcmpl-bad", "object": "chat.completion", "model": "gpt-4o-2024-08-06",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "{\"junk\":1}"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    with respx.mock(base_url="https://api.openai.com") as router:
        router.post("/v1/chat/completions").mock(return_value=Response(200, json=bad_payload))
        refined = await orch.refine(app_, obs, vr)
    qualifiers = {t.qualifier for t in refined.tasks}
    assert qualifiers == {"LLM_OUTPUT_INVALID"}
    # Each task: 2 attempts → 2 CallRecords. 3 tasks × 2 = 6.
    assert len(ring) == 6
