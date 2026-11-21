"""The one repository with no tenant scope: it manages the tenants table itself."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ensure(self, tenant_id: str, name: str) -> Tenant:
        row = (
            await self.session.execute(select(Tenant).where(Tenant.id == tenant_id))
        ).scalar_one_or_none()
        if row is None:
            row = Tenant(id=tenant_id, name=name)
            self.session.add(row)
            await self.session.flush()
        return row
