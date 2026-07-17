"""Endpoints that trigger an agent run. Each of these simply invokes the
corresponding agents/*.py module, which talks only to the gateway — this
router holds no case-data logic of its own.
"""

from fastapi import APIRouter

from agents import report_agent, report_agent_misbehaving, timeline_agent, triage_agent

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/triage/run")
async def run_triage(case_file_id: str):
    return {"flags_created": await triage_agent.run(case_file_id)}


@router.post("/timeline/run")
async def run_timeline(case_file_id: str):
    return {"entries_created": await timeline_agent.run(case_file_id)}


@router.post("/report/run")
async def run_report(case_file_id: str):
    return {"draft": await report_agent.run(case_file_id)}


@router.post("/report/run-misbehaving")
async def run_report_misbehaving(case_file_id: str):
    """Demo/test-only: the deliberately-noncompliant Report Agent variant
    that omits citations on ~20% of claims, used to prove Policy 2 blocks
    the case-ready transition regardless of agent behavior."""
    return await report_agent_misbehaving.run_and_attempt_case_ready(case_file_id)


@router.post("/report/{report_draft_id}/request-case-ready")
async def request_case_ready(report_draft_id: str):
    return await report_agent.request_case_ready(report_draft_id)
