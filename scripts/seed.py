"""Seed synthetic mixed CaseFiles with their artifacts.

Usage:
    python -m scripts.seed          # seed all scenarios
    python -m scripts.seed 1        # seed only CASES[1]
"""

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.seed_data import CASES
from shared.db.models import Artifact, CaseFile
from shared.db.session import init_db, session_scope


async def seed_one(index: int | None = None) -> str:
    """Seed a single case scenario. Random choice from CASES if index is None."""
    await init_db()
    scenario = CASES[index] if index is not None else random.choice(CASES)
    async with session_scope() as session:
        case_file = CaseFile(name=scenario["name"], status="open")
        session.add(case_file)
        await session.flush()

        for artifact in scenario["artifacts"]:
            session.add(
                Artifact(
                    case_file_id=case_file.id,
                    source_type=artifact["source_type"],
                    raw_content=artifact["raw_content"],
                    artifact_metadata=artifact["metadata"],
                )
            )

        await session.commit()
        print(f"Seeded case file {case_file.id} ({case_file.name}) with {len(scenario['artifacts'])} artifacts.")
        return case_file.id


async def seed_all() -> list[str]:
    """Seed every scenario in CASES. Used for the empty-DB startup case."""
    ids = []
    for i in range(len(CASES)):
        ids.append(await seed_one(i))
    return ids


# Backward-compatible alias — some existing code (backend/app/main.py's
# original startup check, scripts/demo.py) may still call seed() directly.
async def seed() -> str:
    return await seed_one(0)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(seed_one(int(sys.argv[1])))
    else:
        asyncio.run(seed_all())
