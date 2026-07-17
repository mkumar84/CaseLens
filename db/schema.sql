-- CaseLens backend schema
-- Target: Supabase (Postgres). Run via Supabase SQL editor or `psql $DATABASE_URL -f db/schema.sql`.
--
-- Design note: this schema backs two physically separate connection pools:
--   1. `backend` (human/system-of-record API) — full read access, plus writes for
--      human actions (case creation, triage-flag approve/reject).
--   2. `gateway` (control-plane) — the ONLY process permitted to write
--      triage_flags (agent-created rows), timeline_entries, report_drafts,
--      audit_log_entries and policy_decision_log. Agents never hold a
--      connection to this database at all; they only speak HTTP to the
--      gateway. See gateway/README section in root README.md.

create extension if not exists "pgcrypto";

create type case_file_status as enum ('open', 'case_ready', 'closed');
create type artifact_source_type as enum ('document', 'device', 'comms');
create type triage_flag_status as enum ('pending', 'approved', 'rejected');
create type report_draft_status as enum ('draft', 'case_ready', 'blocked');
create type decision_type as enum ('allow', 'deny');

create table case_files (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now(),
    status case_file_status not null default 'open'
);

create table artifacts (
    id uuid primary key default gen_random_uuid(),
    case_file_id uuid not null references case_files(id) on delete cascade,
    source_type artifact_source_type not null,
    raw_content text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table triage_flags (
    id uuid primary key default gen_random_uuid(),
    artifact_id uuid not null references artifacts(id) on delete cascade,
    rationale text not null,
    confidence_score numeric(4, 3) not null check (confidence_score >= 0 and confidence_score <= 1),
    status triage_flag_status not null default 'pending',
    reviewed_by text,
    reviewed_at timestamptz,
    created_at timestamptz not null default now()
);

create table timeline_entries (
    id uuid primary key default gen_random_uuid(),
    case_file_id uuid not null references case_files(id) on delete cascade,
    artifact_id uuid not null references artifacts(id),
    event_timestamp timestamptz not null,
    event_description text not null,
    created_by_agent text not null default 'timeline-agent',
    created_at timestamptz not null default now()
);

create table report_drafts (
    id uuid primary key default gen_random_uuid(),
    case_file_id uuid not null references case_files(id) on delete cascade,
    content text not null,
    citations jsonb not null default '[]'::jsonb, -- [{claim_id, artifact_id, claim_text}]
    citation_coverage_pct numeric(5, 2) not null default 0,
    status report_draft_status not null default 'draft',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table audit_log_entries (
    id uuid primary key default gen_random_uuid(),
    case_file_id uuid references case_files(id) on delete cascade,
    actor text not null, -- agent name | human user identifier
    action text not null,
    target_entity text not null,
    decision decision_type not null,
    reason text,
    request_id text not null,
    timestamp timestamptz not null default now(),
    -- Tamper-evident hash chain (PRD Goal #4). Application-assigned (not a
    -- DB serial/identity) so the same appender logic works unchanged on
    -- SQLite in dev/test. entry_hash = sha256(seq, prev_hash, id,
    -- case_file_id, actor, action, target_entity, decision, reason,
    -- request_id) — see shared/audit_chain.py. The unique constraint on
    -- seq turns a concurrent double-append into an immediate DB error
    -- rather than a silently forked chain.
    seq bigint not null unique,
    prev_hash char(64) not null,
    entry_hash char(64) not null unique
);

create table policy_decision_log (
    id uuid primary key default gen_random_uuid(),
    policy_name text not null,
    request_summary text not null,
    decision decision_type not null,
    reason text,
    request_id text not null,
    timestamp timestamptz not null default now()
);

create index idx_artifacts_case_file on artifacts(case_file_id);
create index idx_triage_flags_artifact on triage_flags(artifact_id);
create index idx_triage_flags_status on triage_flags(status);
create index idx_timeline_entries_case_file on timeline_entries(case_file_id);
create index idx_report_drafts_case_file on report_drafts(case_file_id);
create index idx_audit_log_case_file on audit_log_entries(case_file_id);
create index idx_audit_log_request_id on audit_log_entries(request_id);
create index idx_policy_decision_request_id on policy_decision_log(request_id);
