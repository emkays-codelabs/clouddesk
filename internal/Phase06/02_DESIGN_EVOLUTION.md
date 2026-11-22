# Phase 6: system design evolution

> **Status of this phase:** in progress. P6-1 is implemented and checked locally; P6-2 to P6-5 are not started. Nothing is deployed.

---

## P6-1 · Tool registry and policy

- **Added:** `backend/app/tools/policy.py` and `registry.py`. `ToolPolicy` holds an explicit approval bit and a low/medium/high tier per tool; a tool not in the table always requires approval. Refunds also read `approval_required_for_refunds` and `max_refund_without_approval` (default 0, so any amount needs approval).
- **Flow:** `ToolRegistry.execute(name, args, approved)` checks approval, then provenance (named id and amount arguments must be in a trusted set the caller supplies, otherwise `provenance_failed`), then the idempotency key `ticket_id:tool:sha256(canonical args)`, then runs the tool under `TOOL_TIMEOUT_SECONDS`. Every failure becomes `ToolResult(ok=False)`; failures are not cached.
- **Boundaries:** The tools package imports only the config module from core; it calls no LLM and core does not import it.
- **Not built:** the `prohibited` tier (D2 undecided), a DB-backed idempotency store (P6-3, P11-4), read-back verification (placeholder field), and any real tool.
