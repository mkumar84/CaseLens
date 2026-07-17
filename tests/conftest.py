import os
import sys
import tempfile
from pathlib import Path

# Must happen before any `shared.config` / `shared.db.session` import (theirs
# or a fixture's), since Settings reads DATABASE_URL once at import time.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="caselens_test_")
_TEST_DB_PATH = Path(_TEST_DB_DIR) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB_PATH}"
os.environ.pop("ANTHROPIC_API_KEY", None)  # force the offline heuristic path in tests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from db.seed_data import ARTIFACTS, CASE_FILE_NAME
from shared.db.models import Artifact, CaseFile
from shared.db.session import init_db, session_scope


@pytest_asyncio.fixture
async def seeded_case_file_id() -> str:
    await init_db()
    async with session_scope() as session:
        case_file = CaseFile(name=CASE_FILE_NAME, status="open")
        session.add(case_file)
        await session.flush()
        for artifact in ARTIFACTS:
            session.add(
                Artifact(
                    case_file_id=case_file.id,
                    source_type=artifact["source_type"],
                    raw_content=artifact["raw_content"],
                    artifact_metadata=artifact["metadata"],
                )
            )
        await session.commit()
        return case_file.id


@pytest_asyncio.fixture
async def gateway_client():
    from gateway.main import app as gateway_app

    transport = ASGITransport(app=gateway_app)
    async with AsyncClient(transport=transport, base_url="http://gateway.local") as client:
        yield client


@pytest_asyncio.fixture
async def backend_client():
    from backend.app.main import app as backend_app

    transport = ASGITransport(app=backend_app)
    async with AsyncClient(transport=transport, base_url="http://backend.local") as client:
        yield client


@pytest_asyncio.fixture
async def wire_agents_to_gateway():
    """Points agents/gateway_client.py at the gateway's in-process ASGI app
    instead of a real socket, so agent-module tests exercise the real
    agents/*.py code paths without needing a running uvicorn process."""
    import agents.gateway_client as gateway_client
    from gateway.main import app as gateway_app

    gateway_client._set_transport_override(ASGITransport(app=gateway_app))
    yield
    gateway_client._set_transport_override(None)
