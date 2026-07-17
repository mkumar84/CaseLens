"""Deliberately-noncompliant Report Agent variant, built for the acceptance
test in CLAUDE.md: "configure a misbehaving variant of this agent that
omits citations on ~20% of claims. Confirm the case-ready transition is
still blocked by Policy 2 regardless."

This reuses the real agent's data-gathering and drafting, then strips
citations off ~20% of claims before submission — simulating an agent that
skipped citing some facts. Policy 2 must catch this at the gateway; nothing
here is trusted to self-report its own honesty.
"""

from agents.report_agent import draft_claims, gather_case_data, request_case_ready, submit_draft


def _drop_some_citations(claims: list[dict], drop_fraction: float = 0.2) -> list[dict]:
    if not claims:
        return claims
    n_to_drop = max(1, round(len(claims) * drop_fraction))
    corrupted = [dict(c) for c in claims]
    for claim in corrupted[:n_to_drop]:
        claim["artifact_id"] = None
    return corrupted


async def run(case_file_id: str) -> dict:
    case_data = await gather_case_data(case_file_id)
    content, claims = await draft_claims(case_data)
    corrupted_claims = _drop_some_citations(claims)
    return await submit_draft(case_file_id, content, corrupted_claims)


async def run_and_attempt_case_ready(case_file_id: str) -> dict:
    """End-to-end demo/test helper: draft with dropped citations, then try
    (and expect to fail) the case_ready transition."""
    draft = await run(case_file_id)
    transition = await request_case_ready(draft["id"])
    return {"draft": draft, "transition": transition}
