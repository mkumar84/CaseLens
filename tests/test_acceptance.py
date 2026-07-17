"""Acceptance tests mirroring the CLAUDE.md checklist. Each test that
matters here proves a gateway-enforced property, not an app-code check an
agent could have skipped — several deliberately call the gateway the way a
misbehaving or bypassing agent would, and confirm it is stopped regardless.
"""

import pytest
from sqlalchemy import select

from shared.db.models import TriageFlag
from shared.db.session import SessionLocal


async def _get_first_artifact_id(case_file_id: str) -> str:
    from shared.db.models import Artifact

    async with SessionLocal() as session:
        row = (
            await session.execute(select(Artifact).where(Artifact.case_file_id == case_file_id).limit(1))
        ).scalar_one()
        return row.id


async def test_triage_flag_ignores_agent_supplied_status(gateway_client, seeded_case_file_id):
    """Triage Agent prompt discipline: even if the payload tries to set
    status='approved', the gateway must discard it and force 'pending'."""
    artifact_id = await _get_first_artifact_id(seeded_case_file_id)

    resp = await gateway_client.post(
        "/gateway/triage/create-flag",
        json={
            "case_file_id": seeded_case_file_id,
            "artifact_id": artifact_id,
            "rationale": "looks relevant",
            "confidence_score": 0.8,
            "status": "approved",  # a misbehaving/compromised agent trying to self-approve
        },
    )
    body = resp.json()
    assert body["allowed"] is True
    assert body["data"]["status"] == "pending"


async def test_policy1_blocks_direct_bypass_read_of_pending_flag(gateway_client, seeded_case_file_id):
    """Timeline Agent attempts to read an artifact whose TriageFlag was
    never reviewed. This is the direct-bypass test CLAUDE.md calls for:
    the gateway must deny the underlying data request itself."""
    artifact_id = await _get_first_artifact_id(seeded_case_file_id)
    create = await gateway_client.post(
        "/gateway/triage/create-flag",
        json={
            "case_file_id": seeded_case_file_id,
            "artifact_id": artifact_id,
            "rationale": "pending review",
            "confidence_score": 0.5,
        },
    )
    flag_id = create.json()["data"]["id"]

    resp = await gateway_client.post(
        "/gateway/timeline/read-artifact",
        json={"case_file_id": seeded_case_file_id, "triage_flag_id": flag_id},
    )
    body = resp.json()
    assert body["allowed"] is False
    assert "not human-approved" in body["reason"]
    assert body["data"] is None


async def test_policy1_blocks_direct_bypass_read_of_rejected_flag(gateway_client, seeded_case_file_id):
    """Same bypass attempt, but against a flag a human explicitly rejected —
    must still be denied, not merely hidden by the UI."""
    artifact_id = await _get_first_artifact_id(seeded_case_file_id)
    create = await gateway_client.post(
        "/gateway/triage/create-flag",
        json={
            "case_file_id": seeded_case_file_id,
            "artifact_id": artifact_id,
            "rationale": "will be rejected",
            "confidence_score": 0.5,
        },
    )
    flag_id = create.json()["data"]["id"]

    async with SessionLocal() as session:
        flag = await session.get(TriageFlag, flag_id)
        flag.status = "rejected"
        await session.commit()

    resp = await gateway_client.post(
        "/gateway/timeline/read-artifact",
        json={"case_file_id": seeded_case_file_id, "triage_flag_id": flag_id},
    )
    assert resp.json()["allowed"] is False


async def test_policy1_allows_read_once_approved(gateway_client, seeded_case_file_id):
    artifact_id = await _get_first_artifact_id(seeded_case_file_id)
    create = await gateway_client.post(
        "/gateway/triage/create-flag",
        json={
            "case_file_id": seeded_case_file_id,
            "artifact_id": artifact_id,
            "rationale": "will be approved",
            "confidence_score": 0.9,
        },
    )
    flag_id = create.json()["data"]["id"]

    async with SessionLocal() as session:
        flag = await session.get(TriageFlag, flag_id)
        flag.status = "approved"
        await session.commit()

    resp = await gateway_client.post(
        "/gateway/timeline/read-artifact",
        json={"case_file_id": seeded_case_file_id, "triage_flag_id": flag_id},
    )
    body = resp.json()
    assert body["allowed"] is True
    assert body["data"]["artifact_id"] == artifact_id


async def test_full_pipeline_via_real_agent_modules(wire_agents_to_gateway, backend_client, seeded_case_file_id):
    """Runs the actual agents/*.py modules (not just raw gateway calls)
    through triage -> human review -> timeline -> compliant report ->
    case_ready, using the in-process gateway ASGI app."""
    from agents import report_agent, timeline_agent, triage_agent

    flags = await triage_agent.run(seeded_case_file_id)
    assert len(flags) > 0
    assert all(f["status"] == "pending" for f in flags)

    for flag in flags:
        resp = await backend_client.post(
            f"/triage-flags/{flag['id']}/review",
            json={"decision": "approved", "reviewed_by": "test-reviewer"},
        )
        assert resp.status_code == 200

    entries = await timeline_agent.run(seeded_case_file_id)
    assert len(entries) == len(flags)

    draft = await report_agent.run(seeded_case_file_id)
    assert draft["citation_coverage_pct"] == 100.0

    transition = await report_agent.request_case_ready(draft["id"])
    assert transition["allowed"] is True


async def test_misbehaving_report_agent_blocked_by_policy2(wire_agents_to_gateway, backend_client, seeded_case_file_id):
    """The core Policy 2 acceptance test: a Report Agent variant that omits
    ~20% of citations must still be blocked from reaching case_ready, and
    the gateway must report which claims are unsourced."""
    from agents import report_agent_misbehaving, timeline_agent, triage_agent

    flags = await triage_agent.run(seeded_case_file_id)
    for flag in flags:
        await backend_client.post(
            f"/triage-flags/{flag['id']}/review",
            json={"decision": "approved", "reviewed_by": "test-reviewer"},
        )
    await timeline_agent.run(seeded_case_file_id)

    result = await report_agent_misbehaving.run_and_attempt_case_ready(seeded_case_file_id)
    assert result["draft"]["citation_coverage_pct"] < 100.0
    assert result["transition"]["allowed"] is False
    assert "below 100%" in result["transition"]["reason"]
    assert len(result["transition"]["unsourced_claims"]) > 0


async def test_policy2_denial_leaves_report_blocked(backend_client, gateway_client, seeded_case_file_id):
    resp = await gateway_client.post(
        "/gateway/report/create-draft",
        json={
            "case_file_id": seeded_case_file_id,
            "content": "partial report",
            "claims": [
                {"claim_id": "c1", "claim_text": "cited claim", "artifact_id": await _get_first_artifact_id(seeded_case_file_id)},
                {"claim_id": "c2", "claim_text": "uncited claim", "artifact_id": None},
            ],
        },
    )
    draft_id = resp.json()["data"]["id"]

    transition = await gateway_client.post(
        "/gateway/report/transition-status",
        json={"report_draft_id": draft_id, "to_status": "case_ready"},
    )
    assert transition.json()["allowed"] is False

    got = await backend_client.get(f"/report-drafts/{draft_id}")
    assert got.json()["status"] == "blocked"


async def test_policy3_rolls_back_action_when_audit_logging_fails(gateway_client, seeded_case_file_id):
    """Audit-completeness gate: if the Audit Agent fails to log an action,
    the triggering action itself must roll back, not just the log entry."""
    artifact_id = await _get_first_artifact_id(seeded_case_file_id)

    resp = await gateway_client.post(
        "/gateway/triage/create-flag?_force_audit_failure=true",
        json={
            "case_file_id": seeded_case_file_id,
            "artifact_id": artifact_id,
            "rationale": "should not survive",
            "confidence_score": 0.5,
        },
    )
    body = resp.json()
    assert body["allowed"] is False
    assert body["rolled_back"] is True

    async with SessionLocal() as session:
        rows = (
            await session.execute(select(TriageFlag).where(TriageFlag.artifact_id == artifact_id))
        ).scalars().all()
        assert len(rows) == 0, "the rolled-back TriageFlag must not be persisted"


async def test_policy_decision_log_has_explainable_denials(gateway_client, backend_client, seeded_case_file_id):
    """Acceptance checklist: PolicyDecisionLog must show a non-zero,
    explainable set of denials, proving the gateway does real work."""
    artifact_id = await _get_first_artifact_id(seeded_case_file_id)
    create = await gateway_client.post(
        "/gateway/triage/create-flag",
        json={
            "case_file_id": seeded_case_file_id,
            "artifact_id": artifact_id,
            "rationale": "pending",
            "confidence_score": 0.5,
        },
    )
    flag_id = create.json()["data"]["id"]
    await gateway_client.post(
        "/gateway/timeline/read-artifact",
        json={"case_file_id": seeded_case_file_id, "triage_flag_id": flag_id},
    )

    denials = await backend_client.get("/policy-decisions", params={"decision": "deny"})
    denial_rows = denials.json()
    assert len(denial_rows) > 0
    assert any(r["policy_name"] == "require-human-approval" for r in denial_rows)
    assert all(r["reason"] for r in denial_rows)


async def test_audit_chain_verifies_clean_after_normal_activity(
    wire_agents_to_gateway, backend_client, seeded_case_file_id
):
    """PRD Goal #4: the audit log must be tamper-evident. After ordinary
    pipeline activity (which already appends many entries from multiple
    writers — the gateway's Audit Agent and the backend's human-review
    endpoint), the hash chain must verify clean."""
    from agents import triage_agent

    flags = await triage_agent.run(seeded_case_file_id)
    for flag in flags:
        await backend_client.post(
            f"/triage-flags/{flag['id']}/review",
            json={"decision": "approved", "reviewed_by": "test-reviewer"},
        )

    result = await backend_client.get("/audit-log/verify")
    body = result.json()
    assert body["valid"] is True
    assert body["checked"] > 0
    assert body["broken_at_seq"] is None


async def test_audit_chain_detects_tampering(gateway_client, backend_client, seeded_case_file_id):
    """Directly mutating a persisted AuditLogEntry (simulating a
    post-hoc tamper attempt, bypassing the appender entirely) must be
    caught by verify_chain, pinpointing the first broken entry."""
    from shared.db.models import AuditLogEntry

    artifact_id = await _get_first_artifact_id(seeded_case_file_id)
    await gateway_client.post(
        "/gateway/triage/create-flag",
        json={
            "case_file_id": seeded_case_file_id,
            "artifact_id": artifact_id,
            "rationale": "original rationale",
            "confidence_score": 0.5,
        },
    )

    clean = await backend_client.get("/audit-log/verify")
    assert clean.json()["valid"] is True

    async with SessionLocal() as session:
        rows = (await session.execute(select(AuditLogEntry).order_by(AuditLogEntry.seq))).scalars().all()
        target = rows[0]
        target.reason = "tampered after the fact"
        await session.commit()
        tampered_seq = target.seq

    tampered = await backend_client.get("/audit-log/verify")
    body = tampered.json()
    assert body["valid"] is False
    assert body["broken_at_seq"] == tampered_seq


async def test_every_triage_flag_has_rationale_confidence_and_source(gateway_client, seeded_case_file_id):
    listing = await gateway_client.post(
        "/gateway/artifacts/list", params={"case_file_id": seeded_case_file_id}
    )
    artifacts = listing.json()["data"]
    assert len(artifacts) >= 15

    from agents import heuristics

    flags = heuristics.triage_flags(artifacts)
    assert len(flags) > 0
    for flag in flags:
        assert flag["artifact_id"]
        assert flag["rationale"]
        assert 0 <= flag["confidence_score"] <= 1
