"""CloudVisionExtractor — validated default. 9-call layout+per-field pipeline.

Source: E3 L1 §2.2, E3 L2 plan Task 10. Cycle A ships the extract pipeline +
per-instance Semaphore + per-field call helper. Cycle B adds the quality
short-circuit at the top of extract().
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time
from collections import deque
from datetime import datetime, timezone

import httpx

from app.config import Settings
from app.schemas.calls import CallRecord
from app.schemas.expected import BeverageClass
from app.schemas.extracted import FieldObservation
from app.schemas.label import Label
from app.vision import quality
from app.vision.tiebreak_gpt4o import _SCHEMAS

_FIELD_NAMES = (
    "brand_name",
    "class_type",
    "abv",
    "net_contents",
    "gov_warning",
    "heading_typography",
    "name_address",
    "country_origin",
)


class CloudVisionExtractor:
    def __init__(
        self,
        *,
        settings: Settings,
        ring_buffer: deque,
        api_key: str,
    ) -> None:
        self._settings = settings
        self._ring = ring_buffer
        self._api_key = api_key
        self._model = settings.llm_model_snapshot
        self._prompt_version = settings.prompt_version
        self._semaphore = asyncio.Semaphore(4)

    async def ensure_loaded(self) -> None:
        return None

    async def _call_per_field(
        self, *, field_name: str, crop: bytes, label: Label
    ) -> dict:
        body = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Extract field: {field_name}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64.b64encode(crop).decode()}"
                            },
                        },
                    ],
                }
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": field_name,
                    "strict": True,
                    "schema": _SCHEMAS[field_name],
                },
            },
        }
        call_kind = "layout" if field_name == "layout" else "field"
        async with self._semaphore:
            t0 = time.monotonic()
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
                )
                resp.raise_for_status()
            elapsed_ms = int((time.monotonic() - t0) * 1000)
        payload = resp.json()
        content = json.loads(payload["choices"][0]["message"]["content"])
        self._ring.append(
            CallRecord(
                ts=datetime.now(timezone.utc),
                batch_id=label.batch_id,
                label_id=label.label_id,
                stage="vision.gpt4o_tiebreak",
                request={
                    "field_name": field_name,
                    "call_kind": call_kind,
                    "crop_size": len(crop),
                },
                response=content,
                latency_ms=elapsed_ms,
                model=self._model,
                provider="openai",
                prompt_version=self._prompt_version,
                output_hash=hashlib.sha256(
                    json.dumps(content, sort_keys=True).encode()
                ).hexdigest()[:16],
            )
        )
        return content

    async def extract(self, label: Label) -> list[FieldObservation]:
        report = quality.assess(label)
        if report.disposition != "ok":
            return [
                FieldObservation(
                    field_id="quality",
                    beverage_class=BeverageClass.SPIRITS,
                    observed_value=None,
                    evidence=(),
                    upstream_meta={
                        "disposition": report.disposition,
                        "reason_code": report.reason_code,
                    },
                )
            ]

        layout = await self._call_per_field(
            field_name="layout", crop=label.image_bytes, label=label
        )
        bbox_by_id: dict[str, tuple[int, int, int, int]] = {}
        for entry in layout.get("fields", []):
            bbox = entry.get("bbox")
            if bbox and len(bbox) == 4:
                bbox_by_id[entry["id"]] = tuple(int(v) for v in bbox)

        observations: list[FieldObservation] = []
        for fname in _FIELD_NAMES:
            content = await self._call_per_field(
                field_name=fname, crop=label.image_bytes, label=label
            )
            observations.append(
                FieldObservation(
                    field_id=fname,
                    beverage_class=BeverageClass.SPIRITS,
                    observed_value=content,
                    evidence=(),
                    upstream_meta={"bbox": bbox_by_id.get(fname)},
                )
            )
        return observations
