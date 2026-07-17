"""Tamper-evident audit log (PRD Goal #4).

Every AuditLogEntry is linked to the one before it: entry_hash is a SHA-256
digest over this row's own fields plus the previous row's entry_hash. Edit,
delete, or reorder any historical row and every entry_hash computed after it
stops matching — `verify_chain` walks the whole table and reports exactly
where the chain first breaks.

This is the single place that constructs AuditLogEntry rows. Both the
gateway (agent-triggered actions, including denials and rollback records)
and the backend (the one human action in this build, approve/reject) call
`append_entry` so there is one coherent chain across every actor, not one
chain per writer.
"""

import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import AuditLogEntry, new_uuid

GENESIS_HASH = "0" * 64


def _compute_hash(
    *,
    seq: int,
    prev_hash: str,
    entry_id: str,
    case_file_id: str | None,
    actor: str,
    action: str,
    target_entity: str,
    decision: str,
    reason: str | None,
    request_id: str,
) -> str:
    # Deliberately excludes the DateTime `timestamp` column: SQLite round-trips
    # tz-aware datetimes as naive ones, which would make verification depend
    # on driver-specific datetime formatting rather than on the log's actual
    # content. `entry_id` (a fresh UUID minted before insert) gives each row
    # unique entropy instead.
    payload = "|".join(
        [
            str(seq),
            prev_hash,
            entry_id,
            case_file_id or "",
            actor,
            action,
            target_entity,
            decision,
            reason or "",
            request_id,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def append_entry(
    session: AsyncSession,
    *,
    case_file_id: str | None,
    actor: str,
    action: str,
    target_entity: str,
    decision: str,
    reason: str | None,
    request_id: str,
) -> AuditLogEntry:
    last = (
        await session.execute(select(AuditLogEntry).order_by(AuditLogEntry.seq.desc()).limit(1))
    ).scalar_one_or_none()
    seq = (last.seq + 1) if last else 1
    prev_hash = last.entry_hash if last else GENESIS_HASH
    entry_id = new_uuid()

    entry_hash = _compute_hash(
        seq=seq,
        prev_hash=prev_hash,
        entry_id=entry_id,
        case_file_id=case_file_id,
        actor=actor,
        action=action,
        target_entity=target_entity,
        decision=decision,
        reason=reason,
        request_id=request_id,
    )

    entry = AuditLogEntry(
        id=entry_id,
        case_file_id=case_file_id,
        actor=actor,
        action=action,
        target_entity=target_entity,
        decision=decision,
        reason=reason,
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
        seq=seq,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
    )
    session.add(entry)
    await session.flush()
    return entry


async def verify_chain(session: AsyncSession) -> dict:
    rows = (await session.execute(select(AuditLogEntry).order_by(AuditLogEntry.seq))).scalars().all()
    prev_hash = GENESIS_HASH
    for row in rows:
        expected = _compute_hash(
            seq=row.seq,
            prev_hash=prev_hash,
            entry_id=row.id,
            case_file_id=row.case_file_id,
            actor=row.actor,
            action=row.action,
            target_entity=row.target_entity,
            decision=row.decision,
            reason=row.reason,
            request_id=row.request_id,
        )
        if row.prev_hash != prev_hash or row.entry_hash != expected:
            return {"valid": False, "checked": len(rows), "broken_at_seq": row.seq}
        prev_hash = row.entry_hash
    return {"valid": True, "checked": len(rows), "broken_at_seq": None}
