# ADR-0009: Write-capable MCP servers

## Status

Accepted on 2026-11-27 (owner approval in chat). This is decision D3 in `CLAUDE.md` section 20. The decision is taken; nothing is built, and MCP stays read-only in v1 until a `TASKS.md` row builds it.

## Context

Upstream reaches back-office systems over MCP with scoped service tokens, including write tools over HTTP.
CloudDesk keeps MCP read-only and runs writes in process (see
[ADR-0004](0004-tools-run-in-process-through-one-registry.md)).

## Decision

A write tool may be exposed over MCP only behind scoped service tokens, only for tools the policy already approval-gates, and with the idempotency key, the approval record and the read-back verification holding across the network boundary. Writes keep running through `ToolRegistry`; MCP is a front door to it, not a second path.

## Consequences

If adopted: task P6-5 changes, there is a new deployable and a new token-scoping problem, and the
idempotency and approval guarantees must hold across a network boundary. If not adopted, MCP stays a
read-only introspection surface.
