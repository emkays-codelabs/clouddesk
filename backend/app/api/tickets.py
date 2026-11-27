"""Ticket routes (docs/design/06_API_CONTRACT.md, Tickets). HTTP only: rules live in the service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import Principal, get_current_user, require_role
from app.repositories.base import MAX_PAGE_SIZE
from app.schemas.common import ApprovalStatus, Channel, Severity, TicketStatus
from app.schemas.ticket import (
    Ticket,
    TicketCreate,
    TicketEscalate,
    TicketMessage,
    TicketPage,
    TicketReply,
    TicketRequestInfo,
    TicketUpdate,
)
from app.schemas.ticket_detail import TicketDetail
from app.schemas.workflow import Escalation
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(get_current_user)])

Session = Annotated[AsyncSession, Depends(get_session)]
Agent = Annotated[Principal, Depends(require_role("agent"))]


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found")


@router.post(
    "",
    response_model=Ticket,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("agent"))],
)
async def create_ticket(body: TicketCreate, session: Session) -> Ticket:
    try:
        return await ticket_service.create_ticket(session, body)
    except ticket_service.CustomerNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Customer not found") from None


@router.get("", response_model=TicketPage)
async def list_tickets(
    session: Session,
    status: TicketStatus | None = None,
    severity: Severity | None = None,
    search: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    channel: Channel | None = None,
    assigned_to: str | None = None,
    approval_status: ApprovalStatus | None = None,
    escalated: bool | None = None,
) -> TicketPage:
    return await ticket_service.list_tickets(
        session,
        status=status,
        severity=severity,
        search=search,
        page=page,
        page_size=page_size,
        channel=channel,
        assigned_to=assigned_to,
        approval_status=approval_status,
        escalated=escalated,
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(ticket_id: str, session: Session) -> TicketDetail:
    try:
        return await ticket_service.get_ticket(session, ticket_id)
    except ticket_service.TicketNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found") from None


@router.post(
    "/{ticket_id}/reply", response_model=TicketMessage, status_code=status.HTTP_201_CREATED
)
async def reply(ticket_id: str, body: TicketReply, session: Session, user: Agent) -> TicketMessage:
    try:
        return await ticket_service.reply(session, ticket_id, body, user)
    except ticket_service.TicketNotFound:
        raise _not_found() from None


@router.post(
    "/{ticket_id}/request-info", response_model=TicketMessage, status_code=status.HTTP_201_CREATED
)
async def request_info(
    ticket_id: str, body: TicketRequestInfo, session: Session, user: Agent
) -> TicketMessage:
    try:
        return await ticket_service.request_info(session, ticket_id, body, user)
    except ticket_service.TicketNotFound:
        raise _not_found() from None


@router.post(
    "/{ticket_id}/escalate", response_model=Escalation, status_code=status.HTTP_201_CREATED
)
async def escalate(
    ticket_id: str, body: TicketEscalate, session: Session, user: Agent
) -> Escalation:
    try:
        return await ticket_service.escalate(session, ticket_id, body, user)
    except ticket_service.TicketNotFound:
        raise _not_found() from None


@router.patch("/{ticket_id}", response_model=Ticket)
async def update_ticket(
    ticket_id: str, body: TicketUpdate, session: Session, user: Agent
) -> Ticket:
    try:
        return await ticket_service.update_ticket(session, ticket_id, body, user)
    except ticket_service.TicketNotFound:
        raise _not_found() from None
