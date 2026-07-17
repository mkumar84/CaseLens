"""agentgateway control plane (CaseLens emulation).

Every endpoint here is the *only* way an agent process can touch case data.
Agents hold no Supabase/Postgres credentials at all — see README.md for why
that's the property that makes the policy gates provably independent of
agent behavior, rather than app-code checks an agent could just skip.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from sqlalchemy import select

from gateway.action_executor import execute_governed_action_safe
from gateway.policy_engine import engine
from gateway.schemas import (
    CreateReportDraftRequest,
    CreateTimelineEntryRequest,
    CreateTriageFlagRequest,
    GateResponse,
    ReadArtifactRequest,
    TransitionReportStatusRequest,
)
from shared.db.models import Artifact, ReportDraft, TimelineEntry, TriageFlag
from shared.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="CaseLens agentgateway", version="0.1.0", lifespan=lifespan)


def _gate_response(result) -> GateResponse:
    return GateResponse(
        allowed=result.allowed,
        request_id=result.request_id,
        reason=result.reason,
        data=result.data,
        unsourced_claims=result.unsourced_claims,
        rolled_back=result.rolled_back,
    )


@app.post("/gateway/artifacts/list", response_model=GateResponse)
async def list_artifacts_for_triage(case_file_id: str, _force_audit_failure: bool = False):
    """Triage Agent's designated input: raw artifacts for its CaseFile.

    Not resource-gated (Triage's own domain), but still routed through the
    gateway and still subject to Policy 3 (every action is audited).
    """

    async def perform(session):
        rows = (
            await session.execute(select(Artifact).where(Artifact.case_file_id == case_file_id))
        ).scalars().all()
        return [
            {
                "id": a.id,
                "source_type": a.source_type,
                "raw_content": a.raw_content,
                "metadata": a.artifact_metadata,
            }
            for a in rows
        ]

    result = await execute_governed_action_safe(
        actor="triage-agent",
        action="list-artifacts",
        target_entity=f"case_file:{case_file_id}",
        case_file_id=case_file_id,
        request_summary=f"triage-agent list artifacts for case_file={case_file_id}",
        perform=perform,
        _force_audit_failure=_force_audit_failure,
    )
    return _gate_response(result)


@app.post("/gateway/triage/create-flag", response_model=GateResponse)
async def create_triage_flag(req: CreateTriageFlagRequest, _force_audit_failure: bool = False):
    """Triage Agent output. `status` is never taken from the request body —
    server-enforced pending, per the Triage Agent's prompt-discipline
    constraint (it must never assign 'approved' itself)."""

    async def perform(session):
        flag = TriageFlag(
            artifact_id=req.artifact_id,
            rationale=req.rationale,
            confidence_score=req.confidence_score,
            status="pending",
        )
        session.add(flag)
        await session.flush()
        return {"id": flag.id, "artifact_id": flag.artifact_id, "status": flag.status}

    result = await execute_governed_action_safe(
        actor="triage-agent",
        action="create-triage-flag",
        target_entity=f"artifact:{req.artifact_id}",
        case_file_id=req.case_file_id,
        request_summary=f"triage-agent create TriageFlag for artifact={req.artifact_id}",
        perform=perform,
        _force_audit_failure=_force_audit_failure,
    )
    return _gate_response(result)


@app.post("/gateway/timeline/list-approved-flags", response_model=GateResponse)
async def list_approved_flags(case_file_id: str, _force_audit_failure: bool = False):
    """Discovery step for the Timeline Agent: which TriageFlags are approved
    for this case. Server-side filtered to status == 'approved' — the
    gateway never hands back pending/rejected flag ids here, and Policy 1
    re-checks status again at the actual read-artifact call regardless."""

    async def perform(session):
        rows = (
            await session.execute(
                select(TriageFlag)
                .join(Artifact, Artifact.id == TriageFlag.artifact_id)
                .where(Artifact.case_file_id == case_file_id, TriageFlag.status == "approved")
            )
        ).scalars().all()
        return [
            {"triage_flag_id": f.id, "artifact_id": f.artifact_id, "status": f.status}
            for f in rows
        ]

    result = await execute_governed_action_safe(
        actor="timeline-agent",
        action="list-approved-flags",
        target_entity=f"case_file:{case_file_id}",
        case_file_id=case_file_id,
        request_summary=f"timeline-agent list approved flags for case_file={case_file_id}",
        perform=perform,
        _force_audit_failure=_force_audit_failure,
    )
    return _gate_response(result)


@app.post("/gateway/timeline/read-artifact", response_model=GateResponse)
async def timeline_read_artifact(req: ReadArtifactRequest, _force_audit_failure: bool = False):
    """Policy 1 enforcement point. Fetches the TriageFlag + Artifact itself
    (the agent never sees them until/unless this returns allowed=True), so a
    caller cannot forge an 'approved' resource — the gateway is the one
    reading ground truth from the database.
    """

    flag_row = None
    artifact_row = None

    async def perform(session):
        nonlocal flag_row, artifact_row
        flag_row = await session.get(TriageFlag, req.triage_flag_id)
        if flag_row is None:
            raise HTTPException(status_code=404, detail="triage_flag not found")
        artifact_row = await session.get(Artifact, flag_row.artifact_id)
        return {
            "artifact_id": artifact_row.id,
            "source_type": artifact_row.source_type,
            "raw_content": artifact_row.raw_content,
            "metadata": artifact_row.artifact_metadata,
            "triage_flag_id": flag_row.id,
            "triage_flag_status": flag_row.status,
        }

    # Fetch the gating resource *before* the gated perform() runs, using a
    # throwaway read so policy evaluation and the actual data return agree.
    from shared.db.session import SessionLocal

    async with SessionLocal() as probe_session:
        probe_flag = await probe_session.get(TriageFlag, req.triage_flag_id)
        if probe_flag is None:
            raise HTTPException(status_code=404, detail="triage_flag not found")
        gating_resource = {"triage_flag": {"status": probe_flag.status}}

    result = await execute_governed_action_safe(
        actor=req.requesting_agent,
        action="read-artifact",
        target_entity=f"triage_flag:{req.triage_flag_id}",
        case_file_id=req.case_file_id,
        request_summary=(
            f"{req.requesting_agent} read-artifact via triage_flag={req.triage_flag_id} "
            f"(status={gating_resource['triage_flag']['status']})"
        ),
        perform=perform,
        gating_policy="require-human-approval",
        gating_resource=gating_resource,
        _force_audit_failure=_force_audit_failure,
    )
    return _gate_response(result)


@app.post("/gateway/timeline/create-entry", response_model=GateResponse)
async def create_timeline_entry(req: CreateTimelineEntryRequest, _force_audit_failure: bool = False):
    async def perform(session):
        entry = TimelineEntry(
            case_file_id=req.case_file_id,
            artifact_id=req.artifact_id,
            event_timestamp=datetime.fromisoformat(req.event_timestamp),
            event_description=req.event_description,
            created_by_agent=req.created_by_agent,
        )
        session.add(entry)
        await session.flush()
        return {"id": entry.id, "event_description": entry.event_description}

    result = await execute_governed_action_safe(
        actor=req.created_by_agent,
        action="create-timeline-entry",
        target_entity=f"artifact:{req.artifact_id}",
        case_file_id=req.case_file_id,
        request_summary=f"{req.created_by_agent} create TimelineEntry for artifact={req.artifact_id}",
        perform=perform,
        _force_audit_failure=_force_audit_failure,
    )
    return _gate_response(result)


@app.post("/gateway/report/list-case-data", response_model=GateResponse)
async def list_case_data_for_report(case_file_id: str, _force_audit_failure: bool = False):
    """Report Agent's input: approved TriageFlag + TimelineEntry data for a
    CaseFile. Every TriageFlag row is fetched and re-evaluated against
    Policy 1 here (not just filtered by a WHERE clause) so the same CEL gate
    that protects the Timeline Agent's reads is the authority for what the
    Report Agent may see too — not a second, looser code path."""

    async def perform(session):
        flag_rows = (
            await session.execute(
                select(TriageFlag, Artifact)
                .join(Artifact, Artifact.id == TriageFlag.artifact_id)
                .where(Artifact.case_file_id == case_file_id)
            )
        ).all()

        approved_artifacts = []
        for flag, artifact in flag_rows:
            if engine.evaluate("require-human-approval", resource={"triage_flag": {"status": flag.status}}):
                approved_artifacts.append(
                    {
                        "triage_flag_id": flag.id,
                        "artifact_id": artifact.id,
                        "source_type": artifact.source_type,
                        "raw_content": artifact.raw_content,
                        "rationale": flag.rationale,
                    }
                )

        timeline_rows = (
            await session.execute(
                select(TimelineEntry)
                .where(TimelineEntry.case_file_id == case_file_id)
                .order_by(TimelineEntry.event_timestamp)
            )
        ).scalars().all()
        timeline = [
            {
                "id": t.id,
                "artifact_id": t.artifact_id,
                "event_timestamp": t.event_timestamp.isoformat(),
                "event_description": t.event_description,
            }
            for t in timeline_rows
        ]
        return {"approved_artifacts": approved_artifacts, "timeline_entries": timeline}

    result = await execute_governed_action_safe(
        actor="report-agent",
        action="list-case-data",
        target_entity=f"case_file:{case_file_id}",
        case_file_id=case_file_id,
        request_summary=f"report-agent list approved case data for case_file={case_file_id}",
        perform=perform,
        _force_audit_failure=_force_audit_failure,
    )
    return _gate_response(result)


@app.post("/gateway/report/create-draft", response_model=GateResponse)
async def create_report_draft(req: CreateReportDraftRequest, _force_audit_failure: bool = False):
    """Citation coverage is computed here, server-side, from the claims
    list — never trusted from the agent's own self-reported percentage.
    A misbehaving agent that omits citations on some claims still gets an
    honestly-computed (lower) coverage number.
    """

    total = len(req.claims)
    cited = sum(1 for c in req.claims if c.artifact_id)
    coverage_pct = round((cited / total) * 100, 2) if total else 0.0
    citations = [c.model_dump() for c in req.claims]

    async def perform(session):
        draft = ReportDraft(
            case_file_id=req.case_file_id,
            content=req.content,
            citations=citations,
            citation_coverage_pct=coverage_pct,
            status="draft",
        )
        session.add(draft)
        await session.flush()
        return {
            "id": draft.id,
            "citation_coverage_pct": float(draft.citation_coverage_pct),
            "status": draft.status,
        }

    result = await execute_governed_action_safe(
        actor=req.created_by_agent,
        action="create-report-draft",
        target_entity=f"case_file:{req.case_file_id}",
        case_file_id=req.case_file_id,
        request_summary=f"{req.created_by_agent} create ReportDraft for case_file={req.case_file_id}",
        perform=perform,
        _force_audit_failure=_force_audit_failure,
    )
    return _gate_response(result)


@app.post("/gateway/report/transition-status", response_model=GateResponse)
async def transition_report_status(req: TransitionReportStatusRequest, _force_audit_failure: bool = False):
    """Policy 2 enforcement point. citation_coverage_pct is read from the
    database (set at draft-creation time by the gateway itself), never from
    the request, so an agent cannot claim 100% to force the transition."""

    from shared.db.session import SessionLocal

    async with SessionLocal() as probe_session:
        draft = await probe_session.get(ReportDraft, req.report_draft_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="report_draft not found")
        case_file_id = draft.case_file_id
        gating_resource = {"citation_coverage_pct": float(draft.citation_coverage_pct)}
        unsourced = (
            [c for c in draft.citations if not c.get("artifact_id")]
            if req.to_status == "case_ready"
            else None
        )

    async def perform(session):
        row = await session.get(ReportDraft, req.report_draft_id)
        row.status = req.to_status
        await session.flush()
        return {"id": row.id, "status": row.status}

    gating_policy = "require-full-citation-coverage" if req.to_status == "case_ready" else None

    result = await execute_governed_action_safe(
        actor=req.requested_by_agent,
        action="transition-report-status",
        target_entity=f"report_draft:{req.report_draft_id}",
        case_file_id=case_file_id,
        request_summary=(
            f"{req.requested_by_agent} transition ReportDraft {req.report_draft_id} -> {req.to_status} "
            f"(coverage={gating_resource['citation_coverage_pct']}%)"
        ),
        perform=perform,
        gating_policy=gating_policy,
        gating_resource=gating_resource,
        unsourced_claims=unsourced,
        _force_audit_failure=_force_audit_failure,
    )

    if gating_policy and not result.allowed and not result.rolled_back:
        # The requested case_ready transition was correctly denied by
        # Policy 2. Separately (and always-allowed — Policy 2 does not
        # govern this), mark the draft 'blocked' so the failed attempt is
        # visible rather than silently leaving it in 'draft'. This is its
        # own audited action.
        async def mark_blocked(session):
            row = await session.get(ReportDraft, req.report_draft_id)
            row.status = "blocked"
            await session.flush()
            return {"id": row.id, "status": row.status}

        await execute_governed_action_safe(
            actor="agentgateway",
            action="mark-report-blocked",
            target_entity=f"report_draft:{req.report_draft_id}",
            case_file_id=case_file_id,
            request_summary=f"mark ReportDraft {req.report_draft_id} blocked after denied case_ready transition",
            perform=mark_blocked,
        )

    return _gate_response(result)


@app.get("/gateway/health")
async def health():
    return {"status": "ok"}
