from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_session
from backend.app.schemas import AuditLogEntryOut, PolicyDecisionLogOut
from shared.db.models import AuditLogEntry, PolicyDecisionLog

router = APIRouter(tags=["audit"])


@router.get("/audit-log", response_model=list[AuditLogEntryOut])
async def list_audit_log(case_file_id: str | None = None, session: AsyncSession = Depends(get_session)):
    query = select(AuditLogEntry).order_by(AuditLogEntry.timestamp)
    if case_file_id:
        query = query.where(AuditLogEntry.case_file_id == case_file_id)
    rows = (await session.execute(query)).scalars().all()
    return rows


@router.get("/policy-decisions", response_model=list[PolicyDecisionLogOut])
async def list_policy_decisions(
    policy_name: str | None = None, decision: str | None = None, session: AsyncSession = Depends(get_session)
):
    query = select(PolicyDecisionLog).order_by(PolicyDecisionLog.timestamp)
    if policy_name:
        query = query.where(PolicyDecisionLog.policy_name == policy_name)
    if decision:
        query = query.where(PolicyDecisionLog.decision == decision)
    rows = (await session.execute(query)).scalars().all()
    return rows
