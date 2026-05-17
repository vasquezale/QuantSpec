from pathlib import Path

from quant_spec.io.storage import ArtifactStorage
from quant_spec.pipeline.runner import stage_spec, stage_validate_brief
from quant_spec.validation.backtesting import (
    apply_risk_constraints,
    run_python_demo_engine,
)
from quant_spec.validation.metrics import load_fixture_trades


def test_python_demo_engine_persists_results_and_markdown(tmp_path) -> None:
    storage = ArtifactStorage(tmp_path)
    brief = stage_validate_brief(
        Path("examples/HYP-002-intraday-pass-demo.yaml"),
        storage,
    )
    spec_path = stage_spec(brief, storage)

    result = run_python_demo_engine(brief, spec_path, storage)

    assert result.engine == "python_demo_engine"
    assert result.result_hash.startswith("sha256:")
    assert storage.artifact_path(brief.id, "results.json").exists()
    assert storage.artifact_path(brief.id, "results.md").exists()


def test_risk_constraints_discard_non_compliant_trades(tmp_path) -> None:
    trades = load_fixture_trades("HYP-002-intraday-pass-demo")
    brief = stage_validate_brief(
        Path("examples/HYP-002-intraday-pass-demo.yaml"),
        ArtifactStorage(tmp_path),
    )
    trades.loc[0, "has_stop_loss"] = False
    trades.loc[1, "intraday"] = False

    filtered, violations = apply_risk_constraints(trades, brief)

    assert len(filtered) == len(trades) - 2
    assert violations.discarded_trades == 2
    assert violations.reasons == {
        "missing_stop_loss": 1,
        "not_intraday": 1,
    }
