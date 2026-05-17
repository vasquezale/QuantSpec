import math

import pandas as pd
import pytest

from quant_spec.validation.metrics import (
    compute_fixture_metrics,
    compute_is_oos_metrics,
    compute_period_metrics,
    load_fixture_trades,
    oos_degradation,
)


def test_load_fixture_trades_validates_contract() -> None:
    trades = load_fixture_trades("HYP-001-intraday-fail-demo")

    assert list(trades.columns) == [
        "trade_id",
        "period",
        "open_time_utc",
        "close_time_utc",
        "side",
        "pnl_pct",
        "r_multiple",
        "has_stop_loss",
        "intraday",
    ]
    assert len(trades) == 20
    assert trades["trade_id"].is_unique


def test_compute_fixture_metrics_for_fail_demo() -> None:
    metrics = compute_fixture_metrics("HYP-001-intraday-fail-demo")

    assert metrics.insample.sharpe > 0.0
    assert metrics.outsample.sharpe == pytest.approx(0.0)
    assert metrics.outsample.win_rate == pytest.approx(0.5)
    assert metrics.outsample.n_trades == 10


def test_compute_fixture_metrics_for_pass_demo() -> None:
    metrics = compute_fixture_metrics("HYP-002-intraday-pass-demo")

    assert metrics.insample.sharpe > 0.0
    assert metrics.outsample.sharpe >= 1.5
    assert metrics.outsample.win_rate >= 0.55
    assert metrics.outsample.max_drawdown <= 0.20
    assert oos_degradation(metrics.insample.sharpe, metrics.outsample.sharpe) <= 0.20


def test_compute_is_oos_metrics_rejects_duplicate_trade_ids() -> None:
    trades = load_fixture_trades("HYP-001-intraday-fail-demo")
    trades.loc[1, "trade_id"] = trades.loc[0, "trade_id"]

    with pytest.raises(ValueError, match="trade_id"):
        compute_is_oos_metrics(trades)


def test_compute_period_metrics_handles_empty_and_constant_positive_returns() -> None:
    fail_trades = load_fixture_trades("HYP-001-intraday-fail-demo")
    empty_metrics = compute_period_metrics(fail_trades.iloc[0:0])
    constant_metrics = compute_period_metrics(
        pd.DataFrame(
            {
                "pnl_pct": [0.01, 0.01],
                "r_multiple": [1.0, 1.0],
            }
        )
    )

    assert empty_metrics.n_trades == 0
    assert math.isinf(constant_metrics.sharpe)
    assert math.isinf(constant_metrics.profit_factor)


def test_oos_degradation_handles_zero_or_invalid_is_sharpe() -> None:
    assert oos_degradation(0.0, 0.1) == 0.0
    assert math.isinf(oos_degradation(0.0, -0.1))
    assert math.isinf(oos_degradation(math.nan, 1.0))


def test_metrics_reject_missing_required_columns() -> None:
    trades = pd.DataFrame({"trade_id": ["T-1"]})

    with pytest.raises(ValueError, match="missing required columns"):
        compute_is_oos_metrics(trades)


@pytest.mark.parametrize(
    ("column", "bad_value", "message"),
    [
        ("period", "validation", "period"),
        ("side", "flat", "side"),
        ("pnl_pct", math.inf, "finite"),
        ("has_stop_loss", "yes", "has_stop_loss"),
        ("intraday", "yes", "intraday"),
    ],
)
def test_metrics_reject_invalid_trade_values(
    column: str,
    bad_value: object,
    message: str,
) -> None:
    trades = load_fixture_trades("HYP-001-intraday-fail-demo")
    if column in {"has_stop_loss", "intraday"}:
        trades[column] = trades[column].astype(object)
    trades.loc[0, column] = bad_value

    with pytest.raises(ValueError, match=message):
        compute_is_oos_metrics(trades)
