from datetime import date

from quant_spec.models.results import (
    BacktestResult,
    PeriodResult,
    ResultPeriods,
    RiskConstraintViolations,
)
from quant_spec.validation.metrics import compute_fixture_metrics

VALID_HASH = "sha256:" + "b" * 64


def result_for_fixture(hypothesis_id: str) -> BacktestResult:
    metrics = compute_fixture_metrics(hypothesis_id)
    return BacktestResult(
        hypothesis_id=hypothesis_id,
        engine="python_demo_engine",
        engine_version="0.1.0",
        brief_hash=VALID_HASH,
        spec_hash=VALID_HASH,
        data_source="fixture",
        periods=ResultPeriods(
            insample=PeriodResult(
                start=date(2020, 1, 1),
                end=date(2020, 12, 31),
                n_trades=metrics.insample.n_trades,
            ),
            outsample=PeriodResult(
                start=date(2021, 1, 1),
                end=date(2021, 12, 31),
                n_trades=metrics.outsample.n_trades,
            ),
        ),
        metrics=metrics,
        risk_constraint_violations=RiskConstraintViolations(
            discarded_trades=0,
            reasons={},
        ),
        result_hash=VALID_HASH,
    )
