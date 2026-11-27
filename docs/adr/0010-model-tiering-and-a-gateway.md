# ADR-0010: Model tiering behind a gateway (in-process router, no gateway service)

## Status

Accepted in a limited form on 2026-11-27, on the owner's explicit decision: an in-process router, not a separate
gateway service. This is decision D4 in `CLAUDE.md` section 20 and relates to upstream ADR-05. It is built as
tasks P9-9 (the router) and P9-10 (Euron embeddings) in `TASKS.md`.

## Context

Upstream routes calls to small, medium and large models through a gateway with failover and a circuit
breaker, which also gives multi-cloud portability and cost tracking. CloudDesk's `get_llm()` returns one
model, with a `fake` provider for offline use.

## Decision

CloudDesk adds tiers and a failover chain, and does not add a gateway service.

- **Router.** `backend/app/core/llm_router.py` maps three tiers to Euron models: `fast` = `euri-chat-fast`
  (Supervisor), `smart` = `euri-chat-smart` (Resolution, Escalation), `reasoning` = `euri-reasoning`
  (Troubleshooting). Each tier's model is `LLM_MODEL_FAST`, `LLM_MODEL_SMART` or `LLM_MODEL_REASONING`, then
  `LLM_MODEL`, then the tier default.
- **Failover.** `reasoning` falls back to `smart`, then to `fast`; a tier never moves upward. A per-model
  circuit breaker opens after 5 failures in 60 s and skips that model for 60 s.
- **Recording.** `call_structured(..., tier=...)` (default `smart`) reports the tier asked for, the tier and
  model that answered, and the tokens used. The `fake` provider ignores tiers, so tests stay offline.
- **Not built.** A separate gateway service, per-tenant routing, and cost-based routing. Cost per ticket is
  still tracked, never an input to a decision.

## Consequences

Easier: cheap calls (classification, severity) use the fast model, a failing model does not stop a run, and
an operator can move one tier to another model through a setting. Harder: the router is code in the backend
process, so its breaker state is per process and resets on restart; there is no shared view across
replicas, which a gateway would give. No gateway service is a new failure mode avoided, not a feature lost
for v1. The Euron endpoint is the first external service; tests never call it (a socket guard blocks it)
and every client is monkeypatched. No real Euron call had been made when this record was updated.
