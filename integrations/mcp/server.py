"""Read-only MCP server (P6-5). Exposes the read tools and nothing else.

Every call runs through `ToolRegistry.execute`, so timeouts, never-raise and policy still apply.
The registry here is built by `build_read_registry`, which cannot contain a write tool; write
tools stay in-process behind approval (ADR-0004, ADR-0009: write-capable MCP is not decided).
Run with `make mcp` (stdio).
"""

import functools
from typing import Any

from mcp.server.mcpserver import MCPServer

from app.tools.context import ToolContext, build_context
from app.tools.factory import build_read_registry
from app.tools.read_tools import build_read_tools


def build_server(ctx: ToolContext) -> MCPServer:
    registry = build_read_registry(ctx)
    server = MCPServer("clouddesk-readonly")
    for fn in build_read_tools(ctx):
        server.add_tool(_through_registry(registry, fn), name=fn.__name__)
    return server


def _through_registry(registry: Any, fn: Any) -> Any:
    @functools.wraps(fn)  # keeps the signature (the tool's input schema) and the docstring
    async def call(**kwargs: Any) -> Any:
        result = await registry.execute(fn.__name__, kwargs)
        if not result.ok:
            raise ValueError(result.error)
        return result.data

    return call


def main() -> None:
    build_server(build_context()).run("stdio")


if __name__ == "__main__":
    main()
