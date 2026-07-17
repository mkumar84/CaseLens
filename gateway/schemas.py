from pydantic import BaseModel


class CreateTriageFlagRequest(BaseModel):
    case_file_id: str
    artifact_id: str
    rationale: str
    confidence_score: float
    status: str | None = None  # ignored server-side; TriageFlags always start pending


class ReadArtifactRequest(BaseModel):
    case_file_id: str
    triage_flag_id: str
    requesting_agent: str = "timeline-agent"


class CreateTimelineEntryRequest(BaseModel):
    case_file_id: str
    artifact_id: str
    event_timestamp: str
    event_description: str
    created_by_agent: str = "timeline-agent"


class ClaimInput(BaseModel):
    claim_id: str
    claim_text: str
    artifact_id: str | None = None  # None => uncited claim


class CreateReportDraftRequest(BaseModel):
    case_file_id: str
    content: str
    claims: list[ClaimInput]
    created_by_agent: str = "report-agent"


class TransitionReportStatusRequest(BaseModel):
    report_draft_id: str
    to_status: str
    requested_by_agent: str = "report-agent"


class GateResponse(BaseModel):
    allowed: bool
    request_id: str
    reason: str | None = None
    data: dict | list | None = None
    unsourced_claims: list | None = None
    rolled_back: bool = False
