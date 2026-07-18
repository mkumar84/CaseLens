# CaseLens Backend

Four Claude Sonnet agents (Triage, Timeline, Report, Audit), a real
CEL-policy control plane sitting between them, and a tamper-evident,
hash-chained audit trail — built to be consumed by a Lovable frontend over
REST.

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

### Tamper-evident audit log

`CaseLens-PRD.md` states this as Goal #4, not just a nice-to-have, and its
Open Questions section calls out a SHA-256 hash chain specifically. Every
`AuditLogEntry` — from the gateway's Audit Agent, from the rollback
recorder, and from the backend's human-review endpoint — is appended
through the single function in `shared/audit_chain.py`, never constructed
ad hoc: `entry_hash = sha256(seq, prev_hash, id, case_file_id, actor,
action, target_entity, decision, reason, request_id)`. Editing, deleting,
or reordering any historical row breaks every hash computed after it.
`GET /audit-log/verify` walks the whole chain and reports the first broken
`seq` if one exists; `scripts/demo.py` step 10 tampers with a row directly
in the DB (bypassing the appender) and shows verification flip from
`valid: true` to `valid: false` live.

This is the "Prove it, don't assume it" beat from the PRD's Frame-Prove-Earn
mapping made concrete: rather than asserting the audit log is trustworthy,
the demo shows a tamper attempt getting caught.

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

`db/seed_data.py` defines three synthetic mixed CaseFile scenarios (vendor
payment fraud, a departing-employee IP review, falsified inspection
records) — small enough to review in a demo, each roughly half
investigatively relevant and half routine noise. The backend auto-seeds
**all three** on startup if the database is empty (`backend/app/main.py`'s
`lifespan`, via `scripts.seed.seed_all()`), so a fresh deploy — including
the live Railway URL — always has demo data with zero manual steps and
some range to browse. It only fires against a genuinely empty database, so
redeploying against an already-seeded one doesn't create duplicates.
Manual seeding is still available if you want it explicitly:

```bash
python -m scripts.seed                                        # seed all 3 scenarios
python -m scripts.seed 1                                      # seed only CASES[1] (Vantage Robotics)
uvicorn gateway.main:app --port 8001 &
uvicorn backend.app.main:app --port 8000 &                     # also auto-seeds all 3 if the DB is empty
```

Then either drive it through the API (see below) or run the scripted
walkthrough, which starts its own gateway/backend processes (auto-seeding
all three scenarios against the fresh demo database) and runs the full
narrative against the Trussell & Voss scenario specifically — selected by
name, not by list position, since `GET /case-files` orders newest-first
and seeding three scenarios means the "first" one returned is whichever
was seeded last, not necessarily this one:

```bash
python -m scripts.demo
```

This is the Build Order's "demo script" — the interview artifact, not just
the app. It runs normal triage → human approves most flags and **rejects
one** → a simulated Timeline Agent bypass attempt against the rejected
artifact (denied by Policy 1) → Timeline Agent → a compliant Report Agent
reaching `case_ready` → the deliberately-noncompliant Report Agent blocked
by Policy 2 → a summary of `PolicyDecisionLog` and `AuditLogEntry` → a live
tamper attempt on the audit log getting caught by the hash chain. Runs in
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
| `GET` | `/audit-log/verify` | walk the hash chain, report tampering if any |
| `GET` | `/policy-decisions?policy_name=&decision=` | gateway decision log |
| `POST` | `/agents/triage/run?case_file_id=` | run Triage Agent |
| `POST` | `/agents/timeline/run?case_file_id=` | run Timeline Agent |
| `POST` | `/agents/report/run?case_file_id=` | run (compliant) Report Agent |
| `POST` | `/agents/report/run-misbehaving?case_file_id=` | run the noncompliant variant + attempt case_ready |
| `POST` | `/agents/report/{id}/request-case-ready` | request the case_ready transition |
| `POST` | `/dev/seed` | seed one more case file on demand, randomly chosen from the 3 scenarios (demo-only, see below) |
| `POST` | `/dev/seed?with_triage=true` | same, then immediately runs the Triage Agent against it so it arrives with real `pending` flags |

`/dev/seed` is a portfolio-demo convenience, not a production pattern —
unauthenticated and unrate-limited. It's there so a demo run-through can be
reset to a clean state (a fresh set of `pending` flags to approve/reject)
without a full redeploy; it adds a new case file rather than overwriting,
so it's safe to call repeatedly. `with_triage=true` stops after triage
deliberately — chaining straight through to Timeline/Report would skip the
human approve/reject step the whole system exists to require.

## Tests

```bash
python -m pytest
```

`tests/test_acceptance.py` maps directly onto the CLAUDE.md checklist:
Policy 1 bypass denial (pending *and* rejected flags), Policy 2 blocking
the deliberately-noncompliant Report Agent, Policy 3's audit-failure
rollback (proving a rolled-back mutation leaves no row behind), the audit
hash chain verifying clean after normal activity and catching a direct
database tamper, and the full pipeline run through the real agent modules
end to end.

## Deploying (Railway)

This is two services from one repo, each with its own Railway config file
at the repo root:

1. **backend** — `railway.json` points Railway at
   `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
2. **gateway** — `railway.gateway.json` points Railway at
   `uvicorn gateway.main:app --host 0.0.0.0 --port $PORT`. Create a second
   Railway service from the same repo and set its config path to
   `railway.gateway.json` (Settings → Config-as-code) so it picks this up
   instead of the default `railway.json`.

Set `DATABASE_URL` (your Supabase connection string) and
`ANTHROPIC_API_KEY` on both services. Set `GATEWAY_URL` on the backend
service to the gateway service's internal Railway URL. Apply
`db/schema.sql` to your Supabase project before first run (or let the
SQLite fallback create tables automatically for a quick smoke test without
Supabase configured). No manual seeding step is required — the backend
auto-seeds the demo CaseFile on first boot against an empty database (see
"Running it" above); `POST /dev/seed` is there if you want to reset to a
clean run-through afterward.

## Explicitly out of scope

Per CLAUDE.md / the PRD's non-goals: no real forensic tool integration, no
multi-examiner workflows, no model fine-tuning, no court-admissibility
features, no policy versioning/diffing.
