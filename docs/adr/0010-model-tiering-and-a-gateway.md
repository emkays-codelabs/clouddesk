# ADR-0010: Model tiering behind a gateway

## Status

Proposed. This is decision D4 in `CLAUDE.md` section 20 and relates to upstream ADR-05. It is not taken.

## Context

Upstream routes calls to small, medium and large models through a gateway with failover and a circuit
breaker, which also gives multi-cloud portability and cost tracking. CloudDesk's `get_llm()` returns one
model, with a `fake` provider for offline use.

## Decision

Not taken. The question is whether to add tiers and a gateway.

## Consequences

If adopted: task P9-1 and the cost target change, and a new failure mode (gateway down) appears. If not
adopted: every call uses one model, cost per ticket is higher than a tiered design could reach, and
provider failover is the operator's problem. Cost per ticket is tracked and alerted on either way, never an
input to a decision.
