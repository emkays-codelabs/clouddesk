"""Ticket use cases: create, list, and read one with its context (F1).

Creating a ticket only records it and its first message; starting the workflow is a separate,
explicit action (`POST /tickets/{id}/run`).
"""

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import entities
from app.repositories.approvals import EscalationRepository
from app.repositories.customers import CustomerRepository, SubscriptionRepository
from app.repositories.tickets import TicketMessageRepository, TicketRepository
from app.repositories.workflow import ResolutionActionRepository, WorkflowRunRepository
from app.schemas.common import MessageRole, Severity, TicketStatus
from app.schemas.customer import Customer, Subscription
from app.schemas.ticket import Ticket, TicketCreate, TicketMessage, TicketPage, TicketSummary
from app.schemas.ticket_detail import TicketDetail
from app.schemas.workflow import Escalation, ResolutionAction, WorkflowState

HISTORY_LIMIT = 10
NUMBER_ATTEMPTS = 3


class TicketNotFound(Exception):
    pass


class CustomerNotFound(Exception):
    pass


def _summary_fields(ticket: entities.Ticket, customer_name: str) -> dict[str, Any]:
    fields = {
        name: getattr(ticket, name)
        for name in TicketSummary.model_fields
        if name != "customer_name"
    }
    fields["customer_name"] = customer_name
    return fields


def _to_summary(ticket: entities.Ticket, customer_name: str) -> TicketSummary:
    return TicketSummary(**_summary_fields(ticket, customer_name))


def _to_ticket(ticket: entities.Ticket, customer_name: str) -> Ticket:
    return Ticket(
        **_summary_fields(ticket, customer_name),
        body=ticket.body,
        assigned_to=ticket.assigned_to,
        resolved_at=ticket.resolved_at,
        tags=list(ticket.tags or []),
    )


def _to_workflow(run: entities.WorkflowRun) -> WorkflowState:
    # The saved state keeps whatever the graph wrote; the run's own columns are authoritative.
    data = dict(run.state or {})
    data.update(
        workflow_id=run.id,
        ticket_id=run.ticket_id,
        status=run.status,
        current_node=run.current_node,
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=run.duration_ms,
    )
    return WorkflowState.model_validate(data)


def _to_escalation(row: entities.Escalation, ticket_number: str) -> Escalation:
    return Escalation(
        id=row.id,
        ticket_id=row.ticket_id,
        ticket_number=ticket_number,
        reason=row.reason,
        priority=row.priority,
        status=row.status,
        created_by=row.created_by,
        assigned_team=row.assigned_team,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


async def create_ticket(session: AsyncSession, body: TicketCreate) -> Ticket:
    customer = await CustomerRepository(session).get(body.customer_id)
    if customer is None:
        raise CustomerNotFound
    tickets = TicketRepository(session)
    for attempt in range(NUMBER_ATTEMPTS):
        try:
            ticket = await tickets.create(
                ticket_number=await tickets.next_ticket_number(),
                customer_id=customer.id,
                subject=body.subject,
                body=body.body,
                channel=body.channel,
                status=TicketStatus.new,
            )
            await TicketMessageRepository(session).add(
                ticket_id=ticket.id,
                role=MessageRole.customer,
                author_name=customer.name,
                body=body.body,
            )
            await session.commit()
            return _to_ticket(ticket, customer.name)
        except IntegrityError:
            # Two creates read the same "next" number; the unique key refused the loser.
            await session.rollback()
            if attempt == NUMBER_ATTEMPTS - 1:
                raise
    raise AssertionError("unreachable")


async def list_tickets(
    session: AsyncSession,
    *,
    status: TicketStatus | None,
    severity: Severity | None,
    search: str | None,
    page: int,
    page_size: int,
) -> TicketPage:
    rows, total = await TicketRepository(session).list(
        status=status, severity=severity, search=search, page=page, page_size=page_size
    )
    names = await CustomerRepository(session).get_many(list({t.customer_id for t in rows}))
    return TicketPage(
        items=[_to_summary(t, names[t.customer_id].name) for t in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_ticket(session: AsyncSession, ticket_id: str) -> TicketDetail:
    tickets = TicketRepository(session)
    ticket = await tickets.get(ticket_id)
    if ticket is None:
        raise TicketNotFound
    customer = await CustomerRepository(session).get(ticket.customer_id)
    if customer is None:  # a ticket without its customer is a broken row, not a client error
        raise LookupError(f"customer missing for ticket {ticket.ticket_number}")
    subscription = await SubscriptionRepository(session).get_for_customer(customer.id)
    messages = await TicketMessageRepository(session).list_for_ticket(ticket.id)
    previous = await tickets.list_for_customer(
        customer.id, exclude_ticket_id=ticket.id, limit=HISTORY_LIMIT
    )
    run = await WorkflowRunRepository(session).latest_for_ticket(ticket.id)
    actions = await ResolutionActionRepository(session).list_for_ticket(ticket.id)
    escalation = await EscalationRepository(session).latest_for_ticket(ticket.id)
    return TicketDetail(
        **_to_ticket(ticket, customer.name).model_dump(),
        messages=[TicketMessage.model_validate(m) for m in messages],
        customer=Customer.model_validate(customer),
        subscription=Subscription.model_validate(subscription) if subscription else None,
        history=[_to_summary(t, customer.name) for t in previous],
        workflow=_to_workflow(run) if run else None,
        resolution_actions=[ResolutionAction.model_validate(a) for a in actions],
        escalation=_to_escalation(escalation, ticket.ticket_number) if escalation else None,
    )
