from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import settings
from shared.db.models import Base

_connect_args = {}
if settings.database_url.startswith("sqlite"):
    _connect_args = {}

engine = create_async_engine(settings.database_url, echo=False, connect_args=_connect_args)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Create tables if they don't exist yet (SQLite dev/demo path).

    Against real Supabase/Postgres, db/schema.sql is the source of truth and
    should be applied via the Supabase SQL editor / migration tooling instead.
    """
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope():
    async with SessionLocal() as session:
        yield session
