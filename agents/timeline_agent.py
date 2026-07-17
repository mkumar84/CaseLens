"""Timeline Agent.

Input: TriageFlag rows with status == 'approved' only — enforced by
agentgateway Policy 1, not by this agent choosing to filter. This module
never sees a non-approved artifact's content: the gateway fetches ground
truth and only returns raw_content when the CEL rule holds.
Output: TimelineEntry rows, one per approved artifact.
"""

import json

from agents import heuristics
from agents.anthropic_client import complete_json
from agents.gateway_client import gateway_post
from shared.config import settings

SYSTEM_PROMPT = (
    "You are the Timeline Agent for CaseLens. You are given a set of "
    "human-approved artifacts, each already vetted for investigative "
    "relevance. Construct a chronological sequence of discrete events, one "
    "per artifact, each with a single ISO-8601 event_timestamp (use the date "
    "in the artifact's metadata if present) and a concise event_description.\n\n"
    "Respond with strict JSON and nothing else, matching this shape:\n"
    '{"entries": [{"artifact_id": "...", "event_timestamp": "...", "event_description": "..."}]}'
)


async def _build_with_claude(approved_artifacts: list[dict]) -> list[dict]:
    user_prompt = "Approved artifacts:\n" + json.dumps(approved_artifacts, indent=2)
    result = await complete_json(system=SYSTEM_PROMPT, user=user_prompt)
    return result["entries"]


async def run(case_file_id: str) -> list[dict]:
    candidates = await gateway_post(
        "/gateway/timeline/list-approved-flags", params={"case_file_id": case_file_id}
    )
    if not candidates["allowed"]:
        raise RuntimeError(f"gateway denied approved-flag listing: {candidates['reason']}")

    approved_artifacts = []
    for candidate in candidates["data"]:
        gate = await gateway_post(
            "/gateway/timeline/read-artifact",
            json={
                "case_file_id": case_file_id,
                "triage_flag_id": candidate["triage_flag_id"],
                "requesting_agent": "timeline-agent",
            },
        )
        if not gate["allowed"]:
            # Should not happen: list-approved-flags already filtered to
            # 'approved'. If it ever does (a race with a human re-review),
            # Policy 1 is still the one stopping it, not this agent.
            continue
        approved_artifacts.append(gate["data"])

    if not approved_artifacts:
        return []

    if settings.anthropic_api_key:
        entries = await _build_with_claude(approved_artifacts)
    else:
        entries = heuristics.timeline_entries(approved_artifacts)

    created = []
    for entry in entries:
        gate = await gateway_post(
            "/gateway/timeline/create-entry",
            json={
                "case_file_id": case_file_id,
                "artifact_id": entry["artifact_id"],
                "event_timestamp": entry["event_timestamp"],
                "event_description": entry["event_description"],
                "created_by_agent": "timeline-agent",
            },
        )
        if gate["allowed"]:
            created.append(gate["data"])
    return created


async def attempt_bypass_read(case_file_id: str, triage_flag_id: str) -> dict:
    """Used only by the acceptance test that proves Policy 1 blocks a direct
    read of a non-approved artifact, bypassing the normal discovery flow."""
    return await gateway_post(
        "/gateway/timeline/read-artifact",
        json={
            "case_file_id": case_file_id,
            "triage_flag_id": triage_flag_id,
            "requesting_agent": "timeline-agent",
        },
    )
