"""Ticket routes (docs/design/06_API_CONTRACT.md, Tickets). HTTP only: rules live in the service."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import get_current_user, require_role
from app.repositories.base import MAX_PAGE_SIZE
from app.schemas.common import Severity, TicketStatus
from app.schemas.ticket import Ticket, TicketCreate, TicketPage
from app.schemas.ticket_detail import TicketDetail
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(get_current_user)])

Session = Annotated[AsyncSession, Depends(get_session)]


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
) -> TicketPage:
    return await ticket_service.list_tickets(
        session, status=status, severity=severity, search=search, page=page, page_size=page_size
    )


@router.get("/{ticket_id}", response_model=TicketDetail)
async def get_ticket(ticket_id: str, session: Session) -> TicketDetail:
    try:
        return await ticket_service.get_ticket(session, ticket_id)
    except ticket_service.TicketNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found") from None
