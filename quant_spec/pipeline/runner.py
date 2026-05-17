"""Sequential offline pipeline runner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from quant_spec.ai.client import LLMMode
from quant_spec.ai.report_generator import generate_report
from quant_spec.ai.spec_generator import generate_spec
from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.brief import HypothesisBrief
from quant_spec.models.decision import DecisionRecord, DecisionStatus
from quant_spec.models.gates import GateReport, GateSummary
from quant_spec.models.results import BacktestResult
from quant_spec.validation.backtesting import run_python_demo_engine
from quant_spec.validation.gates import evaluate_gates


class BriefValidationError(ValueError):
    """Raised when a brief cannot be loaded or validated."""


class MissingArtifactError(FileNotFoundError):
    """Raised when a required previous artifact is missing."""


@dataclass(frozen=True)
class PipelineResult:
    """Useful paths and records produced by a pipeline run."""

    hypothesis_id: str
    hypothesis_dir: Path
    decision: DecisionRecord
    gates: GateReport
    artifacts: dict[str, Path]


def run_pipeline(
    brief_path: Path | str,
    llm_mode: LLMMode = "fixture",
    storage: ArtifactStorage | None = None,
) -> PipelineResult:
    """Run the complete sequential pipeline for a brief."""

    artifact_storage = storage or ArtifactStorage()
    brief = stage_validate_brief(brief_path, artifact_storage)
    spec_path = stage_spec(brief, artifact_storage, llm_mode)
    result = stage_backtest(brief, artifact_storage)
    gates = stage_gates(result, artifact_storage)
    report_path = stage_report(brief, artifact_storage, llm_mode)
    decision = stage_decision(brief.id, artifact_storage)
    return PipelineResult(
        hypothesis_id=brief.id,
        hypothesis_dir=artifact_storage.hypothesis_dir(brief.id),
        decision=decision,
        gates=gates,
        artifacts={
            "brief": artifact_storage.artifact_path(brief.id, "brief.yaml"),
            "spec": spec_path,
            "results": artifact_storage.artifact_path(brief.id, "results.json"),
            "gates": artifact_storage.artifact_path(brief.id, "gates.json"),
            "report": report_path,
            "decision": artifact_storage.artifact_path(brief.id, "decision.md"),
        },
    )


def stage_validate_brief(
    brief_path: Path | str,
    storage: ArtifactStorage,
) -> HypothesisBrief:
    """Load, validate, and persist a hypothesis brief."""

    path = Path(brief_path)
    if not path.exists():
        msg = f"brief not found: {path}"
        raise BriefValidationError(msg)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = "brief YAML must contain a mapping"
        raise BriefValidationError(msg)
    try:
        brief = HypothesisBrief.model_validate(payload)
    except ValidationError as exc:
        raise BriefValidationError(str(exc)) from exc
    storage.ensure_layout(brief.id)
    storage.write_text(
        brief.id,
        "brief.yaml",
        yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False),
    )
    return brief


def stage_spec(
    brief: HypothesisBrief,
    storage: ArtifactStorage,
    llm_mode: LLMMode = "fixture",
) -> Path:
    """Generate the strategy spec artifact."""

    return generate_spec(brief, storage, llm_mode)


def stage_backtest(
    brief: HypothesisBrief,
    storage: ArtifactStorage,
) -> BacktestResult:
    """Run deterministic evaluation after spec generation."""

    spec_path = storage.artifact_path(brief.id, "spec.md")
    _require_artifact(spec_path)
    return run_python_demo_engine(brief, spec_path, storage)


def stage_gates(result: BacktestResult, storage: ArtifactStorage) -> GateReport:
    """Evaluate fixed quality gates after results generation."""

    gates = evaluate_gates(result)
    storage.write_json(result.hypothesis_id, "gates.json", gates)
    storage.write_text(result.hypothesis_id, "gates.md", _gates_markdown(gates))
    return gates


def stage_report(
    brief: HypothesisBrief,
    storage: ArtifactStorage,
    llm_mode: LLMMode = "fixture",
) -> Path:
    """Generate the report after results and gates exist."""

    spec_path = storage.artifact_path(brief.id, "spec.md")
    result = BacktestResult.model_validate(storage.read_json(brief.id, "results.json"))
    gates = GateReport.model_validate(storage.read_json(brief.id, "gates.json"))
    _require_artifact(spec_path)
    return generate_report(brief, spec_path, result, gates, storage, llm_mode)


def stage_decision(
    hypothesis_id: str,
    storage: ArtifactStorage,
    decided_by: str = "operator",
) -> DecisionRecord:
    """Generate the final decision from persisted report and gates."""

    report_path = storage.artifact_path(hypothesis_id, "report.md")
    _require_artifact(report_path)
    gates = GateReport.model_validate(storage.read_json(hypothesis_id, "gates.json"))
    status = (
        DecisionStatus.CANDIDATE_FOR_REVIEW
        if gates.summary == GateSummary.PASS
        else DecisionStatus.CLOSED_BY_GATE
    )
    decision = DecisionRecord(
        hypothesis_id=hypothesis_id,
        status=status,
        decided_by=decided_by,
        gates_summary=gates.summary,
        report_hash=storage.hash_file(report_path),
    )
    storage.write_text(
        hypothesis_id,
        "decision.md",
        _decision_markdown(decision, gates),
    )
    return decision


def load_persisted_brief(
    target: Path | str,
    storage: ArtifactStorage,
) -> HypothesisBrief:
    """Load a brief from a path or a persisted hypothesis id."""

    target_path = Path(target)
    if target_path.exists():
        return stage_validate_brief(target_path, storage)
    brief_path = storage.artifact_path(str(target), "brief.yaml")
    return stage_validate_brief(brief_path, storage)


def _gates_markdown(gates: GateReport) -> str:
    lines = [
        f"# Quality Gates: {gates.hypothesis_id}",
        "",
        f"- Summary: {gates.summary.value}",
        f"- First failed: {gates.first_failed or 'none'}",
        "",
        "| Gate | Metric | Threshold | Result |",
        "|---|---:|---:|---|",
    ]
    for gate in gates.gates:
        metric = "n/a" if gate.metric is None else f"{gate.metric:.4f}"
        lines.append(
            f"| {gate.id} | {metric} | {gate.op.value} {gate.threshold:.4f} | "
            f"{gate.status.value} |"
        )
    lines.append("")
    return "\n".join(lines)


def _decision_markdown(decision: DecisionRecord, gates: GateReport) -> str:
    frontmatter: dict[str, Any] = decision.model_dump(mode="json")
    evidence = (
        "All gates passed. The hypothesis is ready for human review."
        if decision.status == DecisionStatus.CANDIDATE_FOR_REVIEW
        else f"The hypothesis is closed because {gates.first_failed} failed."
    )
    note = (
        "This document records a reproducible validation outcome. "
        "It is not a recommendation to trade."
    )
    return "\n".join(
        [
            "---",
            yaml.safe_dump(frontmatter, sort_keys=False).strip(),
            "---",
            "",
            "## Decision",
            decision.status.value,
            "",
            "## Evidence",
            evidence,
            "",
            "## Note",
            note,
            "",
        ]
    )


def _require_artifact(path: Path) -> None:
    if not path.exists():
        msg = f"required artifact missing: {path}"
        raise MissingArtifactError(msg)
