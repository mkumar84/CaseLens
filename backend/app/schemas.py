from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CaseFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    created_at: datetime
    status: str


class CreateCaseFileRequest(BaseModel):
    name: str


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_file_id: str
    source_type: str
    raw_content: str
    artifact_metadata: dict
    created_at: datetime


class TriageFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    artifact_id: str
    rationale: str
    confidence_score: float
    status: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ReviewTriageFlagRequest(BaseModel):
    decision: str  # approved | rejected
    reviewed_by: str


class TimelineEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_file_id: str
    artifact_id: str
    event_timestamp: datetime
    event_description: str
    created_by_agent: str
    created_at: datetime


class ReportDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_file_id: str
    content: str
    citations: list
    citation_coverage_pct: float
    status: str
    created_at: datetime
    updated_at: datetime


class AuditLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_file_id: str | None
    actor: str
    action: str
    target_entity: str
    decision: str
    reason: str | None
    request_id: str
    timestamp: datetime
    seq: int
    prev_hash: str
    entry_hash: str


class PolicyDecisionLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    policy_name: str
    request_summary: str
    decision: str
    reason: str | None
    request_id: str
    timestamp: datetime
