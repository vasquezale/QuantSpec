"""Pydantic contract for a hypothesis brief."""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetClass(StrEnum):
    """Supported public demo asset classes."""

    DEMO = "demo"
    EQUITY = "equity"
    FUTURES = "futures"
    FOREX = "forex"
    CRYPTO = "crypto"


class DataSource(StrEnum):
    """Supported data source labels."""

    FIXTURE = "fixture"
    PUBLIC = "public"


class Market(BaseModel):
    """Market metadata for a brief."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    asset_class: AssetClass
    pip_size: float = Field(gt=0)


class RiskConstraints(BaseModel):
    """Risk limits applied before metric calculation."""

    model_config = ConfigDict(extra="forbid")

    max_daily_risk_pct: float = Field(gt=0)
    risk_per_trade_pct: float = Field(gt=0)
    max_trades_per_day: int = Field(ge=1)
    must_have_stop_loss: bool
    intraday_only: bool


class PeriodWindow(BaseModel):
    """Inclusive date window."""

    model_config = ConfigDict(extra="forbid")

    start: date
    end: date

    @model_validator(mode="after")
    def validate_order(self) -> "PeriodWindow":
        if self.start > self.end:
            msg = "period start must be before or equal to end"
            raise ValueError(msg)
        return self


class Periods(BaseModel):
    """In-sample and out-of-sample validation windows."""

    model_config = ConfigDict(extra="forbid")

    insample: PeriodWindow
    outsample: PeriodWindow

    @model_validator(mode="after")
    def validate_split(self) -> "Periods":
        if self.insample.end >= self.outsample.start:
            msg = "insample.end must be before outsample.start"
            raise ValueError(msg)
        return self


class BriefData(BaseModel):
    """Data reference for a brief."""

    model_config = ConfigDict(extra="forbid")

    source: DataSource
    path: str = Field(min_length=1)


class HypothesisBrief(BaseModel):
    """Machine-readable hypothesis brief."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(pattern=r"^HYP-\d{3}-[a-z0-9-]+$")]
    created_at: datetime
    author: str = Field(min_length=1)
    market: Market
    timeframe: str = Field(min_length=1)
    central_hypothesis: str = Field(min_length=1)
    risk_constraints: RiskConstraints
    periods: Periods
    data: BriefData
    notes: str = ""
