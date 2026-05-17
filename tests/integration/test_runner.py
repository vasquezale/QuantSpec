from pathlib import Path

import pytest

from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.decision import DecisionStatus
from quant_spec.pipeline.runner import (
    MissingArtifactError,
    run_pipeline,
    stage_backtest,
    stage_decision,
    stage_validate_brief,
)


def test_runner_produces_fail_demo_artifacts(tmp_path) -> None:
    result = run_pipeline(
        Path("examples/HYP-001-intraday-fail-demo.yaml"),
        storage=ArtifactStorage(tmp_path),
    )

    assert result.decision.status == DecisionStatus.CLOSED_BY_GATE
    assert result.gates.first_failed == "G2_sharpe_oos"
    for path in result.artifacts.values():
        assert path.exists()


def test_runner_produces_pass_demo_artifacts(tmp_path) -> None:
    result = run_pipeline(
        Path("examples/HYP-002-intraday-pass-demo.yaml"),
        storage=ArtifactStorage(tmp_path),
    )

    assert result.decision.status == DecisionStatus.CANDIDATE_FOR_REVIEW
    assert result.gates.summary == "PASS"
    for name in [
        "brief.yaml",
        "spec.md",
        "results.json",
        "gates.json",
        "report.md",
        "decision.md",
    ]:
        assert result.hypothesis_dir.joinpath(name).exists()


def test_runner_rejects_backtest_when_spec_artifact_is_missing(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)
    brief = stage_validate_brief(
        Path("examples/HYP-002-intraday-pass-demo.yaml"),
        storage,
    )

    with pytest.raises(MissingArtifactError, match="spec.md"):
        stage_backtest(brief, storage)


def test_runner_rejects_decision_when_report_artifact_is_missing(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)
    brief = stage_validate_brief(
        Path("examples/HYP-002-intraday-pass-demo.yaml"),
        storage,
    )

    with pytest.raises(MissingArtifactError, match="report.md"):
        stage_decision(brief.id, storage)
