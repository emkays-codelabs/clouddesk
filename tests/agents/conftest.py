"""Fixtures for agent tests: a throwaway seeded database and a tool context over it."""

import pytest

from app.core.config import get_settings
from app.core.database import create_tables, dispose_engine, get_engine, get_sessionmaker
from app.services.seed_service import _id, bootstrap_demo_data  # noqa: PLC2701
from integrations.factory import get_integrations, reset_integrations


@pytest.fixture
async def tool_env(tmp_path):
    """(ToolContext, helpers) over a private seeded SQLite file."""
    from app.tools.context import ToolContext

    engine = get_engine(f"sqlite+aiosqlite:///{tmp_path / 'agents.db'}")
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


@pytest.fixture(scope="session")
def demo_tickets():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "sample_data"
    rows = json.loads((root / "tickets.json").read_text("utf-8"))
    return {t["ticket_number"]: t for t in rows}


@pytest.fixture
def text_of(demo_tickets):
    def _text(number: str) -> str:
        t = demo_tickets[number]
        return f"{t['subject']}\n{t['body']}"

    return _text
