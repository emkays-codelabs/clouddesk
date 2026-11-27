"""Checkpointer selection (CLAUDE.md 7.3): where a paused graph keeps its state.

Does: `InMemorySaver` when `CHECKPOINT_DB_PATH` is `:memory:` (tests), otherwise an
`AsyncSqliteSaver` on that file, so a run paused for approval survives a request and can be resumed
under the same `thread_id`. The SQLite saver needs an open connection, so `open_checkpointer` is an
async context manager that closes it.
Must NOT: know about tickets or approvals; it only stores graph state.
"""

import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

MEMORY = ":memory:"


def is_memory(path: str) -> bool:
    return path.strip() in ("", MEMORY)


def checkpointer_kind(path: str) -> str:
    """Which saver a path selects: `memory` or `sqlite` (what the tests assert)."""
    return "memory" if is_memory(path) else "sqlite"


@asynccontextmanager
async def open_checkpointer(path: str) -> AsyncIterator[BaseCheckpointSaver]:
    """Yield the saver for `path`; an SQLite connection is opened and closed around the block."""
    if is_memory(path):
        yield InMemorySaver()
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(path, isolation_level=None)
    try:
        # AsyncSqliteSaver 3.x expects these attributes on the connection it is given.
        saver = AsyncSqliteSaver(conn)
        await saver.setup()
        yield saver
    finally:
        await conn.close()


__all__ = ["MEMORY", "checkpointer_kind", "is_memory", "open_checkpointer", "sqlite3"]
