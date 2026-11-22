"""Dependencies the tools need, passed in explicitly (no globals).

A `ToolContext` is built once by the caller (the app, a test, the MCP server) and handed to the
builder functions, so a tool never reaches for a module-level session or setting.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from integrations.factory import Integrations

# (query, top_k, mode) -> evidence dicts; the default goes through the retriever and its cache.
DocSearch = Callable[[str, int, str], Awaitable[list[dict[str, Any]]]]


async def default_doc_search(query: str, top_k: int, mode: str) -> list[dict[str, Any]]:
    from app.schemas.knowledge import SearchRequest
    from app.services import knowledge_service

    response = await knowledge_service.search(
        SearchRequest(query=query, top_k=top_k, mode=mode)  # type: ignore[arg-type]
    )
    return [e.model_dump() for e in response.results]


@dataclass
class ToolContext:
    session_factory: async_sessionmaker[AsyncSession]
    settings: Settings
    integrations: Integrations
    search: DocSearch = field(default=default_doc_search)


def build_context() -> ToolContext:
    """The context for the running process: its database, its settings, the demo mocks."""
    from app.core.config import get_settings
    from app.core.database import get_sessionmaker
    from integrations.factory import get_integrations

    settings = get_settings()
    return ToolContext(
        session_factory=get_sessionmaker(),
        settings=settings,
        integrations=get_integrations(settings.demo_mode),
    )
