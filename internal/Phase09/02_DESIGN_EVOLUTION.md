# Phase 9: system design evolution

> **Status of this phase:** in progress. P9-1 to P9-5 are done and checked locally; P9-6 to P9-8 are not started. Nothing is deployed.

---

## P9-1: Workflow schemas and the LLM layer

- **Schemas.** `backend/app/schemas/workflow.py` now holds the agent outputs (`Classification`, `SeverityAssessment`, `CustomerContext`, `PreviousCase`, `Diagnosis`, `ResolutionPlan`, `EscalationDecision`), `TokenUsage` and the full `WorkflowState` from the API contract. Every state field except the run identity is optional and extra keys are still allowed, so states saved earlier still load.
- **One door to a model.** `backend/app/core/llm.py` exposes `get_llm()` and `call_structured()`. `call_structured` caps temperature at 0.2, validates against the schema, sends an invalid reply back for repair at most twice, measures usage and latency, and raises only `LLMError` (carrying the usage spent). A static test fails if `openai` or `langchain_openai` is imported anywhere else.
- **Providers.** `fake` (default) is deterministic with cost 0.0 and accepts rule results as `hints`, because the core layer cannot import the agents layer. `openai` and `euron` use one OpenAI-compatible client; `euron` defaults to its euri endpoint and model `euri-reasoning`. `anthropic` raises a clear not-implemented error. One model, no tiers, no gateway (ADR-0010, D4 undecided).
- **Setting.** `LLM_BASE_URL` (empty default) joined `Settings`, `.env.example` and `CLAUDE.md` 10.1. `/settings` is unchanged.
- **Not done.** No real provider call has been made (no key yet); cost estimates for real models are a one-entry price table and 0.0 for unknown models.

---

## P9-2 to P9-5: the four investigation agents

- **Shape.** `agents/specialists/` holds `SupervisorAgent`, `CustomerAgent`, `KnowledgeAgent` and `TroubleshootingAgent`. Each `run`-style method returns `(result, status, usage, ms, calls)`, where `status` is `ok` or `fallback` and `calls` are `ToolCallRecord`s from `common.py`, so Phase 10 nodes can record telemetry. Planned, not built: the nodes themselves.
- **Supervisor.** The rule category wins when a rule matched; the model decides only when none did. Severity is the model's answer raised, never lowered, by `rule_severity`. A failed model call falls back to the rules. The injection scan travels on `Understanding.injection`. Ticket text reaches the model only through `wrap_untrusted`; the closing ticket summary is deterministic.
- **Customer.** No model call. Customer, subscription and history come through the read-tool registry; the workspace and up to 10 memory notes through their repository and the memory service. `get_customer` and `get_ticket_history` outputs gained fields (additive) so the full schemas validate.
- **Knowledge.** Evidence comes from `search_docs`; any chunk that trips `scan_for_injection` is dropped. Similar cases are Jaccard overlap against `sample_data/previous_resolutions.json` only (resolved tickets in the database carry no resolution text).
- **Troubleshooting.** The model drafts a `Diagnosis`; a per-category playbook and an active incident from `check_service_status` enrich it, and steps are numbered. The model failure fallback is the playbook alone.
- **Not done.** No real model call; the service name per category is a small fixed map.
