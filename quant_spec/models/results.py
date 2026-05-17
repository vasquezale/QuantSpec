"""Pydantic contracts for deterministic backtest results."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

HashString = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
HypothesisId = Annotated[str, Field(pattern=r"^HYP-\d{3}-[a-z0-9-]+$")]


class PeriodResult(BaseModel):
    """Persisted validation period metadata."""

    model_config = ConfigDict(extra="forbid")

    start: date
    end: date
    n_trades: int = Field(ge=0)


class ResultPeriods(BaseModel):
    """In-sample and out-of-sample result periods."""

    model_config = ConfigDict(extra="forbid")

    insample: PeriodResult
    outsample: PeriodResult


class PeriodMetrics(BaseModel):
    """Required deterministic metrics for a period."""

    model_config = ConfigDict(extra="forbid")

    sharpe: float
    win_rate: float = Field(ge=0, le=1)
    max_drawdown: float = Field(ge=0)
    profit_factor: float | None = Field(default=None, ge=0)
    n_trades: int = Field(ge=0)
    avg_trade_r: float


class ResultMetrics(BaseModel):
    """In-sample and out-of-sample metrics."""

    model_config = ConfigDict(extra="forbid")

    insample: PeriodMetrics
    outsample: PeriodMetrics


class RiskConstraintViolations(BaseModel):
    """Trades discarded while enforcing risk constraints."""

    model_config = ConfigDict(extra="forbid")

    discarded_trades: int = Field(ge=0)
    reasons: dict[str, int] = Field(default_factory=dict)


class BacktestResult(BaseModel):
    """Deterministic result artifact contract."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: HypothesisId
    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    brief_hash: HashString
    spec_hash: HashString
    executed_at: datetime | None = None
    data_source: str = Field(min_length=1)
    periods: ResultPeriods
    metrics: ResultMetrics
    risk_constraint_violations: RiskConstraintViolations
    result_hash: HashString
