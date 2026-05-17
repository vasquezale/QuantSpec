"""Fixed quality gates for deterministic QuantSpec results."""

from __future__ import annotations

import math

from quant_spec.io.storage import canonical_sha256, stable_projection
from quant_spec.models.gates import (
    GateCheck,
    GateOperator,
    GateReport,
    GateStatus,
    GateSummary,
)
from quant_spec.models.results import BacktestResult
from quant_spec.validation.metrics import oos_degradation

GATE_SHARPE_IS_MIN = 0.0
GATE_SHARPE_OOS_MIN = 1.5
GATE_WIN_RATE_OOS_MIN = 0.55
GATE_MAX_DRAWDOWN_MAX = 0.20
GATE_OOS_DEGRADATION_MAX = 0.20


def evaluate_gates(result: BacktestResult) -> GateReport:
    """Evaluate gates in order, skipping remaining gates after the first fail."""

    metrics = result.metrics
    gate_specs = [
        (
            "G1_sharpe_is",
            _metric(metrics.insample, "sharpe"),
            GATE_SHARPE_IS_MIN,
            GateOperator.GREATER_EQUAL,
        ),
        (
            "G2_sharpe_oos",
            _metric(metrics.outsample, "sharpe"),
            GATE_SHARPE_OOS_MIN,
            GateOperator.GREATER_EQUAL,
        ),
        (
            "G3_winrate_oos",
            _metric(metrics.outsample, "win_rate"),
            GATE_WIN_RATE_OOS_MIN,
            GateOperator.GREATER_EQUAL,
        ),
        (
            "G4_max_drawdown",
            _metric(metrics.outsample, "max_drawdown"),
            GATE_MAX_DRAWDOWN_MAX,
            GateOperator.LESS_EQUAL,
        ),
        (
            "G5_oos_degradation",
            _degradation_metric(result),
            GATE_OOS_DEGRADATION_MAX,
            GateOperator.LESS_EQUAL,
        ),
    ]

    gates: list[GateCheck] = []
    first_failed: str | None = None
    for gate_id, metric, threshold, op in gate_specs:
        if first_failed is not None:
            status = GateStatus.SKIPPED
        else:
            status = _evaluate_status(metric, threshold, op)
            if status == GateStatus.FAIL:
                first_failed = gate_id
        gates.append(
            GateCheck(
                id=gate_id,
                metric=metric if metric is not None and math.isfinite(metric) else None,
                threshold=threshold,
                op=op,
                status=status,
            )
        )

    summary = GateSummary.FAIL if first_failed else GateSummary.PASS
    report = GateReport(
        hypothesis_id=result.hypothesis_id,
        result_hash=result.result_hash,
        gates_hash="sha256:" + "0" * 64,
        summary=summary,
        gates=gates,
        first_failed=first_failed,
    )
    return report.model_copy(
        update={"gates_hash": canonical_sha256(stable_projection(report))}
    )


def _evaluate_status(
    metric: float | None,
    threshold: float,
    op: GateOperator,
) -> GateStatus:
    if metric is None or not math.isfinite(metric):
        return GateStatus.FAIL
    if op == GateOperator.GREATER_EQUAL:
        return GateStatus.PASS if metric >= threshold else GateStatus.FAIL
    if op == GateOperator.LESS_EQUAL:
        return GateStatus.PASS if metric <= threshold else GateStatus.FAIL
    msg = f"unsupported gate operator: {op}"
    raise ValueError(msg)


def _metric(obj: object, name: str) -> float | None:
    value = getattr(obj, name, None)
    if value is None:
        return None
    return float(value)


def _degradation_metric(result: BacktestResult) -> float | None:
    sharpe_is = _metric(result.metrics.insample, "sharpe")
    sharpe_oos = _metric(result.metrics.outsample, "sharpe")
    if sharpe_is is None or sharpe_oos is None:
        return None
    return oos_degradation(sharpe_is, sharpe_oos)
