# ADR-0009: Write-capable MCP servers

## Status

Proposed. This is decision D3 in `CLAUDE.md` section 20. It is not taken, and nothing may be built on it.

## Context

Upstream reaches back-office systems over MCP with scoped service tokens, including write tools over HTTP.
CloudDesk keeps MCP read-only and runs writes in process (see
[ADR-0004](0004-tools-run-in-process-through-one-registry.md)).

## Decision

Not taken. The question is whether any write tool should move behind an MCP server.

## Consequences

If adopted: task P6-5 changes, there is a new deployable and a new token-scoping problem, and the
idempotency and approval guarantees must hold across a network boundary. If not adopted, MCP stays a
read-only introspection surface.
