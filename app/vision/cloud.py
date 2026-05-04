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
from app.schemas.extracted import Evidence, EvidenceSource, FieldObservation, MatchKind
from app.schemas.label import Label
from app.vision import quality

_SCHEMAS = {
    "brand_name": {
        "type": "object",
        "properties": {"brand_name": {"type": "string"}},
        "required": ["brand_name"],
        "additionalProperties": False,
    },
    "class_type": {
        "type": "object",
        "properties": {"class_type": {"type": "string"}},
        "required": ["class_type"],
        "additionalProperties": False,
    },
    "abv": {
        "type": "object",
        "properties": {
            "abv_pct": {"type": "number"},
            "unit": {"type": "string"},
        },
        "required": ["abv_pct", "unit"],
        "additionalProperties": False,
    },
    "net_contents": {
        "type": "object",
        "properties": {
            "net_contents_value": {"type": "number"},
            "unit": {"type": "string"},
        },
        "required": ["net_contents_value", "unit"],
        "additionalProperties": False,
    },
    "gov_warning": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    },
    "heading_typography": {
        "type": "object",
        "properties": {
            "all_caps": {"type": "boolean"},
            "bold": {"type": "boolean"},
            "type_size_pt": {"type": "number"},
        },
        "required": ["all_caps", "bold", "type_size_pt"],
        "additionalProperties": False,
    },
    "name_address": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "city": {"type": "string"},
            "state": {"type": "string"},
        },
        "required": ["name", "city", "state"],
        "additionalProperties": False,
    },
    "country_origin": {
        "type": "object",
        "properties": {"country": {"type": "string"}},
        "required": ["country"],
        "additionalProperties": False,
    },
    "layout": {
        "type": "object",
        "properties": {
            "fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "bbox": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["id", "bbox"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["fields"],
        "additionalProperties": False,
    },
}

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

    async def _gated_call(
        self, *, field_name: str, crop: bytes, label: Label
    ) -> dict:
        async with self._semaphore:
            return await self._call_per_field(
                field_name=field_name, crop=crop, label=label
            )

    async def extract(self, label: Label) -> list[FieldObservation]:
        report = quality.assess(label)
        if report.disposition != "ok":
            return [
                FieldObservation(
                    field_id="quality",
                    beverage_class=BeverageClass.SPIRITS,
                    observed_value=None,
                    evidence=(_make_evidence(
                        field_id="quality", bbox=None, text=report.reason_code
                    ),),
                    upstream_meta={
                        "disposition": report.disposition,
                        "reason_code": report.reason_code,
                    },
                )
            ]

        layout = await self._gated_call(
            field_name="layout", crop=label.image_bytes, label=label
        )
        bbox_by_id: dict[str, tuple[int, int, int, int]] = {}
        for entry in layout.get("fields", []):
            bbox = entry.get("bbox")
            if bbox and len(bbox) == 4:
                bbox_by_id[entry["id"]] = tuple(int(v) for v in bbox)

        contents = await asyncio.gather(
            *(
                self._gated_call(field_name=fname, crop=label.image_bytes, label=label)
                for fname in _FIELD_NAMES
            )
        )
        observations: list[FieldObservation] = []
        for fname, content in zip(_FIELD_NAMES, contents):
            text = _extract_text(content)
            observations.append(
                FieldObservation(
                    field_id=fname,
                    beverage_class=BeverageClass.SPIRITS,
                    observed_value=content,
                    evidence=(_make_evidence(
                        field_id=fname, bbox=bbox_by_id.get(fname), text=text,
                    ),),
                    upstream_meta={"bbox": bbox_by_id.get(fname)},
                )
            )
        return observations


def _extract_text(content: dict) -> str | None:
    """Pull a representative string out of the per-field LLM JSON payload.
    Schemas vary by field (text/name/country/abv); pick the first present."""
    if not isinstance(content, dict):
        return str(content) if content is not None else None
    for key in ("text", "name", "country", "value"):
        v = content.get(key)
        if v is not None:
            return str(v)
    # Fall back to any non-None scalar value (e.g. abv numeric).
    for v in content.values():
        if isinstance(v, (str, int, float)):
            return str(v)
    return None


def _make_evidence(
    *, field_id: str, bbox: tuple[int, int, int, int] | None, text: str | None,
) -> Evidence:
    """Synthesize a single Evidence from the LLM's per-field payload + the
    bbox surfaced by the layout call. confidence=0.7 is a deliberate stand-in
    until E3 surfaces per-call confidence from the JSON-schema response."""
    return Evidence(
        field_id=field_id,
        source=EvidenceSource.LAYOUT,
        bbox=bbox,
        extracted_text=text,
        match_kind=MatchKind.NONE,
        confidence=0.7,
    )
