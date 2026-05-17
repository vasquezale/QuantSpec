"""Generate deterministic strategy specs from hypothesis briefs."""

from __future__ import annotations

from pathlib import Path

import yaml

from quant_spec.ai.client import LLMMode, client_for_mode
from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.brief import HypothesisBrief

PROMPTS_VERSION = "1.0.0"
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

    client = client_for_mode(llm_mode)
    response = client.complete(brief.id, "spec_response")
    storage.write_raw_json(brief.id, "spec_response.json", response.to_json())
    body = response.text.strip() + "\n"
    validate_spec_sections(body)
    frontmatter = {
        "hypothesis_id": brief.id,
        "spec_version": 1,
        "generated_by": llm_mode,
        "prompts_version": PROMPTS_VERSION,
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
