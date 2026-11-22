"""Customers, their subscriptions and their workspaces."""

from __future__ import annotations

from typing import Any

from app.models.entities import Customer, Subscription, Workspace
from app.repositories.base import ScopedRepository, contains_any


class CustomerRepository(ScopedRepository[Customer]):
    model = Customer

    async def create(self, **fields: Any) -> Customer:
        return await self._add(Customer(**fields))

    async def get(self, id: str) -> Customer | None:
        return await self._get(id)

    async def get_by_email(self, email: str) -> Customer | None:
        result = await self.session.execute(self._select(Customer.email == email))
        return result.scalar_one_or_none()

    async def get_many(self, ids: list[str]) -> dict[str, Customer]:
        if not ids:
            return {}
        rows = await self.session.execute(self._select(Customer.id.in_(ids)))
        return {c.id: c for c in rows.scalars().all()}

    async def list(
        self, search: str | None = None, page: int = 1, page_size: int = 20
    ) -> tuple[list[Customer], int]:
        stmt = self._select().order_by(Customer.name, Customer.id)
        if search:
            stmt = stmt.where(contains_any(search, Customer.name, Customer.email, Customer.company))
        return await self._page(stmt, page, page_size)


class SubscriptionRepository(ScopedRepository[Subscription]):
    model = Subscription

    async def create(self, **fields: Any) -> Subscription:
        return await self._add(Subscription(**fields))

    async def get_for_customer(self, customer_id: str) -> Subscription | None:
        stmt = (
            self._select(Subscription.customer_id == customer_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class WorkspaceRepository(ScopedRepository[Workspace]):
    model = Workspace

    async def create(self, **fields: Any) -> Workspace:
        return await self._add(Workspace(**fields))

    async def get_for_customer(self, customer_id: str) -> Workspace | None:
        stmt = (
            self._select(Workspace.customer_id == customer_id)
            .order_by(Workspace.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get(self, id: str) -> Workspace | None:
        return await self._get(id)
