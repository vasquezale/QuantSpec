"""Pydantic contracts for quality gate evaluation."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

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

    @model_validator(mode="after")
    def validate_gate_consistency(self) -> "GateReport":
        failed_ids = [gate.id for gate in self.gates if gate.status == GateStatus.FAIL]
        if self.summary == GateSummary.PASS:
            if self.first_failed is not None:
                msg = "passing gate reports cannot have first_failed"
                raise ValueError(msg)
            if any(gate.status != GateStatus.PASS for gate in self.gates):
                msg = "passing gate reports require all gates to pass"
                raise ValueError(msg)
            return self

        if not failed_ids:
            msg = "failing gate reports require at least one failed gate"
            raise ValueError(msg)
        if self.first_failed not in failed_ids:
            msg = "first_failed must reference a failed gate"
            raise ValueError(msg)

        first_failed_index = next(
            index
            for index, gate in enumerate(self.gates)
            if gate.id == self.first_failed
        )
        for gate in self.gates[first_failed_index + 1 :]:
            if gate.status != GateStatus.SKIPPED:
                msg = "gates after first_failed must be skipped"
                raise ValueError(msg)
        return self
