from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import agents, artifacts, audit, case_files, reports, timeline, triage
from shared.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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


@app.get("/health")
async def health():
    return {"status": "ok"}
