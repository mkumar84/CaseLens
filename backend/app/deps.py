from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.session import SessionLocal


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
