"""Generic governed-action executor.

Every agent-to-data call, agent-to-agent handoff, and status transition in
CaseLens runs through this one function. It is the physical enforcement
point: agents hold no database credentials at all, so there is no code path
by which an agent can perform a governed action without going through here.

Flow for a single governed action:
  1. Evaluate the action's resource-gating policy, if any (Policy 1 or
     Policy 2). If denied, the mutation in `perform` is skipped entirely.
  2. If allowed, run `perform(session)` — the actual DB mutation — inside
     the transaction.
  3. Record a PolicyDecisionLog row for the gating policy (or note "no
     gating policy applies" for actions Policy 1/2 don't target).
  4. Call the Audit Agent to write the AuditLogEntry for this action
     (allow or deny alike — Policy 3 applies to every action).
  5. Evaluate Policy 3 (audit-completeness) against what's actually in the
     transaction. If it holds, commit. If it doesn't — the Audit Agent
     failed — roll back everything from this request, including the
     mutation and the Policy 1/2 decision log, then write a fresh,
     minimal record of the rollback itself in a new transaction so the
     failure is not silently lost.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import celpy

from gateway.audit_agent import AuditLoggingFailed, entry_exists_for_request, log_action
from gateway.policy_engine import engine
from shared.audit_chain import append_entry
from shared.db.models import PolicyDecisionLog
from shared.db.session import SessionLocal

AUDIT_COMPLETENESS_POLICY = "require-audit-log-on-action"


@dataclass
class GateResult:
    allowed: bool
    request_id: str
    reason: str | None = None
    data: Any = None
    unsourced_claims: list | None = field(default=None)
    rolled_back: bool = False


async def execute_governed_action(
    *,
    actor: str,
    action: str,
    target_entity: str,
    case_file_id: str | None,
    request_summary: str,
    perform: Callable[[Any], Awaitable[Any]],
    gating_policy: str | None = None,
    gating_resource: dict | None = None,
    unsourced_claims: list | None = None,
    _force_audit_failure: bool = False,
) -> GateResult:
    request_id = str(uuid.uuid4())

    async with SessionLocal() as session:
        async with session.begin():
            allowed_by_gate = True
            gate_reason: str | None = None

            if gating_policy is not None:
                allowed_by_gate = engine.evaluate(gating_policy, resource=gating_resource)
                if not allowed_by_gate:
                    gate_reason = engine.reason(gating_policy)

                session.add(
                    PolicyDecisionLog(
                        policy_name=gating_policy,
                        request_summary=request_summary,
                        decision="allow" if allowed_by_gate else "deny",
                        reason=None if allowed_by_gate else gate_reason,
                        request_id=request_id,
                    )
                )

            result = None
            if allowed_by_gate:
                result = await perform(session)

            audit_failed = False
            try:
                await log_action(
                    session,
                    case_file_id=case_file_id,
                    actor=actor,
                    action=action,
                    target_entity=target_entity,
                    decision="allow" if allowed_by_gate else "deny",
                    reason=gate_reason,
                    request_id=request_id,
                    _force_failure=_force_audit_failure,
                )
            except AuditLoggingFailed:
                audit_failed = True

            audit_log_ok = False
            if not audit_failed:
                audit_log_ok = await entry_exists_for_request(session, request_id)

            policy3_holds = engine.evaluate(
                AUDIT_COMPLETENESS_POLICY,
                request={"id": request_id},
                extra_activation={"audit_log": celpy.json_to_cel({})},
                functions={"entry_created_for": lambda audit_log, req_id, _ok=audit_log_ok: _ok},
            )

            session.add(
                PolicyDecisionLog(
                    policy_name=AUDIT_COMPLETENESS_POLICY,
                    request_summary=request_summary,
                    decision="allow" if policy3_holds else "deny",
                    reason=None if policy3_holds else engine.reason(AUDIT_COMPLETENESS_POLICY),
                    request_id=request_id,
                )
            )

            if not policy3_holds:
                # Force a rollback of everything staged in this transaction
                # (the mutation, the Policy 1/2 decision log, the failed
                # audit attempt) by raising out of the `session.begin()`
                # block. The request_id travels with the exception so the
                # post-rollback record below can still be keyed to it.
                raise _RollbackSignal(request_id, request_summary)

        return GateResult(
            allowed=allowed_by_gate,
            request_id=request_id,
            reason=gate_reason,
            data=result,
            unsourced_claims=unsourced_claims if not allowed_by_gate else None,
        )


class _RollbackSignal(Exception):
    def __init__(self, request_id: str, request_summary: str):
        super().__init__(request_id)
        self.request_id = request_id
        self.request_summary = request_summary


async def _record_rollback(request_id: str, request_summary: str) -> None:
    """Persists a durable, independent record that a rollback happened.

    Written fresh, after the offending transaction has already been rolled
    back, so the failure itself is never lost even though its cause (the
    mutation + the failed audit attempt) was undone.
    """
    async with SessionLocal() as session:
        async with session.begin():
            session.add(
                PolicyDecisionLog(
                    policy_name=AUDIT_COMPLETENESS_POLICY,
                    request_summary=f"[rolled back] {request_summary}",
                    decision="deny",
                    reason=engine.reason(AUDIT_COMPLETENESS_POLICY),
                    request_id=request_id,
                )
            )
            await append_entry(
                session,
                case_file_id=None,
                actor="agentgateway",
                action="rollback",
                target_entity=request_id,
                decision="deny",
                reason=engine.reason(AUDIT_COMPLETENESS_POLICY),
                request_id=request_id,
            )


async def execute_governed_action_safe(**kwargs) -> GateResult:
    """Wraps execute_governed_action, catching the internal rollback signal
    and persisting a durable record of the rollback afterward."""
    try:
        return await execute_governed_action(**kwargs)
    except _RollbackSignal as signal:
        await _record_rollback(signal.request_id, signal.request_summary)
        return GateResult(
            allowed=False,
            request_id=signal.request_id,
            reason="Action rolled back: audit logging could not be verified.",
            rolled_back=True,
        )
