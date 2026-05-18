import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from quant_spec.ai.client import LiveClaudeClient, LLMModeError, client_for_mode
from quant_spec.ai.report_generator import (
    ReportValidationError,
    generate_report,
    validate_report,
)
from quant_spec.ai.spec_generator import generate_spec
from quant_spec.io.storage import ArtifactStorage
from quant_spec.pipeline.runner import stage_gates, stage_validate_brief
from quant_spec.settings import Settings, get_settings
from quant_spec.validation.backtesting import run_python_demo_engine


def test_fixture_client_loads_versioned_response() -> None:
    client = client_for_mode("fixture")
    response = client.complete("HYP-001-intraday-fail-demo", "spec_response")

    assert "## Entry Conditions" in response.text
    assert response.model == "fixture-llm"


def test_live_mode_fails_fast_without_external_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setattr(
        "quant_spec.ai.client.get_settings",
        lambda: Settings(anthropic_api_key=None),
    )
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
    assert storage.raw_dir(brief.id).joinpath("usage.json").exists()


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


def test_report_validation_accepts_compact_percent_evidence(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)
    brief = stage_validate_brief(
        Path("examples/HYP-001-intraday-fail-demo.yaml"),
        storage,
    )
    spec_path = generate_spec(brief, storage)
    result = run_python_demo_engine(brief, spec_path, storage)
    gates = stage_gates(result, storage)
    win_rate = f"{result.metrics.outsample.win_rate:.0%}"
    max_drawdown = f"{result.metrics.outsample.max_drawdown:.1%}"
    oos_degradation = "100%"
    compact_report = (
        "## Datos\n\n"
        "The out-of-sample Sharpe is 0, the out-of-sample win rate is "
        f"{win_rate}, the out-of-sample max drawdown is {max_drawdown}, "
        f"and OOS degradation is {oos_degradation}. First failed gate: "
        "G2_sharpe_oos.\n\n"
        "## Interpretacion\n\n"
        "The evidence does not satisfy the fixed quality gates.\n\n"
        "## Recomendacion\n\n"
        "Close the hypothesis by gate outcome.\n"
    )

    validate_report(compact_report, result, gates)


def test_live_claude_client_normalizes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeMessages:
        def create(self, **kwargs: object) -> object:
            return SimpleNamespace(
                content=[SimpleNamespace(text="## Entry Conditions\n\nLive text")],
                model=kwargs["model"],
                usage=SimpleNamespace(input_tokens=7, output_tokens=11),
                model_dump=lambda mode="json": {
                    "id": "msg_test",
                    "model": kwargs["model"],
                    "content": [
                        {"type": "text", "text": "## Entry Conditions\n\nLive text"}
                    ],
                    "usage": {"input_tokens": 7, "output_tokens": 11},
                },
            )

    class FakeAnthropic:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs
            self.messages = FakeMessages()

    monkeypatch.setitem(
        sys.modules,
        "anthropic",
        SimpleNamespace(Anthropic=FakeAnthropic),
    )
    client = LiveClaudeClient(
        Settings(
            anthropic_api_key="test-key",
            claude_model="claude-test",
            http_timeout_s=3,
            llm_max_retries=1,
        )
    )

    response = client.complete(
        "HYP-001-intraday-fail-demo",
        "spec_response",
        system="system",
        user="user",
        max_tokens=64,
    )

    assert response.text.startswith("## Entry Conditions")
    assert response.model == "claude-test"
    assert response.usage == {"input_tokens": 7, "output_tokens": 11}
    assert response.latency_ms is not None
    assert response.raw_response is not None
