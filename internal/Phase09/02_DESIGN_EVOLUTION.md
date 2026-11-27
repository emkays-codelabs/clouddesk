# Phase 9: system design evolution

> **Status of this phase:** in progress. Only P9-1 is done and checked locally; P9-2 to P9-8 are not started. Nothing is deployed.

---

## P9-1: Workflow schemas and the LLM layer

- **Schemas.** `backend/app/schemas/workflow.py` now holds the agent outputs (`Classification`, `SeverityAssessment`, `CustomerContext`, `PreviousCase`, `Diagnosis`, `ResolutionPlan`, `EscalationDecision`), `TokenUsage` and the full `WorkflowState` from the API contract. Every state field except the run identity is optional and extra keys are still allowed, so states saved earlier still load.
- **One door to a model.** `backend/app/core/llm.py` exposes `get_llm()` and `call_structured()`. `call_structured` caps temperature at 0.2, validates against the schema, sends an invalid reply back for repair at most twice, measures usage and latency, and raises only `LLMError` (carrying the usage spent). A static test fails if `openai` or `langchain_openai` is imported anywhere else.
- **Providers.** `fake` (default) is deterministic with cost 0.0 and accepts rule results as `hints`, because the core layer cannot import the agents layer. `openai` and `euron` use one OpenAI-compatible client; `euron` defaults to its euri endpoint and model `euri-reasoning`. `anthropic` raises a clear not-implemented error. One model, no tiers, no gateway (ADR-0010, D4 undecided).
- **Setting.** `LLM_BASE_URL` (empty default) joined `Settings`, `.env.example` and `CLAUDE.md` 10.1. `/settings` is unchanged.
- **Not done.** No real provider call has been made (no key yet); cost estimates for real models are a one-entry price table and 0.0 for unknown models.
