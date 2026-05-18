"""Generate deterministic strategy specs from hypothesis briefs."""

from __future__ import annotations

from pathlib import Path

import yaml

from quant_spec.ai.client import LLMMode, client_for_mode
from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.brief import HypothesisBrief
from quant_spec.settings import get_settings

PROMPT_PATH = Path(__file__).parent / "prompts" / "spec_generator.system.md"
REQUIRED_SPEC_SECTIONS = [
    "## Entry Conditions",
    "## Exit Conditions",
    "## Risk Parameters",
    "## Validation Requirements",
    "## Assumptions",
    "## Known Risks",
]


class SpecValidationError(ValueError):
    """Raised when generated spec markdown is missing required sections."""


def generate_spec(
    brief: HypothesisBrief,
    storage: ArtifactStorage,
    llm_mode: LLMMode = "fixture",
) -> Path:
    """Generate, validate, persist, and return a spec markdown artifact."""

    settings = get_settings()
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_hash = storage.hash_file(PROMPT_PATH)
    client = client_for_mode(llm_mode)
    response = client.complete(
        brief.id,
        "spec_response",
        system=system_prompt,
        user=_render_spec_user_prompt(brief),
        max_tokens=2048,
    )
    storage.write_raw_json(brief.id, "spec_response.json", response.to_json())
    storage.append_usage(
        brief.id,
        "spec",
        _usage_record(response.to_json(), settings.prompts_version, prompt_hash),
    )
    body = response.text.strip() + "\n"
    validate_spec_sections(body)
    frontmatter = {
        "hypothesis_id": brief.id,
        "spec_version": 1,
        "generated_by": llm_mode,
        "prompts_version": settings.prompts_version,
        "prompt_hash": prompt_hash,
        "brief_hash": storage.hash_artifact(brief),
        "strategy": {
            "name": "intraday_breakout_demo",
            "params": {
                "entry_rule": "fixture_breakout",
                "risk_per_trade_pct": brief.risk_constraints.risk_per_trade_pct,
            },
        },
    }
    return storage.write_text(
        brief.id,
        "spec.md",
        _markdown_with_frontmatter(frontmatter, body),
    )


def validate_spec_sections(markdown: str) -> None:
    """Ensure all required spec sections are present."""

    missing = [section for section in REQUIRED_SPEC_SECTIONS if section not in markdown]
    if missing:
        msg = f"spec is missing required sections: {missing}"
        raise SpecValidationError(msg)


def _markdown_with_frontmatter(frontmatter: dict[str, object], body: str) -> str:
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False)
    return f"---\n{yaml_text}---\n\n{body}"


def _render_spec_user_prompt(brief: HypothesisBrief) -> str:
    brief_yaml = yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False)
    return "\n".join(
        [
            "Create a strategy specification for this hypothesis brief.",
            "Return only markdown with the required headings.",
            "",
            "Hypothesis brief:",
            "```yaml",
            brief_yaml.strip(),
            "```",
        ]
    )


def _usage_record(
    response_payload: dict[str, object],
    prompts_version: str,
    prompt_hash: str,
) -> dict[str, object]:
    return {
        "model": response_payload["model"],
        "usage": response_payload["usage"],
        "latency_ms": response_payload["latency_ms"],
        "prompts_version": prompts_version,
        "prompt_hash": prompt_hash,
    }
