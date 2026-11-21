"""Profiles (demo login users), scoped to one tenant."""

from typing import Any

from app.models.entities import Profile
from app.repositories.base import ScopedRepository


class ProfileRepository(ScopedRepository[Profile]):
    model = Profile

    async def create(self, **fields: Any) -> Profile:
        return await self._add(Profile(**fields))

    async def get(self, id: str) -> Profile | None:
        return await self._get(id)

    async def get_by_email(self, email: str) -> Profile | None:
        result = await self.session.execute(self._select(Profile.email == email))
        return result.scalar_one_or_none()
