"""Report Drafting Agent.

Input: approved TriageFlag + TimelineEntry data for a CaseFile (via the
gateway's report/list-case-data, which itself re-evaluates Policy 1 per
row rather than trusting a filtered query).
Output: a ReportDraft with every factual claim citing a specific artifact
id, and a citation_coverage_pct computed by the gateway from the claims
list — never trusted from this agent's own accounting.
"""

import json

from agents import heuristics
from agents.anthropic_client import complete_json
from agents.gateway_client import gateway_post
from shared.config import settings

SYSTEM_PROMPT = (
    "You are the Report Drafting Agent for CaseLens. You are given approved, "
    "investigatively-relevant artifacts and a timeline built from them. Draft a "
    "short investigative report. Every factual claim MUST cite the specific "
    "artifact_id it is drawn from — never state a fact without a citation.\n\n"
    "Respond with strict JSON and nothing else, matching this shape:\n"
    '{"content": "...", "claims": [{"claim_id": "...", "claim_text": "...", '
    '"artifact_id": "..."}]}'
)


async def _draft_with_claude(approved_artifacts: list[dict], timeline_entries: list[dict]) -> tuple[str, list[dict]]:
    user_prompt = (
        "Approved artifacts:\n"
        + json.dumps(approved_artifacts, indent=2)
        + "\n\nTimeline:\n"
        + json.dumps(timeline_entries, indent=2)
    )
    result = await complete_json(system=SYSTEM_PROMPT, user=user_prompt)
    return result["content"], result["claims"]


async def gather_case_data(case_file_id: str) -> dict:
    gate = await gateway_post("/gateway/report/list-case-data", params={"case_file_id": case_file_id})
    if not gate["allowed"]:
        raise RuntimeError(f"gateway denied case data listing: {gate['reason']}")
    return gate["data"]


async def draft_claims(case_data: dict) -> tuple[str, list[dict]]:
    if settings.anthropic_api_key:
        return await _draft_with_claude(case_data["approved_artifacts"], case_data["timeline_entries"])
    return heuristics.report_claims(case_data["approved_artifacts"])


async def submit_draft(case_file_id: str, content: str, claims: list[dict]) -> dict:
    gate = await gateway_post(
        "/gateway/report/create-draft",
        json={
            "case_file_id": case_file_id,
            "content": content,
            "claims": claims,
            "created_by_agent": "report-agent",
        },
    )
    if not gate["allowed"]:
        raise RuntimeError(f"gateway denied report draft creation: {gate['reason']}")
    return gate["data"]


async def run(case_file_id: str) -> dict:
    case_data = await gather_case_data(case_file_id)
    content, claims = await draft_claims(case_data)
    return await submit_draft(case_file_id, content, claims)


async def request_case_ready(report_draft_id: str) -> dict:
    return await gateway_post(
        "/gateway/report/transition-status",
        json={
            "report_draft_id": report_draft_id,
            "to_status": "case_ready",
            "requested_by_agent": "report-agent",
        },
    )
