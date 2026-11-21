"""Tickets and their messages."""

from __future__ import annotations

from typing import Any

from app.models.entities import Ticket, TicketMessage
from app.repositories.base import ScopedRepository, contains_any
from app.schemas.common import Severity, TicketStatus


class TicketRepository(ScopedRepository[Ticket]):
    model = Ticket

    async def create(self, **fields: Any) -> Ticket:
        return await self._add(Ticket(**fields))

    async def get(self, id: str) -> Ticket | None:
        return await self._get(id)

    async def get_by_number(self, ticket_number: str) -> Ticket | None:
        result = await self.session.execute(self._select(Ticket.ticket_number == ticket_number))
        return result.scalar_one_or_none()

    async def list(
        self,
        status: TicketStatus | None = None,
        severity: Severity | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Ticket], int]:
        stmt = self._select().order_by(Ticket.created_at.desc())
        if status is not None:
            stmt = stmt.where(Ticket.status == status)
        if severity is not None:
            stmt = stmt.where(Ticket.severity == severity)
        if search:
            stmt = stmt.where(contains_any(search, Ticket.subject, Ticket.ticket_number))
        return await self._page(stmt, page, page_size)

    async def list_for_customer(
        self, customer_id: str, exclude_ticket_id: str | None = None, limit: int = 10
    ) -> list[Ticket]:
        stmt = self._select(Ticket.customer_id == customer_id)
        if exclude_ticket_id is not None:
            stmt = stmt.where(Ticket.id != exclude_ticket_id)
        stmt = stmt.order_by(Ticket.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def update(self, id: str, **fields: Any) -> Ticket | None:
        return await self._update_where(id, **fields)


class TicketMessageRepository(ScopedRepository[TicketMessage]):
    model = TicketMessage

    async def add(self, **fields: Any) -> TicketMessage:
        return await self._add(TicketMessage(**fields))

    async def list_for_ticket(self, ticket_id: str) -> list[TicketMessage]:
        stmt = self._select(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at)
        return list((await self.session.execute(stmt)).scalars().all())
