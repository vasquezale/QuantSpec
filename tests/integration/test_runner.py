from pathlib import Path

from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.decision import DecisionStatus
from quant_spec.pipeline.runner import run_pipeline


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
