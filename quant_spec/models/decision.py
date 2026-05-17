"""Pydantic contract for a decision record."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_spec.models.gates import GateSummary
from quant_spec.models.results import HashString, HypothesisId


class DecisionStatus(StrEnum):
    """Final hypothesis decision status."""

    CANDIDATE_FOR_REVIEW = "CANDIDATE_FOR_REVIEW"
    CLOSED_BY_GATE = "CLOSED_BY_GATE"


class DecisionRecord(BaseModel):
    """Machine-readable decision metadata."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: HypothesisId
    status: DecisionStatus
    decided_at: datetime | None = None
    decided_by: str = Field(min_length=1)
    gates_summary: GateSummary
    report_hash: HashString

    @model_validator(mode="after")
    def validate_decision_consistency(self) -> "DecisionRecord":
        if (
            self.status == DecisionStatus.CANDIDATE_FOR_REVIEW
            and self.gates_summary != GateSummary.PASS
        ):
            msg = "CANDIDATE_FOR_REVIEW requires PASS gates_summary"
            raise ValueError(msg)
        if (
            self.status == DecisionStatus.CLOSED_BY_GATE
            and self.gates_summary != GateSummary.FAIL
        ):
            msg = "CLOSED_BY_GATE requires FAIL gates_summary"
            raise ValueError(msg)
        return self
