"""Pydantic contract for a decision record."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

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
