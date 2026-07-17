"""Triage Agent.

Input: raw artifacts for a CaseFile (its designated domain — read via the
gateway, but not resource-gated, since this is the agent's own starting
input, not another agent's output).
Output: TriageFlag rows, always created as status='pending'. The agent
prompt explicitly tells the model it has no authority to approve anything;
the gateway also discards any status field from the payload server-side
(see gateway/main.py::create_triage_flag) so this is enforced twice.
"""

import json

from agents import heuristics
from agents.anthropic_client import complete_json
from agents.gateway_client import gateway_post
from shared.config import settings

SYSTEM_PROMPT = (
    "You are the Triage Agent for CaseLens, an investigative case-review system. "
    "You will be given raw artifacts (documents, device-extraction records, and "
    "communications) from a single case file. Flag ONLY the artifacts that are "
    "investigatively relevant to a potential vendor-payment irregularity or "
    "similar misconduct; ignore routine, personal, or unrelated content. For each "
    "flagged artifact, give a concise plain-language rationale and a confidence "
    "score between 0 and 1.\n\n"
    "You have no authority to approve artifacts for downstream use — approval is "
    "a human-only action. Never include a 'status' field in your output; it will "
    "be ignored if you do.\n\n"
    "Respond with strict JSON and nothing else, matching this shape:\n"
    '{"flags": [{"artifact_id": "...", "rationale": "...", "confidence_score": 0.0}]}'
)


async def _flag_with_claude(artifacts: list[dict]) -> list[dict]:
    user_prompt = "Artifacts:\n" + json.dumps(artifacts, indent=2)
    result = await complete_json(system=SYSTEM_PROMPT, user=user_prompt)
    return result["flags"]


async def run(case_file_id: str) -> list[dict]:
    listing = await gateway_post("/gateway/artifacts/list", params={"case_file_id": case_file_id})
    if not listing["allowed"]:
        raise RuntimeError(f"gateway denied artifact listing: {listing['reason']}")
    artifacts = listing["data"]

    if settings.anthropic_api_key:
        flags = await _flag_with_claude(artifacts)
    else:
        flags = heuristics.triage_flags(artifacts)

    created = []
    for flag in flags:
        gate = await gateway_post(
            "/gateway/triage/create-flag",
            json={
                "case_file_id": case_file_id,
                "artifact_id": flag["artifact_id"],
                "rationale": flag["rationale"],
                "confidence_score": flag["confidence_score"],
            },
        )
        if gate["allowed"]:
            created.append(gate["data"])
    return created
