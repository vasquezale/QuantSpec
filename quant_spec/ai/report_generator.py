"""Generate deterministic executive reports from validated artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from quant_spec.ai.client import LLMMode, client_for_mode
from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.brief import HypothesisBrief
from quant_spec.models.gates import GateReport
from quant_spec.models.results import BacktestResult
from quant_spec.settings import get_settings

PROMPT_PATH = Path(__file__).parent / "prompts" / "report_generator.system.md"
REQUIRED_REPORT_SECTIONS = [
    "## Datos",
    "## Interpretacion",
    "## Recomendacion",
]


class ReportValidationError(ValueError):
    """Raised when generated report markdown is invalid."""


def generate_report(
    brief: HypothesisBrief,
    spec_path: Path,
    result: BacktestResult,
    gates: GateReport,
    storage: ArtifactStorage,
    llm_mode: LLMMode = "fixture",
) -> Path:
    """Generate, validate, persist, and return a report markdown artifact."""

    settings = get_settings()
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    prompt_hash = storage.hash_file(PROMPT_PATH)
    client = client_for_mode(llm_mode)
    response = client.complete(
        brief.id,
        "report_response",
        system=system_prompt,
        user=_render_report_user_prompt(brief, spec_path, result, gates),
        max_tokens=2048,
    )
    rendered_body = (
        _render_report_body(response.text, result, gates)
        if llm_mode == "fixture"
        else response.text.strip() + "\n"
    )
    if llm_mode == "live":
        rendered_body = _append_verified_evidence(rendered_body, result, gates)
    storage.write_raw_json(
        brief.id,
        "report_response.json",
        {**response.to_json(), "text": rendered_body},
    )
    storage.append_usage(
        brief.id,
        "report",
        _usage_record(response.to_json(), settings.prompts_version, prompt_hash),
    )
    validate_report(rendered_body, result, gates)
    frontmatter = {
        "hypothesis_id": brief.id,
        "generated_by": llm_mode,
        "prompts_version": settings.prompts_version,
        "prompt_hash": prompt_hash,
        "input_hashes": {
            "brief_hash": storage.hash_artifact(brief),
            "spec_hash": storage.hash_file(spec_path),
            "result_hash": result.result_hash,
            "gates_hash": gates.gates_hash,
        },
        "gates_summary": gates.summary.value,
    }
    return storage.write_text(
        brief.id,
        "report.md",
        _markdown_with_frontmatter(frontmatter, rendered_body),
    )


def validate_report(
    markdown: str,
    result: BacktestResult,
    gates: GateReport,
) -> None:
    """Validate required report sections and metric references."""

    missing = [
        section for section in REQUIRED_REPORT_SECTIONS if section not in markdown
    ]
    if missing:
        msg = f"report is missing required sections: {missing}"
        raise ReportValidationError(msg)
    required_values = {
        "sharpe_oos": _number_variants(result.metrics.outsample.sharpe),
        "win_rate_oos": _percent_variants(result.metrics.outsample.win_rate),
        "max_drawdown_oos": _percent_variants(result.metrics.outsample.max_drawdown),
        "oos_degradation": _percent_variants(_oos_degradation(gates)),
        "first_failed": {gates.first_failed or "none"},
    }
    absent = [
        label
        for label, variants in required_values.items()
        if not any(variant in markdown for variant in variants)
    ]
    if absent:
        msg = f"report is missing required evidence values: {absent}"
        raise ReportValidationError(msg)


def _render_report_body(
    template: str,
    result: BacktestResult,
    gates: GateReport,
) -> str:
    return (
        template.format(
            sharpe_oos=result.metrics.outsample.sharpe,
            win_rate_oos=result.metrics.outsample.win_rate,
            max_drawdown_oos=result.metrics.outsample.max_drawdown,
            oos_degradation=_oos_degradation(gates),
            first_failed=gates.first_failed or "none",
            gates_summary=gates.summary.value,
        ).strip()
        + "\n"
    )


def _append_verified_evidence(
    markdown: str,
    result: BacktestResult,
    gates: GateReport,
) -> str:
    evidence = "\n".join(
        [
            "",
            "## Verified Evidence",
            "",
            f"- Sharpe OOS: {result.metrics.outsample.sharpe:.2f}",
            f"- Win rate OOS: {result.metrics.outsample.win_rate:.2%}",
            f"- Max drawdown OOS: {result.metrics.outsample.max_drawdown:.2%}",
            f"- OOS degradation: {_oos_degradation(gates):.2%}",
            f"- First failed gate: {gates.first_failed or 'none'}",
            "",
        ]
    )
    return markdown.rstrip() + "\n" + evidence


def _oos_degradation(gates: GateReport) -> float:
    for gate in gates.gates:
        if gate.id == "G5_oos_degradation" and gate.metric is not None:
            return gate.metric
    msg = "report is missing OOS degradation gate evidence"
    raise ReportValidationError(msg)


def _markdown_with_frontmatter(frontmatter: dict[str, object], body: str) -> str:
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False)
    return f"---\n{yaml_text}---\n\n{body}"


def _number_variants(value: float) -> set[str]:
    return {f"{value:.2f}", f"{value:.1f}", f"{value:g}"}


def _percent_variants(value: float) -> set[str]:
    percent = value * 100
    return {
        f"{percent:.2f}%",
        f"{percent:.1f}%",
        f"{percent:g}%",
        f"{value:.2%}",
        f"{value:.1%}",
    }


def _render_report_user_prompt(
    brief: HypothesisBrief,
    spec_path: Path,
    result: BacktestResult,
    gates: GateReport,
) -> str:
    evidence_strings = [
        f"{result.metrics.outsample.sharpe:.2f}",
        f"{result.metrics.outsample.win_rate:.2%}",
        f"{result.metrics.outsample.max_drawdown:.2%}",
        f"{_oos_degradation(gates):.2%}",
        gates.first_failed or "none",
    ]
    return "\n".join(
        [
            "Create an executive report from these verified artifacts.",
            "Return only markdown with headings: ## Datos, ## Interpretacion, "
            "## Recomendacion.",
            "Do not invent numbers. Include these evidence strings exactly: "
            + ", ".join(evidence_strings),
            "",
            "Hypothesis brief:",
            "```yaml",
            yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False).strip(),
            "```",
            "",
            "Strategy spec:",
            "```markdown",
            spec_path.read_text(encoding="utf-8").strip(),
            "```",
            "",
            "Results JSON:",
            "```json",
            json.dumps(result.model_dump(mode="json"), indent=2, sort_keys=True),
            "```",
            "",
            "Gates JSON:",
            "```json",
            json.dumps(gates.model_dump(mode="json"), indent=2, sort_keys=True),
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
