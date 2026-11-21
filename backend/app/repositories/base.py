"""Tenant-scoped repository base.

Every read goes through `_select`, which adds the tenant filter, and every insert is stamped with
the repository's tenant. SQLite has no RLS, so on the demo database this filter is the boundary.

Repositories flush and never commit: the caller (a service, or the seed bootstrap) owns the
transaction. A caller that forgets to commit loses its writes.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import DEMO_TENANT_ID, Base

MAX_PAGE_SIZE = 100
_last_stamp = datetime.min.replace(tzinfo=UTC)


def _now() -> datetime:
    # The Windows clock ticks about every 15 ms, so two inserts can read the same time. Force a
    # strictly increasing stamp so insertion order is always recoverable.
    global _last_stamp
    stamp = datetime.now(UTC)
    if stamp <= _last_stamp:
        stamp = _last_stamp + timedelta(microseconds=1)
    _last_stamp = stamp
    return stamp


def contains_any(term: str, *columns: Any) -> sa.ColumnElement[bool]:
    # lower()+contains is portable across SQLite and Postgres; autoescape guards % and _.
    needle = term.lower()
    return sa.or_(*(sa.func.lower(c).contains(needle, autoescape=True) for c in columns))


class ScopedRepository[ModelT: Base]:
    model: ClassVar[type[Base]]

    def __init__(self, session: AsyncSession, tenant_id: str = DEMO_TENANT_ID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def _select(self, *extra: Any) -> sa.Select[Any]:
        return sa.select(self.model).where(self.model.tenant_id == self.tenant_id, *extra)  # type: ignore[attr-defined]

    async def _get(self, id: str) -> ModelT | None:
        result = await self.session.execute(self._select(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def _add(self, obj: ModelT) -> ModelT:
        current = getattr(obj, "tenant_id", None)
        if current is not None and current != self.tenant_id:
            raise ValueError("object belongs to another tenant")
        obj.tenant_id = self.tenant_id  # type: ignore[attr-defined]
        # SQLite's CURRENT_TIMESTAMP has whole-second resolution; set microseconds here so rows
        # inserted in the same second still sort.
        if getattr(obj, "created_at", None) is None:
            obj.created_at = _now()  # type: ignore[attr-defined]
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def _update_where(self, id: str, **values: Any) -> ModelT | None:
        row = await self._get(id)
        if row is None:
            return None
        for key, value in values.items():
            setattr(row, key, value)
        await self.session.flush()
        return row

    async def _delete_where(self, *criteria: Any) -> int:
        stmt = sa.delete(self.model).where(
            self.model.tenant_id == self.tenant_id,  # type: ignore[attr-defined]
            *criteria,
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def _page(
        self, stmt: sa.Select[Any], page: int = 1, page_size: int = 20
    ) -> tuple[list[ModelT], int]:
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))
        page = max(1, page)
        total = (
            await self.session.execute(sa.select(sa.func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = await self.session.execute(stmt.limit(page_size).offset((page - 1) * page_size))
        return list(rows.scalars().all()), total
