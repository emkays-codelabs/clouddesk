# Phase 6: system design evolution

> **Status of this phase:** all five tasks (P6-1 to P6-5) are implemented and checked locally; the four phase documents are not yet written. Nothing is deployed.

---

## P6-1 · Tool registry and policy

- **Added:** `backend/app/tools/policy.py` and `registry.py`. `ToolPolicy` holds an explicit approval bit and a low/medium/high tier per tool; a tool not in the table always requires approval. Refunds also read `approval_required_for_refunds` and `max_refund_without_approval` (default 0, so any amount needs approval).
- **Flow:** `ToolRegistry.execute(name, args, approved)` checks approval, then provenance (named id and amount arguments must be in a trusted set the caller supplies, otherwise `provenance_failed`), then the idempotency key `ticket_id:tool:sha256(canonical args)`, then runs the tool under `TOOL_TIMEOUT_SECONDS`. Every failure becomes `ToolResult(ok=False)`; failures are not cached.
- **Boundaries:** The tools package imports only the config module from core; it calls no LLM and core does not import it.
- **Not built:** the `prohibited` tier (D2 undecided), a DB-backed idempotency store (P6-3, P11-4), read-back verification (placeholder field), and any real tool.

## P6-4 · Mock integrations

- **Added:** `integrations/protocols.py` (four `Protocol`s: `EmailSender`, `BillingService`, `WorkspaceAdmin`, `TicketNotifier`), `integrations/mock/services.py` (in-memory adapters that record every call; the billing mock is idempotent on its key and can read a refund back) and `integrations/factory.py` (`get_integrations(demo_mode)` returns one shared bundle of mocks, and raises outside demo mode because v1 has no real adapter).
- **Boundaries:** the factory takes `demo_mode` as a plain argument, so `integrations/` imports nothing from `app`; a test fails if anything under `backend/app/core` imports `integrations`.
- **Not built:** any real adapter; nothing calls the mocks until P6-3.

## P6-2 · Read-only support tools

- **Added:** `backend/app/tools/read_tools.py` (five async tools built by `build_read_tools(ctx)`, docstring is the description, documented return shapes, a missing record raises `LookupError` which the registry turns into `ok=False`), `backend/app/tools/context.py` (`ToolContext` carries the session factory, settings, integration mocks and a doc-search callable, so no tool uses a global) and `backend/app/tools/factory.py` (`build_read_registry`).
- **Flow:** each call opens its own session through the context, reads through repositories and returns plain data; `search_docs` goes through `knowledge_service.search`, so it uses the hybrid retriever and the Redis cache.
- **Change to the registry:** `register(..., idempotent=False)` skips the idempotency store, so reads always return fresh data.
- **Not built:** write tools (P6-3) and the MCP server (P6-5).

## P6-3 · Approval-gated write tools

- **Added:** `backend/app/tools/write_tools.py` (four tools built by `build_write_tools(ctx)`), `backend/app/tools/idempotency.py` (`DbIdempotencyStore`, which persists each successful action in `resolution_actions` with its key, arguments, result and verification) and `build_default_registry` in `backend/app/tools/factory.py`.
- **Flow:** policy decides approval; the registry then checks provenance, requires a workflow run id for recorded tools, looks the key up in the store, runs the tool, and stores the result. A write tool returns `Verified(data, verification)`: it reads its own record back (ticket row, escalation row, mock billing refund, mock workspace setting). A failed read-back returns `ok=False` and is not stored.
- **Refunds:** the subscription must belong to the customer, and the amount must be positive; the mock billing adapter is also idempotent on its own key.
- **Changes to the registry:** the store protocol is async, `execute` takes `workflow_id`, and `Verified` carries the read-back.
- **Not built:** the approval workflow around these tools (Phase 11) and any real billing adapter.

## P6-5 · MCP read-only server and `/mcp/tools`

- **Added:** `integrations/mcp/server.py` (`build_server(ctx)` registers only the read tools on an `MCPServer`; each wrapper keeps the tool's signature and docstring and calls `ToolRegistry.execute`, so a failed result becomes an MCP error result), `integrations/mcp/client_example.py` (stdio client), the `make mcp` target, `backend/app/api/mcp.py` with `backend/app/services/tool_service.py` and `backend/app/schemas/mcp.py` (`GET /api/v1/mcp/tools` lists all nine registered tools with `requires_approval`), and the `integrations/` COPY in `backend/Dockerfile`.
- **Boundary:** the server builds its registry with `build_read_registry`, which cannot hold a write tool; a test lists the server's tools and tries to call each write tool. The HTTP listing shows write tools too, because it describes the registry, not the MCP surface. Write-capable MCP (D3, ADR-0009) is not decided and not built.
- **Dependency:** `mcp` 2.3 (the 2.x `MCPServer`, not the 1.x `FastMCP`).
- **Not built:** an authenticated or network MCP transport; the server speaks stdio only.
