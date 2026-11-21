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


async def test_get_first_by_role_is_oldest_first_and_tenant_scoped(session, tenants):
    demo, other = tenants
    await ProfileRepository(session, other).create(
        email="root@o.io", full_name="O", role=Role.admin
    )
    repo = ProfileRepository(session, demo)
    first = await repo.create(email="a@x.io", full_name="A", role=Role.agent)
    await repo.create(email="b@x.io", full_name="B", role=Role.agent)
    await session.commit()

    assert (await repo.get_first_by_role("agent")).id == first.id
    assert await repo.get_first_by_role("admin") is None  # only the other tenant has an admin
