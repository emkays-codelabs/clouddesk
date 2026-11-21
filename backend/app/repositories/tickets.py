"""Tickets and their messages."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa

from app.models.entities import Ticket, TicketMessage
from app.repositories.base import ScopedRepository, contains_any
from app.schemas.common import Category, Severity, TicketStatus

TICKET_PREFIX = "CD-"
FIRST_TICKET_NUMBER = 1001


class TicketRepository(ScopedRepository[Ticket]):
    model = Ticket

    async def create(self, **fields: Any) -> Ticket:
        return await self._add(Ticket(**fields))

    async def get(self, id: str) -> Ticket | None:
        return await self._get(id)

    async def get_by_number(self, ticket_number: str) -> Ticket | None:
        result = await self.session.execute(self._select(Ticket.ticket_number == ticket_number))
        return result.scalar_one_or_none()

    async def next_ticket_number(self) -> str:
        """The next `CD-NNNN`, one past the highest number in this tenant (1001 when empty)."""
        # Cast the numeric suffix: as text, CD-10000 would sort below CD-1013.
        suffix = sa.cast(sa.func.substr(Ticket.ticket_number, len(TICKET_PREFIX) + 1), sa.Integer)
        stmt = sa.select(sa.func.max(suffix)).where(
            Ticket.tenant_id == self.tenant_id, Ticket.ticket_number.like(f"{TICKET_PREFIX}%")
        )
        highest = (await self.session.execute(stmt)).scalar_one_or_none()
        return f"{TICKET_PREFIX}{max(highest or 0, FIRST_TICKET_NUMBER - 1) + 1}"

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

    async def _count(self, *criteria: Any) -> int:
        stmt = (
            sa.select(sa.func.count())
            .select_from(Ticket)
            .where(Ticket.tenant_id == self.tenant_id, *criteria)
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_open(self) -> int:
        """Tickets that are neither resolved nor closed."""
        return await self._count(Ticket.status.not_in([TicketStatus.resolved, TicketStatus.closed]))

    async def count_resolved_since(self, since: datetime) -> int:
        return await self._count(
            Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed]),
            Ticket.resolved_at >= sa.literal(since, Ticket.resolved_at.type),
        )

    async def _count_by(self, column: Any) -> dict[Any, int]:
        stmt = (
            sa.select(column, sa.func.count())
            .where(Ticket.tenant_id == self.tenant_id, column.is_not(None))
            .group_by(column)
        )
        return {key: n for key, n in (await self.session.execute(stmt)).all()}

    async def count_by_severity(self) -> dict[Severity, int]:
        return await self._count_by(Ticket.severity)

    async def count_by_category(self) -> dict[Category, int]:
        return await self._count_by(Ticket.category)

    async def resolution_spans(self) -> list[tuple[datetime, datetime]]:
        """(created_at, resolved_at) of every ticket that has been resolved."""
        stmt = sa.select(Ticket.created_at, Ticket.resolved_at).where(
            Ticket.tenant_id == self.tenant_id, Ticket.resolved_at.is_not(None)
        )
        return [(c, r) for c, r in (await self.session.execute(stmt)).all()]


class TicketMessageRepository(ScopedRepository[TicketMessage]):
    model = TicketMessage

    async def add(self, **fields: Any) -> TicketMessage:
        return await self._add(TicketMessage(**fields))

    async def list_for_ticket(self, ticket_id: str) -> list[TicketMessage]:
        stmt = self._select(TicketMessage.ticket_id == ticket_id).order_by(TicketMessage.created_at)
        return list((await self.session.execute(stmt)).scalars().all())
