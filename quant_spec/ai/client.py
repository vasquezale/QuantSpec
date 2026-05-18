"""LLM client boundary used by fixture and opt-in live runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from quant_spec.settings import Settings, get_settings

LLMMode = Literal["fixture", "live"]


class LLMModeError(RuntimeError):
    """Raised when a requested LLM mode is unavailable."""


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response returned by an LLM client."""

    text: str
    model: str
    usage: dict[str, Any]
    latency_ms: int | None = None
    raw_response: dict[str, Any] | None = None

    def to_json(self) -> dict[str, object]:
        """Return a JSON-serializable response payload."""

        payload: dict[str, object] = {
            "text": self.text,
            "model": self.model,
            "usage": self.usage,
            "latency_ms": self.latency_ms,
        }
        if self.raw_response is not None:
            payload["raw_response"] = self.raw_response
        return payload


class LLMClient(Protocol):
    """Protocol shared by fixture and live LLM clients."""

    def complete(
        self,
        hypothesis_id: str,
        response_name: str,
        *,
        system: str = "",
        user: str = "",
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Return a normalized LLM response."""


class FixtureLLMClient:
    """Load versioned local LLM responses from package fixtures."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self.fixtures_dir = fixtures_dir or Path(__file__).parent / "fixtures"

    def complete(
        self,
        hypothesis_id: str,
        response_name: str,
        *,
        system: str = "",
        user: str = "",
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Return the fixture response for a hypothesis and response name."""

        response_path = self.fixtures_dir / hypothesis_id / f"{response_name}.json"
        payload = json.loads(response_path.read_text(encoding="utf-8"))
        return LLMResponse(
            text=str(payload["text"]),
            model=str(payload.get("model", "fixture-llm")),
            usage=dict(payload.get("usage", {})),
            latency_ms=payload.get("latency_ms"),
            raw_response=payload,
        )


class LiveClaudeClient:
    """Anthropic Claude client used only when live mode is explicitly selected."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        api_key = self.settings.anthropic_api_key
        model = self.settings.claude_model.strip()
        if not api_key:
            msg = "ANTHROPIC_API_KEY is required for --llm-mode live"
            raise LLMModeError(msg)
        if not model:
            msg = "QUANTSPEC_CLAUDE_MODEL must be set or use the documented default"
            raise LLMModeError(msg)
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - dependency is declared
            msg = "anthropic package is required for --llm-mode live"
            raise LLMModeError(msg) from exc
        self.model = model
        self._client = Anthropic(
            api_key=api_key,
            timeout=self.settings.http_timeout_s,
            max_retries=self.settings.llm_max_retries,
        )

    def complete(
        self,
        hypothesis_id: str,
        response_name: str,
        *,
        system: str = "",
        user: str = "",
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Call Claude Messages API and normalize the response."""

        started = time.perf_counter()
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            msg = (
                f"Claude live request failed for {hypothesis_id}/{response_name}: {exc}"
            )
            raise LLMModeError(msg) from exc
        latency_ms = round((time.perf_counter() - started) * 1000)
        return LLMResponse(
            text=_text_from_message(message),
            model=str(getattr(message, "model", self.model)),
            usage=_usage_payload(getattr(message, "usage", None)),
            latency_ms=latency_ms,
            raw_response=_raw_message_payload(message),
        )


def client_for_mode(llm_mode: LLMMode) -> LLMClient:
    """Return the supported client for the requested mode."""

    if llm_mode == "fixture":
        return FixtureLLMClient()
    if llm_mode == "live":
        return LiveClaudeClient()
    msg = f"unsupported LLM mode: {llm_mode}"
    raise LLMModeError(msg)


def _text_from_message(message: Any) -> str:
    blocks = getattr(message, "content", [])
    parts: list[str] = []
    for block in blocks:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return "\n".join(parts).strip()


def _usage_payload(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        payload = usage.model_dump(mode="json")
    elif isinstance(usage, dict):
        payload = usage
    else:
        payload = {
            key: getattr(usage, key)
            for key in dir(usage)
            if key.endswith("_tokens") and isinstance(getattr(usage, key), int)
        }
    return {
        str(key): _jsonable_usage_value(value)
        for key, value in payload.items()
        if value is not None
    }


def _jsonable_usage_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _jsonable_usage_value(nested_value)
            for key, nested_value in value.items()
            if nested_value is not None
        }
    if isinstance(value, list):
        return [_jsonable_usage_value(item) for item in value]
    if isinstance(value, int | float | str | bool):
        return value
    return str(value)


def _raw_message_payload(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return dict(message.model_dump(mode="json"))
    if hasattr(message, "to_json"):
        return dict(json.loads(message.to_json()))
    return {
        "id": getattr(message, "id", None),
        "model": getattr(message, "model", None),
        "stop_reason": getattr(message, "stop_reason", None),
        "usage": _usage_payload(getattr(message, "usage", None)),
    }
