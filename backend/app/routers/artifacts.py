from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_session
from backend.app.schemas import ArtifactOut
from shared.db.models import Artifact

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactOut])
async def list_artifacts(case_file_id: str, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Artifact).where(Artifact.case_file_id == case_file_id).order_by(Artifact.created_at)
        )
    ).scalars().all()
    return rows
