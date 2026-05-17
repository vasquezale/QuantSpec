"""Deterministic offline backtesting engine for fixture demos."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from quant_spec.io.storage import ArtifactStorage
from quant_spec.models.brief import HypothesisBrief
from quant_spec.models.results import (
    BacktestResult,
    PeriodResult,
    ResultPeriods,
    RiskConstraintViolations,
)
from quant_spec.validation.metrics import (
    compute_is_oos_metrics,
    fixture_trades_path,
    load_trades_csv,
)

ENGINE_NAME = "python_demo_engine"
ENGINE_VERSION = "0.1.0"


def run_python_demo_engine(
    brief: HypothesisBrief,
    spec_path: Path,
    storage: ArtifactStorage,
) -> BacktestResult:
    """Run the deterministic fixture engine and persist result artifacts."""

    trades = load_trades_csv(_resolve_trades_path(brief, storage))
    filtered_trades, violations = apply_risk_constraints(trades, brief)
    metrics = compute_is_oos_metrics(filtered_trades)
    result = BacktestResult(
        hypothesis_id=brief.id,
        engine=ENGINE_NAME,
        engine_version=ENGINE_VERSION,
        brief_hash=storage.hash_artifact(brief),
        spec_hash=storage.hash_file(spec_path),
        executed_at=datetime.now(UTC),
        data_source=brief.data.source.value,
        periods=ResultPeriods(
            insample=PeriodResult(
                start=brief.periods.insample.start,
                end=brief.periods.insample.end,
                n_trades=metrics.insample.n_trades,
            ),
            outsample=PeriodResult(
                start=brief.periods.outsample.start,
                end=brief.periods.outsample.end,
                n_trades=metrics.outsample.n_trades,
            ),
        ),
        metrics=metrics,
        risk_constraint_violations=violations,
        result_hash="sha256:" + "0" * 64,
    )
    result = result.model_copy(update={"result_hash": storage.hash_artifact(result)})
    storage.write_json(brief.id, "results.json", result)
    storage.write_text(brief.id, "results.md", _results_markdown(result))
    return result


def apply_risk_constraints(
    trades: pd.DataFrame,
    brief: HypothesisBrief,
) -> tuple[pd.DataFrame, RiskConstraintViolations]:
    """Filter trades that violate generic demo risk constraints."""

    filtered = trades.copy()
    reasons: Counter[str] = Counter()
    if brief.risk_constraints.must_have_stop_loss:
        mask = filtered["has_stop_loss"]
        reasons["missing_stop_loss"] += int((~mask).sum())
        filtered = filtered.loc[mask]
    if brief.risk_constraints.intraday_only:
        mask = filtered["intraday"]
        reasons["not_intraday"] += int((~mask).sum())
        filtered = filtered.loc[mask]

    max_by_daily_risk = int(
        brief.risk_constraints.max_daily_risk_pct
        // brief.risk_constraints.risk_per_trade_pct
    )
    max_trades_per_day = min(
        brief.risk_constraints.max_trades_per_day,
        max_by_daily_risk,
    )
    if max_trades_per_day <= 0:
        reasons["daily_risk_limit"] += int(len(filtered))
        filtered = filtered.iloc[0:0]
    else:
        filtered = filtered.sort_values(["open_time_utc", "trade_id"]).copy()
        open_dates = filtered["open_time_utc"].dt.date
        daily_order = filtered.groupby(open_dates).cumcount()
        mask = daily_order < max_trades_per_day
        reasons["max_trades_per_day"] += int((~mask).sum())
        filtered = filtered.loc[mask]

    filtered = filtered.sort_values("trade_id").reset_index(drop=True)
    return filtered, RiskConstraintViolations(
        discarded_trades=sum(reasons.values()),
        reasons={key: count for key, count in sorted(reasons.items()) if count},
    )


def _resolve_trades_path(brief: HypothesisBrief, storage: ArtifactStorage) -> Path:
    root_relative_path = storage.root / brief.data.path
    if root_relative_path.exists():
        return root_relative_path
    direct_path = Path(brief.data.path)
    if direct_path.exists():
        return direct_path
    return fixture_trades_path(brief.id)


def _results_markdown(result: BacktestResult) -> str:
    return "\n".join(
        [
            f"# Results: {result.hypothesis_id}",
            "",
            f"- Engine: {result.engine} {result.engine_version}",
            f"- Result hash: {result.result_hash}",
            (
                "- IS: "
                f"Sharpe {result.metrics.insample.sharpe:.2f}, "
                f"win rate {result.metrics.insample.win_rate:.2%}, "
                f"max drawdown {result.metrics.insample.max_drawdown:.2%}"
            ),
            (
                "- OOS: "
                f"Sharpe {result.metrics.outsample.sharpe:.2f}, "
                f"win rate {result.metrics.outsample.win_rate:.2%}, "
                f"max drawdown {result.metrics.outsample.max_drawdown:.2%}"
            ),
            "",
        ]
    )
