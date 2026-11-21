"""Demo authentication (N1): turn a seeded profile into a signed token.

Only the three seeded demo profiles can log in, and the token is signed with the server secret,
which is never part of any response.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.entities import Profile
from app.repositories.profiles import ProfileRepository
from app.schemas.auth import TokenResponse, User


class DemoLoginRefused(Exception):
    """No such demo user, or the email and role named different users."""


def to_user(profile: Profile) -> User:
    return User(
        id=profile.id,
        email=profile.email,
        full_name=profile.full_name,
        role=profile.role,
        avatar_url=profile.avatar_url,
    )


async def demo_login(session: AsyncSession, email: str | None, role: str | None) -> TokenResponse:
    repo = ProfileRepository(session)
    profile = await repo.get_by_email(email) if email else await repo.get_first_by_role(role or "")
    if profile is None or (role is not None and profile.role != role):
        raise DemoLoginRefused
    token = create_access_token(profile.id, profile.role, email=profile.email)
    return TokenResponse(access_token=token, user=to_user(profile))


async def get_user(session: AsyncSession, profile_id: str) -> User | None:
    profile = await ProfileRepository(session).get(profile_id)
    return to_user(profile) if profile else None
