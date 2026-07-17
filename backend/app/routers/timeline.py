from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_session
from backend.app.schemas import TimelineEntryOut
from shared.db.models import TimelineEntry

router = APIRouter(prefix="/timeline-entries", tags=["timeline"])


@router.get("", response_model=list[TimelineEntryOut])
async def list_timeline_entries(case_file_id: str, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(TimelineEntry)
            .where(TimelineEntry.case_file_id == case_file_id)
            .order_by(TimelineEntry.event_timestamp)
        )
    ).scalars().all()
    return rows
