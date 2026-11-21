"""API test helpers."""

import pytest


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """A private SQLite file for one test, for tests that count rows across the whole table.

    The default test database is shared by the session, so counts there depend on test order.
    Must run before `client`, which seeds the database at startup.
    """
    from app.core.config import get_settings

    url = f"sqlite+aiosqlite:///{(tmp_path / 'api.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()
    # Windows keeps the file open until the engine is disposed.
    import asyncio

    from app.core.database import dispose_engine

    asyncio.run(dispose_engine())
