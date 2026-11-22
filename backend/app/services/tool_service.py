"""Tool introspection: what is registered and which tools need approval (F9)."""

from app.schemas.mcp import ToolInfo, ToolsResponse
from app.tools.context import build_context
from app.tools.factory import build_default_registry


def list_tools() -> ToolsResponse:
    """Every registered tool. The MCP server itself exposes only the read-only subset."""
    registry = build_default_registry(build_context())
    return ToolsResponse(tools=[ToolInfo(**t) for t in registry.list_tools()])
