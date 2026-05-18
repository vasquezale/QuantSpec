"""Environment-driven settings for QuantSpec."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5-20250929"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )
    claude_model: str = Field(
        default=DEFAULT_CLAUDE_MODEL,
        validation_alias="QUANTSPEC_CLAUDE_MODEL",
    )
    http_timeout_s: float = Field(
        default=120.0,
        validation_alias="QUANTSPEC_HTTP_TIMEOUT_S",
    )
    llm_max_retries: int = Field(
        default=2,
        validation_alias="QUANTSPEC_LLM_MAX_RETRIES",
    )
    prompts_version: str = Field(
        default="1.0.0",
        validation_alias="QUANTSPEC_PROMPTS_VERSION",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for the current process."""

    return Settings()
