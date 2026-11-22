"""Shared fixtures for tool tests: a throwaway seeded database and a tool context over it."""

import pytest

from app.core.config import get_settings
from app.core.database import create_tables, dispose_engine, get_engine, get_sessionmaker
from app.services.seed_service import _id, bootstrap_demo_data  # noqa: PLC2701
from integrations.factory import get_integrations, reset_integrations


@pytest.fixture
async def tool_env(tmp_path):
    """(ToolContext, helpers) over a private seeded SQLite file."""
    from app.tools.context import ToolContext

    engine = get_engine(f"sqlite+aiosqlite:///{tmp_path / 'tools.db'}")
    await create_tables(engine)
    sessionmaker = get_sessionmaker(engine)
    settings = get_settings()
    report = await bootstrap_demo_data(sessionmaker, settings.sample_data_dir)
    assert report.loaded
    reset_integrations()
    ctx = ToolContext(
        session_factory=sessionmaker,
        settings=settings,
        integrations=get_integrations(demo_mode=True),
    )
    yield ctx
    reset_integrations()
    await dispose_engine()


@pytest.fixture
def seed_id():
    return _id
