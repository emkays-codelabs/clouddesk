# ADR-0004: Tools run in process through one registry

## Status

Accepted. Differs from upstream ADR-02. The question of write-capable MCP servers is open as
[ADR-0009](0009-write-capable-mcp-servers.md).

## Context

Upstream ADR-02 puts all tool access behind MCP servers, with scoped service tokens and write tools over
HTTP. CloudDesk v1 must run offline on one machine, and its integrations are mocks: no real email, no real
refunds.

## Decision

Every tool is an async `@tool` function, and all execution goes through `ToolRegistry.execute(name, args,
approved=...)`. Unknown tools require approval. A tool exception becomes `ToolResult(ok=False)` and never
crashes the graph. MCP exposes the read-only tools only.

## Consequences

- One code path serves auto-resolved and human-approved actions, so the approval gate cannot be bypassed.
- Every write carries an idempotency key and is read back, so a retried or resumed run cannot act twice.
- Tool arguments need provenance: an id or amount comes from customer context or an earlier tool result,
  never from ticket text.
- There is no network boundary between the agents and the tools, so the registry is the only control.
