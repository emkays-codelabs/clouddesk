import pytest
from sqlalchemy.exc import IntegrityError

from app.repositories.profiles import ProfileRepository
from app.schemas.common import Role


async def test_get_by_email_is_exact(session, tenants):
    repo = ProfileRepository(session)
    p = await repo.create(email="sam@x.io", full_name="Sam", role=Role.agent)
    await session.commit()
    assert (await repo.get_by_email("sam@x.io")).id == p.id
    assert (await repo.get(p.id)).role == Role.agent
    assert await repo.get_by_email("sam@x") is None
    assert await repo.get_by_email("SAM@x.io") is None


async def test_email_is_unique_per_tenant(session, tenants):
    repo = ProfileRepository(session)
    await repo.create(email="sam@x.io", full_name="Sam")
    with pytest.raises(IntegrityError):
        await repo.create(email="sam@x.io", full_name="Sam2")
