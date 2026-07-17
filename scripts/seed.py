"""Seed one synthetic mixed CaseFile with its artifacts.

Usage: python -m scripts.seed
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.seed_data import ARTIFACTS, CASE_FILE_NAME
from shared.db.models import Artifact, CaseFile
from shared.db.session import init_db, session_scope


async def seed() -> str:
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
        print(f"Seeded case file {case_file.id} ({case_file.name}) with {len(ARTIFACTS)} artifacts.")
        return case_file.id


if __name__ == "__main__":
    asyncio.run(seed())
