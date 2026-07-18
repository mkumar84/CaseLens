from fastapi import APIRouter

from agents import triage_agent
from scripts.seed import seed_one

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/seed")
async def reseed(with_triage: bool = False):
    """Portfolio-demo convenience, not a production pattern: unauthenticated,
    unrate-limited on-demand reseeding. A multi-tenant version of this
    endpoint would need both. Each call adds one new case file. Prefers a
    scenario not already represented in the database, so repeated calls
    cover all demo scenarios once each before ever repeating one.

    with_triage=true additionally runs the Triage Agent against the new
    case immediately, so it arrives with real flags ready for human
    review — deliberately stops there rather than chaining Timeline/Report,
    since skipping straight to a finished report would bypass the human
    approve/reject step the whole system is built to require.
    """
    case_file_id = await seed_one()
    flags_created = []
    if with_triage:
        flags_created = await triage_agent.run(case_file_id)
    return {
        "case_file_id": case_file_id,
        "status": "seeded",
        "triage_flags_created": len(flags_created),
    }
