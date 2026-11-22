"""Example MCP client: starts the read-only server over stdio, lists its tools and calls one.

Run from the repository root, after `make seed`:
    uv run python -m integrations.mcp.client_example
"""

import asyncio
import os
import sys

from mcp.client import Client
from mcp.client.stdio import StdioServerParameters


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "integrations.mcp.server"],
        env={**os.environ, "PYTHONPATH": "backend"},
    )
    async with Client(params) as client:
        listed = await client.list_tools()
        for tool in listed.tools:
            print(f"{tool.name}: {(tool.description or '').splitlines()[0]}")
        result = await client.call_tool("check_service_status", {})
        print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
