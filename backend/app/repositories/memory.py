"""Long-term customer memory rows. Scrubbing and the confidence floor belong to memory/ (P8)."""

from typing import Any

from app.models.entities import CustomerMemory
from app.repositories.base import ScopedRepository
from app.schemas.common import MemoryType


class CustomerMemoryRepository(ScopedRepository[CustomerMemory]):
    model = CustomerMemory

    async def list_for_customer(self, customer_id: str, limit: int = 10) -> list[CustomerMemory]:
        stmt = (
            self._select(CustomerMemory.customer_id == customer_id)
            .order_by(CustomerMemory.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def exists(self, customer_id: str, memory_type: MemoryType, content: str) -> bool:
        stmt = self._select(
            CustomerMemory.customer_id == customer_id,
            CustomerMemory.memory_type == memory_type,
            CustomerMemory.content == content,
        ).limit(1)
        return (await self.session.execute(stmt)).first() is not None

    async def add(self, **fields: Any) -> CustomerMemory:
        return await self._add(CustomerMemory(**fields))

    async def delete_for_customer(self, customer_id: str) -> int:
        return await self._delete_where(CustomerMemory.customer_id == customer_id)
