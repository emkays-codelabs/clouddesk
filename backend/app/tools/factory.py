"""Build registries from a `ToolContext`. The one place that decides which tools exist."""

from app.core.config import Settings
from app.tools.context import ToolContext
from app.tools.idempotency import DbIdempotencyStore
from app.tools.read_tools import READ_TOOL_NAMES, build_read_tools
from app.tools.registry import IdempotencyStore, ToolRegistry
from app.tools.write_tools import WRITE_TOOL_NAMES, build_write_tools

__all__ = [
    "READ_TOOL_NAMES",
    "WRITE_TOOL_NAMES",
    "build_default_registry",
    "build_read_registry",
]


def build_read_registry(
    ctx: ToolContext, settings: Settings | None = None, store: IdempotencyStore | None = None
) -> ToolRegistry:
    """A registry with only the read tools (what the MCP server exposes)."""
    registry = ToolRegistry(settings or ctx.settings, store=store)
    for tool in build_read_tools(ctx):
        registry.register(tool, idempotent=False)  # reads are always fresh, never replayed
    return registry


def build_default_registry(
    ctx: ToolContext, settings: Settings | None = None, store: IdempotencyStore | None = None
) -> ToolRegistry:
    """Every tool. Writes are recorded in `resolution_actions` so a retry never acts twice."""
    registry = ToolRegistry(
        settings or ctx.settings, store=store or DbIdempotencyStore(ctx.session_factory)
    )
    for tool in build_read_tools(ctx):
        registry.register(tool, idempotent=False)
    for tool in build_write_tools(ctx):
        registry.register(tool)
    return registry
