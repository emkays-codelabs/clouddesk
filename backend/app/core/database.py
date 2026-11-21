"""Async engine, session factory and table creation. Imports models, never agents/."""

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.models.entities import Base

_engines: dict[str, AsyncEngine] = {}


def _make_engine(url: str) -> AsyncEngine:
    parsed = make_url(url)
    is_sqlite = parsed.get_backend_name() == "sqlite"
    if is_sqlite and parsed.database and parsed.database != ":memory:":
        # SQLite will not create the directory itself.
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(url)
    if is_sqlite:

        @event.listens_for(engine.sync_engine, "connect")
        def _foreign_keys_on(dbapi_conn, _record) -> None:
            # SQLite ignores foreign keys unless asked; Postgres would catch the bugs it hides.
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def get_engine(url: str | None = None) -> AsyncEngine:
    url = url or get_settings().database_url
    if url not in _engines:
        _engines[url] = _make_engine(url)
    return _engines[url]


def get_sessionmaker(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine or get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


async def create_tables(engine: AsyncEngine | None = None) -> None:
    engine = engine or get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    engines = list(_engines.values())
    _engines.clear()
    for engine in engines:
        await engine.dispose()
