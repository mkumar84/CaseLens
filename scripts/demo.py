"""CaseLens end-to-end demo script.

Walks through the full Frame-Prove-Earn loop in one run: normal triage ->
human review (approve some, REJECT one) -> a direct-bypass attempt on the
rejected artifact (denied by agentgateway) -> Timeline Agent -> a compliant
Report Agent reaching case_ready -> a deliberately-noncompliant Report Agent
blocked by Policy 2 -> the full policy-decision and audit trail.

Usage: python -m scripts.demo
Starts its own gateway + backend uvicorn processes on 127.0.0.1:8001/8000,
seeds a fresh CaseFile, runs the narrative, and shuts everything down. Runs
in well under 5 minutes; most of that is Claude API latency if
ANTHROPIC_API_KEY is set, or near-instant if it falls back to the offline
heuristics (see agents/heuristics.py).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

GATEWAY_PORT = 8001
BACKEND_PORT = 8000
GATEWAY_URL = f"http://127.0.0.1:{GATEWAY_PORT}"
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"

ROOT = Path(__file__).resolve().parent.parent


def banner(title: str) -> None:
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def wait_for_health(health_url: str, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(health_url, timeout=2)
            if resp.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    raise RuntimeError(f"{health_url} did not become healthy in time")


def main() -> None:
    start = time.monotonic()
    db_path = ROOT / "demo.db"
    if db_path.exists():
        db_path.unlink()
    env = {**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"}

    banner("Starting agentgateway and backend API")
    gateway_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "gateway.main:app", "--port", str(GATEWAY_PORT)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--port", str(BACKEND_PORT)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        wait_for_health(f"{GATEWAY_URL}/gateway/health")
        wait_for_health(f"{BACKEND_URL}/health")
        print("Both services are up.")

        client = httpx.Client(timeout=30)

        banner("Step 1 — Synthetic mixed CaseFile")
        from db.seed_data import ARTIFACTS

        # backend/app/main.py's lifespan auto-seeds one CaseFile on startup
        # against an empty database (the same behavior the deployed Railway
        # app relies on so a fresh URL always has demo data ready). Reuse
        # it here instead of also creating one directly — doing both would
        # leave two duplicate-looking case files sitting in demo.db.
        case_files = client.get(f"{BACKEND_URL}/case-files").json()
        case_file = case_files[0]
        case_file_id = case_file["id"]
        print(f"Case file (auto-seeded on backend startup): {case_file['name']} ({case_file_id})")
        print(f"{len(ARTIFACTS)} artifacts (documents, device extraction, comms).")

        banner("Step 2 — Triage Agent flags investigatively relevant artifacts")
        triage_result = client.post(f"{BACKEND_URL}/agents/triage/run", params={"case_file_id": case_file_id}).json()
        flags = triage_result["flags_created"]
        print(f"Triage Agent proposed {len(flags)} flags (all status=pending):")
        flag_details = client.get(f"{BACKEND_URL}/triage-flags", params={"case_file_id": case_file_id}).json()
        for f in flag_details:
            print(f"  - [{f['confidence_score']:.2f}] {f['rationale'][:90]}")

        banner("Step 3 — Human review: approve most, REJECT one")
        rejected_id = flag_details[-1]["id"]
        for f in flag_details:
            decision = "rejected" if f["id"] == rejected_id else "approved"
            client.post(
                f"{BACKEND_URL}/triage-flags/{f['id']}/review",
                json={"decision": decision, "reviewed_by": "demo-reviewer"},
            )
        print(f"Approved {len(flag_details) - 1} flags, rejected 1 ({rejected_id}).")

        banner("Step 4 — Direct-bypass attempt on the REJECTED artifact")
        print("Simulating Timeline Agent trying to read the rejected artifact's content directly...")
        bypass = client.post(
            f"{GATEWAY_URL}/gateway/timeline/read-artifact",
            json={"case_file_id": case_file_id, "triage_flag_id": rejected_id},
        ).json()
        assert bypass["allowed"] is False, "Policy 1 should have denied this"
        print(f"DENIED by agentgateway (Policy 1): {bypass['reason']}")

        banner("Step 5 — Timeline Agent builds the chronology from approved artifacts only")
        timeline_result = client.post(f"{BACKEND_URL}/agents/timeline/run", params={"case_file_id": case_file_id}).json()
        entries = timeline_result["entries_created"]
        print(f"Timeline Agent created {len(entries)} entries (never saw the rejected artifact's content).")

        banner("Step 6 — Compliant Report Agent drafts a fully-cited report")
        report_result = client.post(f"{BACKEND_URL}/agents/report/run", params={"case_file_id": case_file_id}).json()
        draft = report_result["draft"]
        print(f"ReportDraft {draft['id']} — citation_coverage_pct={draft['citation_coverage_pct']}")
        transition = client.post(f"{BACKEND_URL}/agents/report/{draft['id']}/request-case-ready").json()
        print(f"case_ready transition: allowed={transition['allowed']}")

        banner("Step 7 — Misbehaving Report Agent (omits ~20% of citations)")
        misbehaving = client.post(
            f"{BACKEND_URL}/agents/report/run-misbehaving", params={"case_file_id": case_file_id}
        ).json()
        print(f"ReportDraft {misbehaving['draft']['id']} — citation_coverage_pct={misbehaving['draft']['citation_coverage_pct']}")
        print(f"case_ready transition: allowed={misbehaving['transition']['allowed']}")
        print(f"Reason: {misbehaving['transition']['reason']}")
        print(f"Unsourced claims flagged: {len(misbehaving['transition']['unsourced_claims'])}")
        assert misbehaving["transition"]["allowed"] is False, "Policy 2 should have blocked this regardless"

        banner("Step 8 — PolicyDecisionLog: a non-zero, explainable set of denials")
        decisions = client.get(f"{BACKEND_URL}/policy-decisions").json()
        from collections import Counter

        counts = Counter((d["policy_name"], d["decision"]) for d in decisions)
        for (policy, decision), count in sorted(counts.items()):
            print(f"  {policy:35s} {decision:6s} x{count}")

        banner("Step 9 — AuditLogEntry: full decision trail for this case")
        audit_rows = client.get(f"{BACKEND_URL}/audit-log", params={"case_file_id": case_file_id}).json()
        print(f"{len(audit_rows)} audit entries recorded for this case file. Last 8:")
        for row in audit_rows[-8:]:
            print(f"  {row['actor']:20s} {row['action']:28s} {row['decision']:6s} {row['reason'] or ''}")

        banner("Step 10 — Tamper-evident audit log (PRD Goal #4)")
        clean = client.get(f"{BACKEND_URL}/audit-log/verify").json()
        print(f"Chain verify before tampering: valid={clean['valid']}, checked={clean['checked']} entries")
        print("Simulating a post-hoc tamper: editing one persisted audit row's 'reason' directly in the DB...")
        _tamper_first_audit_row(env)
        tampered = client.get(f"{BACKEND_URL}/audit-log/verify").json()
        print(f"Chain verify after tampering:  valid={tampered['valid']}, broken_at_seq={tampered['broken_at_seq']}")
        assert clean["valid"] is True and tampered["valid"] is False, "tamper detection should have fired"

        elapsed = time.monotonic() - start
        banner(f"Demo complete in {elapsed:.1f}s")

    finally:
        gateway_proc.terminate()
        backend_proc.terminate()
        gateway_proc.wait(timeout=10)
        backend_proc.wait(timeout=10)


def _tamper_first_audit_row(env: dict) -> None:
    """Demo-only: mutates a persisted AuditLogEntry directly in the DB,
    bypassing shared/audit_chain.py entirely, to show the hash chain
    catching a tamper attempt that never went through the appender."""
    import asyncio

    os.environ["DATABASE_URL"] = env["DATABASE_URL"]
    from sqlalchemy import select

    from shared.db.models import AuditLogEntry
    from shared.db.session import session_scope

    async def _run():
        async with session_scope() as session:
            row = (
                await session.execute(select(AuditLogEntry).order_by(AuditLogEntry.seq).limit(1))
            ).scalar_one()
            row.reason = "tampered after the fact"
            await session.commit()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
