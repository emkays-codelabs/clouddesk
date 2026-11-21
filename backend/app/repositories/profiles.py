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

    async def get_first_by_role(self, role: str) -> Profile | None:
        # Oldest first, so the answer is stable when a role has several users.
        result = await self.session.execute(
            self._select(Profile.role == role).order_by(Profile.created_at, Profile.email).limit(1)
        )
        return result.scalar_one_or_none()
