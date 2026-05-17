"""Generate deterministic executive reports from validated artifacts."""

from __future__ import annotations

from pathlib import Path

import yaml

from quant_spec.ai.client import LLMMode, client_for_mode
from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.brief import HypothesisBrief
from quant_spec.models.gates import GateReport
from quant_spec.models.results import BacktestResult

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

    client = client_for_mode(llm_mode)
    response = client.complete(brief.id, "report_response")
    rendered_body = _render_report_body(response.text, result, gates)
    storage.write_raw_json(
        brief.id,
        "report_response.json",
        {**response.to_json(), "text": rendered_body},
    )
    validate_report(rendered_body, result, gates)
    frontmatter = {
        "hypothesis_id": brief.id,
        "generated_by": llm_mode,
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
    required_values = [
        f"{result.metrics.outsample.sharpe:.2f}",
        f"{result.metrics.outsample.win_rate:.2%}",
        f"{result.metrics.outsample.max_drawdown:.2%}",
        f"{_oos_degradation(gates):.2%}",
        gates.first_failed or "none",
    ]
    absent = [value for value in required_values if value not in markdown]
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


def _oos_degradation(gates: GateReport) -> float:
    for gate in gates.gates:
        if gate.id == "G5_oos_degradation" and gate.metric is not None:
            return gate.metric
    msg = "report is missing OOS degradation gate evidence"
    raise ReportValidationError(msg)


def _markdown_with_frontmatter(frontmatter: dict[str, object], body: str) -> str:
    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False)
    return f"---\n{yaml_text}---\n\n{body}"
