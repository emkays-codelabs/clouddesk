# Phase 9: system design evolution

> **Status of this phase:** complete and validated locally. All ten tasks (P9-1 to P9-10) are done; the graph that joins the agents is Phase 10. P9-9 added the in-process Euron router and P9-10 the Euron embeddings provider (ADR 0010, accepted in limited form). Nothing is deployed.

---

## P9-1: Workflow schemas and the LLM layer

- **Schemas.** `backend/app/schemas/workflow.py` now holds the agent outputs (`Classification`, `SeverityAssessment`, `CustomerContext`, `PreviousCase`, `Diagnosis`, `ResolutionPlan`, `EscalationDecision`), `TokenUsage` and the full `WorkflowState` from the API contract. Every state field except the run identity is optional and extra keys are still allowed, so states saved earlier still load.
- **One door to a model.** `backend/app/core/llm.py` exposes `get_llm()` and `call_structured()`. `call_structured` caps temperature at 0.2, validates against the schema, sends an invalid reply back for repair at most twice, measures usage and latency, and raises only `LLMError` (carrying the usage spent). A static test fails if `openai` or `langchain_openai` is imported anywhere else.
- **Providers.** `fake` (default) is deterministic with cost 0.0 and accepts rule results as `hints`, because the core layer cannot import the agents layer. `openai` and `euron` use one OpenAI-compatible client; `euron` defaults to its euri endpoint. `anthropic` raises a clear not-implemented error. When P9-1 was written there was one model, no tiers and no gateway; P9-9 below added in-process tiers (ADR-0010, accepted in a limited form).
- **Setting.** `LLM_BASE_URL` (empty default) joined `Settings`, `.env.example` (removed, then re-created 2026-11-27 as a placeholders-only template) and `CLAUDE.md` 10.1. `/settings` is unchanged.
- **Not done at the time.** No real provider call had been made (no key yet), and cost estimates for real models were a one-entry price table with 0.0 for unknown models. Both changed later: real Euron calls were made on 2026-11-27, and unknown prices now report `unavailable` (see the QA section at the end).

---

## P9-2 to P9-5: the four investigation agents

- **Shape.** `agents/specialists/` holds `SupervisorAgent`, `CustomerAgent`, `KnowledgeAgent` and `TroubleshootingAgent`. Each `run`-style method returns `(result, status, usage, ms, calls)`, where `status` is `ok` or `fallback` and `calls` are `ToolCallRecord`s from `common.py`, so Phase 10 nodes can record telemetry. The nodes themselves were built in Phase 10.
- **Supervisor.** The rule category wins when a rule matched; the model decides only when none did. Severity is the model's answer raised, never lowered, by `rule_severity`. A failed model call falls back to the rules. The injection scan travels on `Understanding.injection`. Ticket text reaches the model only through `wrap_untrusted`; the closing ticket summary is deterministic.
- **Customer.** No model call. Customer, subscription and history come through the read-tool registry; the workspace and up to 10 memory notes through their repository and the memory service. `get_customer` and `get_ticket_history` outputs gained fields (additive) so the full schemas validate.
- **Knowledge.** Evidence comes from `search_docs`; any chunk that trips `scan_for_injection` is dropped. Similar cases are Jaccard overlap against `sample_data/previous_resolutions.json` only (resolved tickets in the database carry no resolution text).
- **Troubleshooting.** The model drafts a `Diagnosis`; a per-category playbook and an active incident from `check_service_status` enrich it, and steps are numbered. The model failure fallback is the playbook alone.
- **Not done at the time.** No real model call (made later, on Euron); the service name per category is a small fixed map.

---

## P9-6: the Resolution agent

- **Actions are policy, not prose.** `ResolutionAgent.plan_actions` is the only source of `ResolutionPlan.actions`; whatever actions a model returns are discarded. A seat refund is planned for a billing ticket that asks for one, with `customer_id`, `subscription_id` and the amount (unused seats times the per-seat price) computed from the subscription and workspace, and each argument is checked with `validate_provenance` before it is planned. A workspace setting reset is planned only when the ticket names one. A policy escalation plans nothing. Each action carries `requires_approval` from `ToolPolicy`, and one `update_ticket` sets the status.
- **Grounded reply.** The model drafts wording; `_ground_response` keeps only draft sentences the evidence and diagnosis steps support, then adds the steps and the cited article titles. `validate_customer_output` runs; a groundedness miss is revised once (steps and citation only); a second miss or any leak replaces the reply with a holding message and writes `OUTPUT_VALIDATION_FAILED` into the internal notes, which `reply_failed_validation` reads, so the Phase 10 risk node can escalate.
- **Not done at the time.** Nothing is executed here (the execute node came in Phase 10) and no real model call had been made.

## P9-7: the Escalation agent

- **Policy first.** A matching escalation rule names the team and no model is called. Otherwise a model escalation is kept only at high or critical severity with confidence of 0.6 or more; doubt (below 0.6) on a high or critical ticket escalates to Tier 2 support; anything else, including a failed model call, does not escalate. The decision is recorded through `create_escalation` in the registry, so a retry adds no second row.

## P9-8: the evaluation dataset

- `datasets/eval_cases.json` holds 16 cases: every demo ticket plus three text cases (an enterprise outage, an invoice question, an API token). Each has an expected category, escalation flag, article slug and action tools. The test rejects an invalid category or a missing article and checks that the labels agree with the policy rules. The metric thresholds that use it are Phase 14.


## P9-9: the in-process model router

- **Why in process.** Upstream routes calls through a gateway with failover. The owner accepted a limited form on 2026-11-27 (ADR-0010): the same behaviour inside the backend, with no separate gateway service to run.
- **What it does.** `backend/app/core/llm_router.py` defines three tiers, `fast`, `smart` and `reasoning`. Each tier's model is its own setting (`LLM_MODEL_FAST`, `LLM_MODEL_SMART`, `LLM_MODEL_REASONING`), else `LLM_MODEL`, else the tier default (`euri-chat-fast`, `euri-chat-smart`, `euri-reasoning`). A tier falls only to cheaper ones: reasoning, then smart, then fast. A per-model circuit breaker opens after five failures inside 60 seconds and stays open for 60 seconds, so a failing model is not called on every request. If every model in the chain fails the router raises one `RouterError`, which `call_structured` maps to `LLMError`.
- **Who asks for which tier.** Classification and severity ask for `fast`, the diagnosis for `reasoning`, and the resolution plan and escalation judgement for `smart`; `call_structured` takes a `tier` argument and non-tiered providers ignore it.
- **Verified.** `tests/unit/test_llm_router.py` and `tests/agents/test_agent_tiers.py` offline; on 2026-11-27 the router served real calls on Euron. Not verified: a real fallback during a provider outage, and the breaker under load.
- **Not built.** A separate gateway service, per-tenant routing and cost-based routing.

## P9-10: the Euron embeddings provider

- **What it does.** `rag/embeddings.py` gains `EuronEmbeddings`, which sends batches of up to 64 texts to Euron's OpenAI-compatible embeddings endpoint (model `euri-embedding`), reads the vector size from the first reply and refuses a size that differs from `EMBEDDING_DIMENSIONS` with a clear `EmbeddingError` that never echoes a provider message. The fake hashed embeddings stay the default and the only ones tests use.
- **Settings.** `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_BASE_URL` (empty falls back to the LLM base URL) and `EMBEDDING_DIMENSIONS` (1024 for `euri-embedding`). Changing the model needs `POST /api/v1/knowledge/reindex`, because the collection is recreated.
- **Verified.** `tests/rag/test_euron_embeddings.py` offline; on 2026-11-27 the real endpoint filled a local Qdrant collection with 75 chunks of 1,024 dimensions and search returned the right article first.

---

## QA remediation, 2026-11-27: duplicate steps and honest cost

- **Duplicate diagnosis steps.** The playbook merge in `agents/specialists/troubleshooting.py` compared steps by exact text, so a model step such as "Compare the billed seat count with the active workspace member count" and the playbook's "Compare billed seats with active workspace members" both appeared. `is_duplicate_step` and `merge_steps` now treat a step as a duplicate when nearly all of the shorter step's content words appear in the longer one; short steps must match exactly. Model steps stay first and distinct playbook steps are kept (`tests/agents/test_troubleshooting.py`).
- **Cost reporting.** No Euron price is verified, so real runs reported `$0.0000`. `TokenUsage` now carries `cost_basis` (`none`, `actual`, `estimated`, `unavailable`); a provider-reported cost is actual, a price from the owner's `LLM_PRICING` setting gives an estimate, and tokens with no price are unavailable. Nothing is invented, and unknown is never shown as zero (`tests/unit/test_cost_reporting.py`).
