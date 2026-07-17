from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.deps import get_session
from backend.app.schemas import CaseFileOut, CreateCaseFileRequest
from shared.db.models import CaseFile

router = APIRouter(prefix="/case-files", tags=["case-files"])


@router.get("", response_model=list[CaseFileOut])
async def list_case_files(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(CaseFile).order_by(CaseFile.created_at.desc()))).scalars().all()
    return rows


@router.post("", response_model=CaseFileOut)
async def create_case_file(req: CreateCaseFileRequest, session: AsyncSession = Depends(get_session)):
    case_file = CaseFile(name=req.name, status="open")
    session.add(case_file)
    await session.commit()
    await session.refresh(case_file)
    return case_file


@router.get("/{case_file_id}", response_model=CaseFileOut)
async def get_case_file(case_file_id: str, session: AsyncSession = Depends(get_session)):
    case_file = await session.get(CaseFile, case_file_id)
    if case_file is None:
        raise HTTPException(status_code=404, detail="case file not found")
    return case_file
