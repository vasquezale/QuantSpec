from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from quant_spec.models import (
    BacktestResult,
    DecisionRecord,
    DecisionStatus,
    GateReport,
    GateSummary,
    HypothesisBrief,
)

VALID_HASH = "sha256:" + "a" * 64


def test_hypothesis_brief_validates_required_contract() -> None:
    brief = HypothesisBrief.model_validate(
        {
            "id": "HYP-001-intraday-fail-demo",
            "created_at": "2020-01-01T00:00:00Z",
            "author": "operator",
            "market": {
                "symbol": "DEMO_INTRADAY",
                "asset_class": "demo",
                "pip_size": 0.01,
            },
            "timeframe": "DEMO_M15",
            "central_hypothesis": "Synthetic intraday demo.",
            "risk_constraints": {
                "max_daily_risk_pct": 5.0,
                "risk_per_trade_pct": 0.5,
                "max_trades_per_day": 1,
                "must_have_stop_loss": True,
                "intraday_only": True,
            },
            "periods": {
                "insample": {"start": "2020-01-01", "end": "2020-12-31"},
                "outsample": {"start": "2021-01-01", "end": "2021-12-31"},
            },
            "data": {
                "source": "fixture",
                "path": (
                    "quant_spec/data/fixtures/HYP-001-intraday-fail-demo/trades.csv"
                ),
            },
            "notes": "Synthetic data only.",
        }
    )

    assert brief.id == "HYP-001-intraday-fail-demo"
    assert brief.periods.insample.end == date(2020, 12, 31)


def test_hypothesis_brief_rejects_bad_id_and_overlapping_periods() -> None:
    payload = {
        "id": "bad-id",
        "created_at": "2020-01-01T00:00:00Z",
        "author": "operator",
        "market": {"symbol": "DEMO", "asset_class": "demo", "pip_size": 0.01},
        "timeframe": "DEMO_M15",
        "central_hypothesis": "Synthetic intraday demo.",
        "risk_constraints": {
            "max_daily_risk_pct": 5.0,
            "risk_per_trade_pct": 0.5,
            "max_trades_per_day": 1,
            "must_have_stop_loss": True,
            "intraday_only": True,
        },
        "periods": {
            "insample": {"start": "2020-01-01", "end": "2021-01-01"},
            "outsample": {"start": "2021-01-01", "end": "2021-12-31"},
        },
        "data": {"source": "fixture", "path": "fixture.csv"},
    }

    with pytest.raises(ValidationError):
        HypothesisBrief.model_validate(payload)


def test_hypothesis_brief_rejects_reversed_period_window() -> None:
    payload = {
        "id": "HYP-001-intraday-fail-demo",
        "created_at": "2020-01-01T00:00:00Z",
        "author": "operator",
        "market": {"symbol": "DEMO", "asset_class": "demo", "pip_size": 0.01},
        "timeframe": "DEMO_M15",
        "central_hypothesis": "Synthetic intraday demo.",
        "risk_constraints": {
            "max_daily_risk_pct": 5.0,
            "risk_per_trade_pct": 0.5,
            "max_trades_per_day": 1,
            "must_have_stop_loss": True,
            "intraday_only": True,
        },
        "periods": {
            "insample": {"start": "2020-12-31", "end": "2020-01-01"},
            "outsample": {"start": "2021-01-01", "end": "2021-12-31"},
        },
        "data": {"source": "fixture", "path": "fixture.csv"},
    }

    with pytest.raises(ValidationError, match="period start"):
        HypothesisBrief.model_validate(payload)


def test_results_gates_and_decision_models_validate() -> None:
    result = BacktestResult.model_validate(
        {
            "hypothesis_id": "HYP-002-intraday-pass-demo",
            "engine": "python_demo_engine",
            "engine_version": "0.1.0",
            "brief_hash": VALID_HASH,
            "spec_hash": VALID_HASH,
            "executed_at": datetime(2026, 5, 15, tzinfo=UTC),
            "data_source": "fixture",
            "periods": {
                "insample": {
                    "start": "2020-01-01",
                    "end": "2020-12-31",
                    "n_trades": 10,
                },
                "outsample": {
                    "start": "2021-01-01",
                    "end": "2021-12-31",
                    "n_trades": 10,
                },
            },
            "metrics": {
                "insample": {
                    "sharpe": 1.0,
                    "win_rate": 0.6,
                    "max_drawdown": 0.1,
                    "profit_factor": 1.5,
                    "n_trades": 10,
                    "avg_trade_r": 0.2,
                },
                "outsample": {
                    "sharpe": 1.6,
                    "win_rate": 0.6,
                    "max_drawdown": 0.1,
                    "profit_factor": 1.5,
                    "n_trades": 10,
                    "avg_trade_r": 0.2,
                },
            },
            "risk_constraint_violations": {"discarded_trades": 0, "reasons": {}},
            "result_hash": VALID_HASH,
        }
    )
    gates = GateReport.model_validate(
        {
            "hypothesis_id": result.hypothesis_id,
            "result_hash": result.result_hash,
            "gates_hash": VALID_HASH,
            "summary": "PASS",
            "gates": [
                {
                    "id": "G1_sharpe_is",
                    "metric": 1.0,
                    "threshold": 0.0,
                    "op": ">=",
                    "status": "PASS",
                }
            ],
        }
    )
    decision = DecisionRecord.model_validate(
        {
            "hypothesis_id": result.hypothesis_id,
            "status": "CANDIDATE_FOR_REVIEW",
            "decided_by": "operator",
            "gates_summary": gates.summary,
            "report_hash": VALID_HASH,
        }
    )

    assert gates.summary == GateSummary.PASS
    assert decision.status == DecisionStatus.CANDIDATE_FOR_REVIEW
