"""Approvals and escalations as a person sees them (F9, F10, FR-24).

Does: list and read approval requests, and `decide`: record the decision on every pending request of
the run, then resume the paused graph with it (approved runs the actions through the registry,
rejected goes to escalation). Also lists escalations and updates their status.
Must NOT: talk HTTP, execute an action itself (the resumed graph does, through the registry), or
decide a request that is not pending or whose run is not paused (409).
"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_sessionmaker
from app.core.observability import WorkflowTracer
from app.core.security import Principal
from app.repositories.approvals import ApprovalRepository, EscalationRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.repositories.workflow import WorkflowRunRepository
from app.schemas.approval import ApprovalDecisionResult, ApprovalRequest
from app.schemas.common import (
    ApprovalStatus,
    EscalationStatus,
    MessageRole,
    TicketStatus,
    WorkflowEventType,
    WorkflowStatus,
)
from app.schemas.workflow import Escalation, PlannedAction
from app.services import workflow_service
from app.services.ticket_service import _to_escalation, _to_workflow


class ApprovalNotFound(Exception):
    pass


class EscalationNotFound(Exception):
    pass


def _actor(user: Principal) -> str:
    return user.email or user.sub


async def _to_schema(session: AsyncSession, row) -> ApprovalRequest:
    ticket = await TicketRepository(session).get(row.ticket_id)
    return ApprovalRequest(
        id=row.id,
        ticket_id=row.ticket_id,
        ticket_number=ticket.ticket_number if ticket else "",
        workflow_id=row.workflow_id,
        action=PlannedAction.model_validate(row.action),
        risk_level=row.risk_level,
        reason=row.reason,
        requested_by=row.requested_by,
        status=row.status,
        decided_by=row.decided_by,
        decision_note=row.decision_note,
        created_at=row.created_at,
        decided_at=row.decided_at,
    )


async def list_approvals(
    session: AsyncSession, status: ApprovalStatus | None = None
) -> list[ApprovalRequest]:
    rows = await ApprovalRepository(session).list(status)
    return [await _to_schema(session, r) for r in rows]


async def get_approval(session: AsyncSession, approval_id: str) -> ApprovalRequest:
    row = await ApprovalRepository(session).get(approval_id)
    if row is None:
        raise ApprovalNotFound
    return await _to_schema(session, row)


async def decide(
    session: AsyncSession,
    approval_id: str,
    decision: ApprovalStatus,
    note: str | None,
    user: Principal,
) -> ApprovalDecisionResult:
    approvals = ApprovalRepository(session)
    row = await approvals.get(approval_id)
    if row is None:
        raise ApprovalNotFound
    run = await WorkflowRunRepository(session).get(row.workflow_id)
    if (
        row.status != ApprovalStatus.pending
        or run is None
        or run.status != WorkflowStatus.waiting_for_approval
    ):
        raise workflow_service.RunConflict("The run is not paused on this approval.")

    run_id, ticket_id = run.id, row.ticket_id
    for pending in await approvals.list(ApprovalStatus.pending):
        if pending.workflow_id == run_id:
            await approvals.decide(pending.id, decision, _actor(user), note)
    ticket_status = (
        TicketStatus.in_progress if decision == ApprovalStatus.approved else TicketStatus.escalated
    )
    await TicketRepository(session).update(
        ticket_id, status=ticket_status, approval_status=decision
    )
    await session.commit()
    await WorkflowTracer(get_sessionmaker(), run_id, ticket_id).event(
        WorkflowEventType.approval_resolved,
        node="human_approval",
        message=f"approval {decision.value} by {_actor(user)}",
        payload={"decision": decision.value, "note": note},
    )

    await workflow_service.resume_workflow(run_id, decision.value, note)

    session.expire_all()
    refreshed = await approvals.get(approval_id)
    run_after = await WorkflowRunRepository(session).get(run_id)
    return ApprovalDecisionResult(
        approval=await _to_schema(session, refreshed if refreshed else row),
        workflow=_to_workflow(run_after) if run_after else None,
    )


async def expire_overdue(session: AsyncSession, now: datetime | None = None) -> int:
    """FR-24: an approval nobody decided expires and the run escalates; it never executes."""
    approvals = ApprovalRepository(session)
    expired = await approvals.list_expired(now or datetime.now(UTC))
    runs = {r.workflow_id for r in expired}
    for row in expired:
        await approvals.decide(row.id, ApprovalStatus.rejected, "system", "Approval timed out.")
    await session.commit()
    for run_id in runs:
        await workflow_service.resume_workflow(run_id, ApprovalStatus.rejected.value, "timeout")
    return len(expired)


async def list_escalations(
    session: AsyncSession, status: EscalationStatus | None = None
) -> list[Escalation]:
    tickets = TicketRepository(session)
    out: list[Escalation] = []
    for row in await EscalationRepository(session).list(status):
        ticket = await tickets.get(row.ticket_id)
        out.append(_to_escalation(row, ticket.ticket_number if ticket else ""))
    return out


async def update_escalation(
    session: AsyncSession,
    escalation_id: str,
    status: EscalationStatus,
    note: str | None,
    user: Principal,
) -> Escalation:
    repo = EscalationRepository(session)
    row = await repo.update_status(escalation_id, status)
    if row is None:
        raise EscalationNotFound
    ticket = await TicketRepository(session).get(row.ticket_id)
    if note and ticket is not None:
        await TicketMessageRepository(session).add(
            ticket_id=ticket.id,
            role=MessageRole.system,
            author_name=_actor(user),
            body=f"Escalation {status.value}: {note}",
            internal=True,
        )
    await session.commit()
    return _to_escalation(row, ticket.ticket_number if ticket else "")
