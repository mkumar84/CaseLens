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
--
-- IDs are varchar(36) (not native uuid) and status/decision columns are
-- varchar (not native Postgres enums) to match shared/db/models.py exactly:
-- the app generates UUID strings in Python and validates status values at
-- the application layer, not the database layer. Drop-and-recreate below
-- is idempotent and safe to re-run.

drop table if exists policy_decision_log cascade;
drop table if exists audit_log_entries cascade;
drop table if exists report_drafts cascade;
drop table if exists timeline_entries cascade;
drop table if exists triage_flags cascade;
drop table if exists artifacts cascade;
drop table if exists case_files cascade;
drop type if exists case_file_status;
drop type if exists artifact_source_type;
drop type if exists triage_flag_status;
drop type if exists report_draft_status;
drop type if exists decision_type;

create table case_files (
    id varchar(36) primary key,
    name text not null,
    created_at timestamptz not null default now(),
    status varchar(20) not null default 'open'
);

create table artifacts (
    id varchar(36) primary key,
    case_file_id varchar(36) not null references case_files(id) on delete cascade,
    source_type varchar(20) not null,
    raw_content text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create table triage_flags (
    id varchar(36) primary key,
    artifact_id varchar(36) not null references artifacts(id) on delete cascade,
    rationale text not null,
    confidence_score numeric(4, 3) not null check (confidence_score >= 0 and confidence_score <= 1),
    status varchar(20) not null default 'pending',
    reviewed_by text,
    reviewed_at timestamptz,
    created_at timestamptz not null default now()
);

create table timeline_entries (
    id varchar(36) primary key,
    case_file_id varchar(36) not null references case_files(id) on delete cascade,
    artifact_id varchar(36) not null references artifacts(id),
    event_timestamp timestamptz not null,
    event_description text not null,
    created_by_agent text not null default 'timeline-agent',
    created_at timestamptz not null default now()
);

create table report_drafts (
    id varchar(36) primary key,
    case_file_id varchar(36) not null references case_files(id) on delete cascade,
    content text not null,
    citations jsonb not null default '[]'::jsonb, -- [{claim_id, artifact_id, claim_text}]
    citation_coverage_pct numeric(5, 2) not null default 0,
    status varchar(20) not null default 'draft',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table audit_log_entries (
    id varchar(36) primary key,
    case_file_id varchar(36) references case_files(id) on delete cascade,
    actor text not null, -- agent name | human user identifier
    action text not null,
    target_entity text not null,
    decision varchar(10) not null,
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
    id varchar(36) primary key,
    policy_name text not null,
    request_summary text not null,
    decision varchar(10) not null,
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
