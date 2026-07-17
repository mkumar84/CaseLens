from fastapi import APIRouter

from scripts.seed import seed

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/seed")
async def reseed():
    """Portfolio-demo convenience, not a production pattern: unauthenticated,
    unrate-limited on-demand reseeding. A multi-tenant version of this
    endpoint would need both. Safe to call repeatedly — adds a new case file
    each time rather than overwriting, so existing demo state from a prior
    run-through is preserved unless manually cleared.
    """
    case_file_id = await seed()
    return {"case_file_id": case_file_id, "status": "seeded"}
