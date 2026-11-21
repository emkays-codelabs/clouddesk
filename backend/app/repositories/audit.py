"""Audit log rows."""

from __future__ import annotations

from typing import Any

from app.models.entities import AuditLog
from app.repositories.base import ScopedRepository


class AuditLogRepository(ScopedRepository[AuditLog]):
    model = AuditLog

    async def append(self, **fields: Any) -> AuditLog:
        return await self._add(AuditLog(**fields))

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        actor: str | None = None,
        action: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        stmt = self._select().order_by(AuditLog.created_at.desc())
        if actor:
            stmt = stmt.where(AuditLog.actor == actor)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return await self._page(stmt, page, page_size)
