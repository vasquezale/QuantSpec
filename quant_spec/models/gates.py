"""Pydantic contracts for quality gate evaluation."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from quant_spec.models.results import HashString, HypothesisId


class GateStatus(StrEnum):
    """Per-gate status."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


class GateSummary(StrEnum):
    """Overall gate report status."""

    PASS = "PASS"
    FAIL = "FAIL"


class GateOperator(StrEnum):
    """Supported gate comparisons."""

    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="


class GateCheck(BaseModel):
    """Single quality gate result."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    metric: float | None
    threshold: float
    op: GateOperator
    status: GateStatus


class GateReport(BaseModel):
    """Quality gate report artifact contract."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: HypothesisId
    result_hash: HashString
    gates_hash: HashString
    summary: GateSummary
    gates: list[GateCheck] = Field(min_length=1)
    first_failed: str | None = None
