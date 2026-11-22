"""P6-5: the MCP server exposes the read tools only; write tools never appear on it (ADR-0004)."""

import ast
from pathlib import Path

from mcp.client import Client

from app.tools.factory import READ_TOOL_NAMES, WRITE_TOOL_NAMES
from integrations.mcp.server import build_server

ROOT = Path(__file__).resolve().parents[2]


async def test_server_lists_exactly_the_read_tools(tool_env):
    async with Client(build_server(tool_env)) as client:
        listed = await client.list_tools()
    names = {t.name for t in listed.tools}
    assert names == set(READ_TOOL_NAMES)


async def test_no_write_tool_is_exposed_or_callable(tool_env):
    server = build_server(tool_env)
    async with Client(server) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        assert names.isdisjoint(WRITE_TOOL_NAMES)
        for name in WRITE_TOOL_NAMES:
            result = await client.call_tool(name, {})
            assert result.is_error, f"{name} must not be callable over MCP"
    assert tool_env.integrations.billing.calls == []


async def test_tools_carry_their_docstring_as_description(tool_env):
    async with Client(build_server(tool_env)) as client:
        listed = await client.list_tools()
    assert all(t.description and t.description.strip() for t in listed.tools)


async def test_a_read_tool_call_goes_through_the_registry_and_returns_data(tool_env, seed_id):
    cid = seed_id("customer", "cust-northwind")
    async with Client(build_server(tool_env)) as client:
        result = await client.call_tool("get_customer", {"customer_id": cid})
    assert not result.is_error
    assert "Priya Raman" in str(result.content)


async def test_a_failed_tool_is_reported_as_an_error_result(tool_env):
    async with Client(build_server(tool_env)) as client:
        result = await client.call_tool("get_customer", {"customer_id": "nope"})
    assert result.is_error


def test_server_module_never_references_a_write_tool_builder():
    src = (ROOT / "integrations" / "mcp" / "server.py").read_text(encoding="utf-8")
    names = {n.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Attribute)
    }
    assert not names & {"build_write_tools", "build_default_registry", *WRITE_TOOL_NAMES}


def test_client_example_exists():
    assert (ROOT / "integrations" / "mcp" / "client_example.py").is_file()
