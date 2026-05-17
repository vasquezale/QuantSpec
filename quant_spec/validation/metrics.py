"""Deterministic metrics for fixture trades."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from quant_spec.models.results import PeriodMetrics, ResultMetrics

REQUIRED_TRADE_COLUMNS = [
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
VALID_PERIODS = {"insample", "outsample"}
VALID_SIDES = {"long", "short"}


def fixture_trades_path(hypothesis_id: str) -> Path:
    """Return the packaged fixture trade path for a hypothesis."""

    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "fixtures"
        / hypothesis_id
        / "trades.csv"
    )


def load_fixture_trades(hypothesis_id: str) -> pd.DataFrame:
    """Load packaged fixture trades and validate the CSV contract."""

    return load_trades_csv(fixture_trades_path(hypothesis_id))


def load_trades_csv(path: Path | str) -> pd.DataFrame:
    """Load trades from CSV and validate required deterministic fields."""

    trades = pd.read_csv(path)
    _validate_trades(trades)
    trades = trades.copy()
    trades["open_time_utc"] = pd.to_datetime(trades["open_time_utc"], utc=True)
    trades["close_time_utc"] = pd.to_datetime(trades["close_time_utc"], utc=True)
    trades["has_stop_loss"] = trades["has_stop_loss"].map(_parse_bool)
    trades["intraday"] = trades["intraday"].map(_parse_bool)
    trades["pnl_pct"] = trades["pnl_pct"].astype(float)
    trades["r_multiple"] = trades["r_multiple"].astype(float)
    return trades.sort_values("trade_id").reset_index(drop=True)


def compute_period_metrics(trades: pd.DataFrame) -> PeriodMetrics:
    """Compute required metrics for one validation period."""

    if trades.empty:
        return PeriodMetrics(
            sharpe=0.0,
            win_rate=0.0,
            max_drawdown=0.0,
            profit_factor=0.0,
            n_trades=0,
            avg_trade_r=0.0,
        )

    pnl = trades["pnl_pct"].astype(float).to_numpy()
    r_multiple = trades["r_multiple"].astype(float).to_numpy()
    wins = pnl > 0
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(abs(pnl[pnl < 0].sum()))
    profit_factor = math.inf if gross_loss == 0 and gross_profit > 0 else 0.0
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss

    return PeriodMetrics(
        sharpe=_trade_sharpe(pnl),
        win_rate=float(wins.mean()),
        max_drawdown=_max_drawdown(pnl),
        profit_factor=profit_factor,
        n_trades=int(len(trades)),
        avg_trade_r=float(r_multiple.mean()),
    )


def compute_is_oos_metrics(trades: pd.DataFrame) -> ResultMetrics:
    """Compute in-sample and out-of-sample metrics from normalized trades."""

    _validate_trades(trades)
    insample = trades.loc[trades["period"] == "insample"]
    outsample = trades.loc[trades["period"] == "outsample"]
    return ResultMetrics(
        insample=compute_period_metrics(insample),
        outsample=compute_period_metrics(outsample),
    )


def compute_fixture_metrics(hypothesis_id: str) -> ResultMetrics:
    """Load fixture trades and compute deterministic IS/OOS metrics."""

    return compute_is_oos_metrics(load_fixture_trades(hypothesis_id))


def oos_degradation(sharpe_is: float, sharpe_oos: float) -> float:
    """Return OOS Sharpe degradation as a non-negative fraction."""

    if not math.isfinite(sharpe_is) or not math.isfinite(sharpe_oos):
        return math.inf
    if sharpe_is <= 0:
        return 0.0 if sharpe_oos >= sharpe_is else math.inf
    return max(0.0, (sharpe_is - sharpe_oos) / abs(sharpe_is))


def _trade_sharpe(pnl: np.ndarray) -> float:
    if len(pnl) < 2:
        return 0.0
    std = float(np.std(pnl, ddof=1))
    if std == 0:
        return math.inf if float(np.mean(pnl)) > 0 else 0.0
    return float(np.sqrt(len(pnl)) * float(np.mean(pnl)) / std)


def _max_drawdown(pnl: np.ndarray) -> float:
    equity = np.cumprod(1.0 + pnl)
    peaks = np.maximum.accumulate(np.insert(equity, 0, 1.0))[1:]
    drawdowns = (peaks - equity) / peaks
    return float(drawdowns.max(initial=0.0))


def _validate_trades(trades: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_TRADE_COLUMNS if col not in trades.columns]
    if missing:
        msg = f"trades CSV missing required columns: {missing}"
        raise ValueError(msg)
    if trades[REQUIRED_TRADE_COLUMNS].isnull().any().any():
        msg = "trades CSV contains empty values in required columns"
        raise ValueError(msg)
    if trades["trade_id"].duplicated().any():
        msg = "trade_id values must be unique"
        raise ValueError(msg)
    if not set(trades["period"]).issubset(VALID_PERIODS):
        msg = "period must be insample or outsample"
        raise ValueError(msg)
    if not set(trades["side"]).issubset(VALID_SIDES):
        msg = "side must be long or short"
        raise ValueError(msg)
    pnl = trades["pnl_pct"].astype(float)
    r_multiple = trades["r_multiple"].astype(float)
    if not np.isfinite(pnl).all() or not np.isfinite(r_multiple).all():
        msg = "pnl_pct and r_multiple must be finite"
        raise ValueError(msg)
    bool_values = {"true", "false", True, False}
    if not set(trades["has_stop_loss"]).issubset(bool_values):
        msg = "has_stop_loss must be boolean"
        raise ValueError(msg)
    if not set(trades["intraday"]).issubset(bool_values):
        msg = "intraday must be boolean"
        raise ValueError(msg)


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return value == "true"
