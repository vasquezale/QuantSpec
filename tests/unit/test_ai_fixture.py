from pathlib import Path

import pytest

from quant_spec.ai.client import LLMModeError, client_for_mode
from quant_spec.ai.report_generator import (
    ReportValidationError,
    generate_report,
    validate_report,
)
from quant_spec.ai.spec_generator import generate_spec
from quant_spec.io.storage import ArtifactStorage
from quant_spec.pipeline.runner import stage_gates, stage_validate_brief
from quant_spec.validation.backtesting import run_python_demo_engine


def test_fixture_client_loads_versioned_response() -> None:
    client = client_for_mode("fixture")
    response = client.complete("HYP-001-intraday-fail-demo", "spec_response")

    assert "## Entry Conditions" in response.text
    assert response.model == "fixture-llm"


def test_live_mode_fails_fast_without_external_call() -> None:
    with pytest.raises(LLMModeError):
        client_for_mode("live")


def test_fixture_generators_write_spec_report_and_raw_payloads(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)
    brief = stage_validate_brief(
        Path("examples/HYP-001-intraday-fail-demo.yaml"),
        storage,
    )

    spec_path = generate_spec(brief, storage)
    result = run_python_demo_engine(brief, spec_path, storage)
    gates = stage_gates(result, storage)
    report_path = generate_report(brief, spec_path, result, gates, storage)

    assert spec_path.exists()
    assert report_path.exists()
    assert "OOS degradation is 100.00%" in report_path.read_text(encoding="utf-8")
    assert storage.raw_dir(brief.id).joinpath("spec_response.json").exists()
    assert storage.raw_dir(brief.id).joinpath("report_response.json").exists()


def test_report_validation_requires_oos_degradation_evidence(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)
    brief = stage_validate_brief(
        Path("examples/HYP-001-intraday-fail-demo.yaml"),
        storage,
    )
    spec_path = generate_spec(brief, storage)
    result = run_python_demo_engine(brief, spec_path, storage)
    gates = stage_gates(result, storage)
    incomplete_report = (
        "## Datos\n\n"
        "The out-of-sample Sharpe is 0.00, the out-of-sample win rate is "
        "50.00%, and the out-of-sample max drawdown is 0.40%. "
        "Gate summary: FAIL. First failed gate: G2_sharpe_oos.\n\n"
        "## Interpretacion\n\n"
        "The evidence does not satisfy the fixed quality gates.\n\n"
        "## Recomendacion\n\n"
        "Close the hypothesis by gate outcome.\n"
    )

    with pytest.raises(ReportValidationError, match="required evidence values"):
        validate_report(incomplete_report, result, gates)
