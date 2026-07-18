from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.app.routers import agents, artifacts, audit, case_files, dev, reports, timeline, triage
from scripts.seed import seed_all
from shared.db.models import CaseFile
from shared.db.session import init_db, session_scope


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with session_scope() as session:
        result = await session.execute(select(CaseFile.id).limit(1))
        has_data = result.scalar_one_or_none() is not None
    if not has_data:
        # Deployed demo has no manual seeding step (Railway CLI access
        # isn't a fair prerequisite for someone just pulling up the live
        # URL). Only fires against a genuinely empty DB, so redeploys
        # against an already-seeded database don't create duplicates.
        # Seeds every demo scenario in db/seed_data.py, not just one, so a
        # fresh deploy shows range rather than a single case.
        await seed_all()
    yield


app = FastAPI(title="CaseLens API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(case_files.router)
app.include_router(artifacts.router)
app.include_router(triage.router)
app.include_router(timeline.router)
app.include_router(reports.router)
app.include_router(audit.router)
app.include_router(agents.router)
app.include_router(dev.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
