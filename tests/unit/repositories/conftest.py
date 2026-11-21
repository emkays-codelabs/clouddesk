import pytest

from app.core.database import create_tables, dispose_engine, get_engine, get_sessionmaker
from app.models.entities import DEMO_TENANT_ID, Tenant

OTHER_TENANT_ID = "00000000-0000-4000-8000-000000000002"


@pytest.fixture
async def engine(tmp_path):
    eng = get_engine(f"sqlite+aiosqlite:///{tmp_path / 'repo.db'}")
    await create_tables(eng)
    yield eng
    # Windows keeps the file open until the engine is disposed.
    await dispose_engine()


@pytest.fixture
async def session(engine):
    async with get_sessionmaker(engine)() as s:
        yield s


@pytest.fixture
async def tenants(session):
    session.add(Tenant(id=DEMO_TENANT_ID, name="Demo"))
    session.add(Tenant(id=OTHER_TENANT_ID, name="Other"))
    await session.commit()
    return DEMO_TENANT_ID, OTHER_TENANT_ID
