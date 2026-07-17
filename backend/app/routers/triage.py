from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_session
from backend.app.schemas import ReviewTriageFlagRequest, TriageFlagOut
from shared.db.models import Artifact, AuditLogEntry, TriageFlag

router = APIRouter(prefix="/triage-flags", tags=["triage"])


@router.get("", response_model=list[TriageFlagOut])
async def list_triage_flags(
    case_file_id: str, status: str | None = None, session: AsyncSession = Depends(get_session)
):
    query = select(TriageFlag).join(Artifact, Artifact.id == TriageFlag.artifact_id).where(
        Artifact.case_file_id == case_file_id
    )
    if status:
        query = query.where(TriageFlag.status == status)
    rows = (await session.execute(query.order_by(TriageFlag.created_at))).scalars().all()
    return rows


@router.post("/{flag_id}/review", response_model=TriageFlagOut)
async def review_triage_flag(
    flag_id: str, req: ReviewTriageFlagRequest, session: AsyncSession = Depends(get_session)
):
    """Human-only action: approve or reject a Triage Agent proposal. Not
    routed through the gateway (this isn't an agent action), but still
    recorded to AuditLogEntry directly for traceability in the demo's
    decision trail.
    """
    if req.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'rejected'")

    flag = await session.get(TriageFlag, flag_id)
    if flag is None:
        raise HTTPException(status_code=404, detail="triage flag not found")

    flag.status = req.decision
    flag.reviewed_by = req.reviewed_by
    flag.reviewed_at = datetime.now(timezone.utc)

    artifact = await session.get(Artifact, flag.artifact_id)
    session.add(
        AuditLogEntry(
            case_file_id=artifact.case_file_id if artifact else None,
            actor=req.reviewed_by,
            action=f"human-{req.decision}-triage-flag",
            target_entity=f"triage_flag:{flag_id}",
            decision="allow",
            reason=None,
            request_id=f"human-review-{flag_id}",
        )
    )

    await session.commit()
    await session.refresh(flag)
    return flag
