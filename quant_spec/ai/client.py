"""Offline LLM client boundary used by deterministic demo runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LLMMode = Literal["fixture", "live"]


class LLMModeError(RuntimeError):
    """Raised when a requested LLM mode is unavailable."""


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response returned by an LLM client."""

    text: str
    model: str
    usage: dict[str, int]
    latency_ms: int | None = None

    def to_json(self) -> dict[str, object]:
        """Return a JSON-serializable response payload."""

        return {
            "text": self.text,
            "model": self.model,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
        }


class FixtureLLMClient:
    """Load versioned local LLM responses from package fixtures."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or Path(__file__).parent / "fixtures"

    def complete(self, hypothesis_id: str, response_name: str) -> LLMResponse:
        """Return the fixture response for a hypothesis and response name."""

        response_path = self.fixtures_dir / hypothesis_id / f"{response_name}.json"
        payload = json.loads(response_path.read_text(encoding="utf-8"))
        return LLMResponse(
            text=str(payload["text"]),
            model=str(payload.get("model", "fixture-llm")),
            usage=dict(payload.get("usage", {})),
            latency_ms=payload.get("latency_ms"),
        )


def client_for_mode(llm_mode: LLMMode) -> FixtureLLMClient:
    """Return the supported client for the requested mode."""

    if llm_mode == "fixture":
        return FixtureLLMClient()
    msg = "Live LLM mode is unavailable in the offline MVP."
    raise LLMModeError(msg)
