"""GPT-4o-on-crop tiebreaker for the local-mode pipeline. Source: E3 L1 §2.3.

Single-call OpenAI Structured Output (strict:true) returning a typed JSON dict.
HTTP layer only — this module never imports the openai SDK directly; uses
httpx so respx recordings cover the wire.
"""
from __future__ import annotations

import base64
import hashlib
import json
import time
from collections import deque
from datetime import datetime, timezone

import httpx


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


class GPT4oTiebreakRunner:
    def __init__(
        self,
        *,
        ring_buffer: deque,
        batch_id: str,
        label_id: str,
        api_key: str,
        model_snapshot: str,
        prompt_version: str,
    ) -> None:
        self._ring = ring_buffer
        self._batch_id = batch_id
        self._label_id = label_id
        self._api_key = api_key
        self._model = model_snapshot
        self._prompt_version = prompt_version

    async def ensure_loaded(self) -> None:  # no-op; HTTP client is per-call
        return None

    async def run(self, *, crop: bytes, prompt: str) -> dict:
        from app.schemas.calls import CallRecord

        body = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Extract field: {prompt}"},
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
                    "name": prompt,
                    "strict": True,
                    "schema": _SCHEMAS[prompt],
                },
            },
        }
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
                batch_id=self._batch_id,
                label_id=self._label_id,
                stage="vision.gpt4o_tiebreak",
                request={"prompt": prompt, "crop_size": len(crop)},
                response=content,
                latency_ms=elapsed_ms,
                model=self._model,
                provider="openai",
                prompt_version=self._prompt_version,
                output_hash=hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()[:16],
            )
        )
        return content
