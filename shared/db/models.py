import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CaseFile(Base):
    __tablename__ = "case_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | case_ready | closed


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_file_id: Mapped[str] = mapped_column(ForeignKey("case_files.id"))
    source_type: Mapped[str] = mapped_column(String(20))  # document | device | comms
    raw_content: Mapped[str] = mapped_column(Text)
    artifact_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class TriageFlag(Base):
    __tablename__ = "triage_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"))
    rationale: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class TimelineEntry(Base):
    __tablename__ = "timeline_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_file_id: Mapped[str] = mapped_column(ForeignKey("case_files.id"))
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"))
    event_timestamp: Mapped[datetime] = mapped_column()
    event_description: Mapped[str] = mapped_column(Text)
    created_by_agent: Mapped[str] = mapped_column(String(100), default="timeline-agent")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ReportDraft(Base):
    __tablename__ = "report_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_file_id: Mapped[str] = mapped_column(ForeignKey("case_files.id"))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list] = mapped_column(JSON, default=list)  # [{claim_id, artifact_id, claim_text}]
    citation_coverage_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | case_ready | blocked
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    case_file_id: Mapped[str | None] = mapped_column(ForeignKey("case_files.id"), nullable=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    target_entity: Mapped[str] = mapped_column(String(255))
    decision: Mapped[str] = mapped_column(String(10))  # allow | deny
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(default=utcnow)


class PolicyDecisionLog(Base):
    __tablename__ = "policy_decision_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    policy_name: Mapped[str] = mapped_column(String(100))
    request_summary: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(10))  # allow | deny
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str] = mapped_column(String(64))
    timestamp: Mapped[datetime] = mapped_column(default=utcnow)
