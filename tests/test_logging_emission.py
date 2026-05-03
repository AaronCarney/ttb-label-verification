"""Logging subsystem: formatter + redaction + configure_logging."""
from __future__ import annotations

import json
import logging


def test_otel_genai_formatter_emits_one_json_line() -> None:
    from app.logging.otel_genai import OtelGenAIFormatter

    formatter = OtelGenAIFormatter()
    record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="evaluation_complete",
        args=None,
        exc_info=None,
    )
    record.evaluation_id = "00000000-0000-4000-8000-000000000001"
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["msg"] == "evaluation_complete"
    assert parsed["level"] == "INFO"
    assert parsed["evaluation_id"] == "00000000-0000-4000-8000-000000000001"
    assert "ts" in parsed


def test_otel_genai_formatter_uses_gen_ai_attribute_names() -> None:
    """ARCH §13.1: LLM-call log lines use OpenTelemetry GenAI conventions."""
    from app.logging.otel_genai import OtelGenAIFormatter

    formatter = OtelGenAIFormatter()
    record = logging.LogRecord(
        name="app", level=logging.INFO, pathname=__file__, lineno=1,
        msg="llm_call", args=None, exc_info=None,
    )
    setattr(record, "gen_ai.request.model", "gpt-4o-2024-08-06")
    setattr(record, "gen_ai.response.model", "gpt-4o-2024-08-06")
    setattr(record, "gen_ai.usage.input_tokens", 1234)
    line = formatter.format(record)
    parsed = json.loads(line)
    assert parsed["gen_ai.request.model"] == "gpt-4o-2024-08-06"
    assert parsed["gen_ai.usage.input_tokens"] == 1234
