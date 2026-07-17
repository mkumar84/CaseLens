from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_session
from backend.app.schemas import ReportDraftOut
from shared.db.models import ReportDraft

router = APIRouter(prefix="/report-drafts", tags=["reports"])


@router.get("", response_model=list[ReportDraftOut])
async def list_report_drafts(case_file_id: str, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(ReportDraft).where(ReportDraft.case_file_id == case_file_id).order_by(ReportDraft.created_at)
        )
    ).scalars().all()
    return rows


@router.get("/{report_draft_id}", response_model=ReportDraftOut)
async def get_report_draft(report_draft_id: str, session: AsyncSession = Depends(get_session)):
    draft = await session.get(ReportDraft, report_draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="report draft not found")
    return draft
