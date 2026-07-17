"""Audit Agent.

Writes the AuditLogEntry for every gateway-routed action, including denials.
Invoked internally by the gateway's action executor as a distinct step (not
inlined) so its failure is a real, detectable event: if this raises, the
executor's Policy 3 check sees no entry for the request id and rolls the
triggering action back.

`_force_failure` exists only so acceptance tests can prove the rollback path
works — it simulates the Audit Agent failing to log, e.g. a downstream outage.
It is never set by production code paths.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import AuditLogEntry


class AuditLoggingFailed(Exception):
    pass


async def log_action(
    session: AsyncSession,
    *,
    case_file_id: str | None,
    actor: str,
    action: str,
    target_entity: str,
    decision: str,
    reason: str | None,
    request_id: str,
    _force_failure: bool = False,
) -> AuditLogEntry:
    if _force_failure:
        raise AuditLoggingFailed(f"Audit Agent failed to log request {request_id}")

    entry = AuditLogEntry(
        case_file_id=case_file_id,
        actor=actor,
        action=action,
        target_entity=target_entity,
        decision=decision,
        reason=reason,
        request_id=request_id,
    )
    session.add(entry)
    await session.flush()
    return entry


async def entry_exists_for_request(session: AsyncSession, request_id: str) -> bool:
    from sqlalchemy import select

    result = await session.execute(
        select(AuditLogEntry.id).where(AuditLogEntry.request_id == request_id)
    )
    return result.first() is not None
