# CaseLens Backend

Four Claude Sonnet agents (Triage, Timeline, Report, Audit), a real
CEL-policy control plane sitting between them, and an append-only audit
trail — built to be consumed by a Lovable frontend over REST.

## The property this build is trying to prove

**Agents hold zero database credentials.** Every file under `agents/`
imports `agents/gateway_client.py` and nothing else for I/O — there is no
`import asyncpg`, no Supabase client, no SQLAlchemy session anywhere in that
package. The only way an agent can read or write case data is an HTTP call
to the gateway, and the gateway independently re-fetches whatever resource
a policy needs to evaluate (it never trusts a value the agent sent). That's
what makes a policy gate here different from an `if` statement in app code:
an agent can't route around a check it never gets a chance to call.

`tests/test_acceptance.py` and `scripts/demo.py` both include a call that
plays the part of a misbehaving or bypassing agent — reading a
non-approved artifact directly, or submitting a report with missing
citations — and confirm the gateway stops it regardless.

## Architecture

```
                       ┌────────────────────┐
  Lovable frontend ───▶│   backend/  (:8000) │── reads case data directly
                       │  human-facing API    │   (case files, review
                       └──────────┬───────────┘    actions, listings)
                                  │ POST /agents/*
                                  ▼
                       ┌────────────────────┐
        agents/*.py ──▶│   gateway/  (:8001)  │── the ONLY DB connection
     (Triage, Timeline,│  agentgateway         │   an agent-triggered
      Report agents)   │  control plane        │   action ever touches
                       └──────────┬───────────┘
                                  ▼
                          Postgres (Supabase)
                          or local SQLite
```

- **`backend/`** — the human/system-of-record FastAPI app. Lists case
  files, artifacts, triage flags, timeline entries, reports, and the audit
  trail; handles the one human action in this build (approve/reject a
  TriageFlag); triggers agent runs via `/agents/*`. Holds a direct DB
  connection — that's fine, it isn't an agent, and a human clicking
  "approve" isn't the thing Policy 1 is designed to gate.
- **`gateway/`** — the control plane. Every agent-to-data read, every
  cross-agent handoff, and every status transition goes through here. It's
  the sole holder of DB credentials for anything an agent triggers, it
  evaluates the CEL rules in `gateway/policies/*.yaml` with a real CEL
  engine ([`cel-python`](https://github.com/cloud-custodian/cel-python)),
  and it writes `PolicyDecisionLog` + `AuditLogEntry` rows itself rather
  than trusting an agent to self-report.
- **`agents/`** — one module per agent (`triage_agent.py`,
  `timeline_agent.py`, `report_agent.py`, plus
  `report_agent_misbehaving.py`, the deliberately-noncompliant variant used
  in the Policy 2 acceptance test). The fourth agent, Audit, lives inside
  the gateway (`gateway/audit_agent.py`) rather than as a caller of it —
  its whole job is to be invoked *by* the gateway for every action, so
  that's where it has to live for the rollback guarantee to mean anything.
- **`shared/`** — the SQLAlchemy models and DB session, imported by
  `backend/` and `gateway/` only, never by `agents/`.

### A note on "agentgateway"

CLAUDE.md's build note flags that the real `agentgateway.dev` YAML/CEL
schema should be validated against the installed version before wiring it
in. Standing up the actual Rust agentgateway binary as a second piece of
infrastructure was out of reach for this build session, so `gateway/` is a
from-scratch FastAPI service that enforces the *same* `AgentgatewayPolicy`
contract — same YAML shape, same CEL rule strings (one `100` →`100.0`
literal-typing fix, called out in `gateway/policies/require_full_citation_coverage.yaml`),
same allow/deny/log semantics — using a real CEL implementation rather than
hand-rolled `if` checks. If a real agentgateway instance is stood up later,
the policy YAML in `gateway/policies/` is what it would be configured with;
`gateway/action_executor.py` is the piece that would be replaced by
agentgateway's own request routing.

## Data model

See `db/schema.sql` for the full Postgres/Supabase DDL. Matches the model
in CLAUDE.md exactly: `case_files`, `artifacts`, `triage_flags`,
`timeline_entries`, `report_drafts`, `audit_log_entries`,
`policy_decision_log`. `shared/db/models.py` is the SQLAlchemy mirror of
the same schema, portable between SQLite (local/dev/test) and Postgres
(Supabase) — IDs are stored as strings rather than native UUID/enum types
for that portability; `db/schema.sql` remains the source of truth for what
actually gets applied to Supabase.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in DATABASE_URL / ANTHROPIC_API_KEY if you have them
```

Both are optional for local development:
- No `DATABASE_URL` → falls back to a local SQLite file (`./caselens.db`).
  `db/schema.sql` is what you'd run against a real Supabase instance instead.
- No `ANTHROPIC_API_KEY` → every agent falls back to the deterministic
  logic in `agents/heuristics.py` instead of calling Claude, so the
  gateway, policies, seed data, tests, and demo script are all runnable
  without a live key. Set the key to see the real Claude Sonnet-backed
  reasoning.

## Running it

```bash
python -m scripts.seed                                        # seed one CaseFile, 18 artifacts
uvicorn gateway.main:app --port 8001 &
uvicorn backend.app.main:app --port 8000 &
```

Then either drive it through the API (see below) or run the scripted
walkthrough, which starts its own gateway/backend processes, seeds its own
case file, and runs the full narrative in one shot:

```bash
python -m scripts.demo
```

This is the Build Order's "demo script" — the interview artifact, not just
the app. It runs normal triage → human approves most flags and **rejects
one** → a simulated Timeline Agent bypass attempt against the rejected
artifact (denied by Policy 1) → Timeline Agent → a compliant Report Agent
reaching `case_ready` → the deliberately-noncompliant Report Agent blocked
by Policy 2 → a summary of `PolicyDecisionLog` and `AuditLogEntry`. Runs in
well under 5 minutes (a few seconds against the offline heuristics; mostly
Claude API latency if a key is set).

### Key API endpoints (backend, :8000)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/case-files` | create a case |
| `GET` | `/artifacts?case_file_id=` | list raw artifacts |
| `GET` | `/triage-flags?case_file_id=&status=` | list triage flags |
| `POST` | `/triage-flags/{id}/review` | human approve/reject |
| `GET` | `/timeline-entries?case_file_id=` | list timeline |
| `GET` | `/report-drafts?case_file_id=` | list report drafts |
| `GET` | `/audit-log?case_file_id=` | audit trail |
| `GET` | `/policy-decisions?policy_name=&decision=` | gateway decision log |
| `POST` | `/agents/triage/run?case_file_id=` | run Triage Agent |
| `POST` | `/agents/timeline/run?case_file_id=` | run Timeline Agent |
| `POST` | `/agents/report/run?case_file_id=` | run (compliant) Report Agent |
| `POST` | `/agents/report/run-misbehaving?case_file_id=` | run the noncompliant variant + attempt case_ready |
| `POST` | `/agents/report/{id}/request-case-ready` | request the case_ready transition |

## Tests

```bash
python -m pytest
```

`tests/test_acceptance.py` maps directly onto the CLAUDE.md checklist:
Policy 1 bypass denial (pending *and* rejected flags), Policy 2 blocking
the deliberately-noncompliant Report Agent, Policy 3's audit-failure
rollback (proving a rolled-back mutation leaves no row behind), and the
full pipeline run through the real agent modules end to end.

## Deploying (Railway)

This is two services from one repo:

1. **backend** — `railway.json` at the repo root already points Railway at
   `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
2. **gateway** — create a second Railway service from the same repo,
   override its start command to
   `uvicorn gateway.main:app --host 0.0.0.0 --port $PORT`.

Set `DATABASE_URL` (your Supabase connection string) and
`ANTHROPIC_API_KEY` on both services. Set `GATEWAY_URL` on the backend
service to the gateway service's internal Railway URL. Apply
`db/schema.sql` to your Supabase project before first run (or let the
SQLite fallback create tables automatically for a quick smoke test without
Supabase configured).

## Explicitly out of scope

Per CLAUDE.md / the PRD's non-goals: no real forensic tool integration, no
multi-examiner workflows, no model fine-tuning, no court-admissibility
features, no policy versioning/diffing.
