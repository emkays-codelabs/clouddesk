"""Approval requests and escalations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa

from app.models.entities import ApprovalRequest, Escalation
from app.repositories.base import ScopedRepository
from app.schemas.common import ApprovalStatus, EscalationStatus


class ApprovalRepository(ScopedRepository[ApprovalRequest]):
    model = ApprovalRequest

    async def create(self, **fields: Any) -> ApprovalRequest:
        return await self._add(ApprovalRequest(**fields))

    async def get(self, id: str) -> ApprovalRequest | None:
        return await self._get(id)

    async def list(self, status: ApprovalStatus | None = None) -> list[ApprovalRequest]:
        stmt = self._select().order_by(ApprovalRequest.created_at.desc())
        if status is not None:
            stmt = stmt.where(ApprovalRequest.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def decide(
        self, id: str, status: ApprovalStatus, decided_by: str, note: str | None
    ) -> ApprovalRequest | None:
        # Only a pending row can be decided, so a second decision returns None (the 409 later).
        row = (
            await self.session.execute(
                self._select(
                    ApprovalRequest.id == id, ApprovalRequest.status == ApprovalStatus.pending
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        row.status = status
        row.decided_by = decided_by
        row.decision_note = note
        row.decided_at = datetime.now(UTC)
        await self.session.flush()
        return row

    async def count_pending(self) -> int:
        stmt = (
            sa.select(sa.func.count())
            .select_from(ApprovalRequest)
            .where(
                ApprovalRequest.tenant_id == self.tenant_id,
                ApprovalRequest.status == ApprovalStatus.pending,
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_expired(self, now: datetime) -> list[ApprovalRequest]:
        # Compared in SQL: SQLite hands datetimes back naive, so a Python comparison would fail.
        stmt = self._select(
            ApprovalRequest.status == ApprovalStatus.pending,
            ApprovalRequest.expires_at.is_not(None),
            ApprovalRequest.expires_at < sa.literal(now, ApprovalRequest.expires_at.type),
        ).order_by(ApprovalRequest.expires_at)
        return list((await self.session.execute(stmt)).scalars().all())


class EscalationRepository(ScopedRepository[Escalation]):
    model = Escalation

    async def create(self, **fields: Any) -> Escalation:
        return await self._add(Escalation(**fields))

    async def get(self, id: str) -> Escalation | None:
        return await self._get(id)

    async def latest_for_ticket(self, ticket_id: str) -> Escalation | None:
        stmt = (
            self._select(Escalation.ticket_id == ticket_id)
            .order_by(Escalation.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list(self, status: EscalationStatus | None = None) -> list[Escalation]:
        stmt = self._select().order_by(Escalation.created_at.desc())
        if status is not None:
            stmt = stmt.where(Escalation.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_open(self) -> int:
        stmt = (
            sa.select(sa.func.count())
            .select_from(Escalation)
            .where(
                Escalation.tenant_id == self.tenant_id,
                Escalation.status == EscalationStatus.open,
            )
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def update_status(self, id: str, status: EscalationStatus) -> Escalation | None:
        return await self._update_where(id, status=status)
