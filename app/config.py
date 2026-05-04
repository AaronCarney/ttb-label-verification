"""Pydantic Settings — single source of truth for the env-var inventory.

ARCH §12.2: every secret name is read here and **only** here. The grep
enforcement test (``tests/test_secrets_grep.py``) asserts no other module
references ``os.environ`` directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_TRUTHY = frozenset({"1", "true", "yes", "on"})


class Settings(BaseSettings):
    """Process-level configuration loaded from environment variables.

    Source: ARCH §12.2 (env-var inventory).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Vision selection (D-015).
    vision_mode: Literal["local", "cloud", "auto"] = Field(default="auto", alias="VISION_MODE")

    # Orchestrator selection (D-021).
    orchestrator_backend: Literal["openai", "anthropic"] = Field(
        default="openai", alias="ORCHESTRATOR_BACKEND"
    )

    # Secrets — required at request time when the corresponding seam is invoked.
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Pinned model + prompt versions (D-020).
    llm_model_snapshot: str = Field(default="gpt-4o-2024-08-06", alias="LLM_MODEL_SNAPSHOT")
    prompt_version: str = Field(default="v1", alias="PROMPT_VERSION")

    # Batch lookahead window.
    lookahead_k: int = Field(default=3, ge=1, alias="LOOKAHEAD_K")

    # Dev-only routes (D-019). Empty string and unset both coerce to False.
    dev_mode: bool = Field(default=False, alias="DEV_MODE")

    # Future OTel collector endpoint (S3 Q13).
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )

    # Logging level (L2-added; flag for ARCH §12.2 amendment).
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # YAML rules directory (D-014).
    rules_root: Path = Field(
        default=Path("rules").resolve(),
        alias="RULES_ROOT",
        description="Absolute path to the YAML rules directory (D-014).",
    )

    @field_validator("dev_mode", mode="before")
    @classmethod
    def _coerce_dev_mode(cls, value: object) -> bool:
        """Empty string / None / falsy strings → False; truthy strings → True."""
        if value is None or value == "":
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in _TRUTHY
        return bool(value)

    @classmethod
    def from_env(cls) -> "Settings":
        """Convenience factory mandated by L1 §2.2; equivalent to ``cls()``."""
        return cls()

    @property
    def app_version(self) -> str:
        return "0.1.0"
