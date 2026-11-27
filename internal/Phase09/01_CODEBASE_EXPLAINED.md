# Phase 9 explained: the specialist agents

> **Status:** implemented and checked locally with the offline fake model. The Euron router and embeddings were also exercised against the real Euron API during the Docker bring-up (see `MEMORY.md`). Nothing is deployed.

## A. Executive summary

Phase 9 builds the six specialist agents and the single door through which any of them reaches a language model. Each agent is an ordinary class with one job, returns a Pydantic model, and can be called directly in a test. Phase 10 later joins them into a graph.

## B. Business problem and solution

A support ticket needs several different kinds of thinking: what is this, who is the customer, what do our documents say, what is probably wrong, what should we do, and must a human take over. One large prompt does all of that badly and cannot be audited. Six narrow agents, each with a structured output and a rules layer for policy, can be tested, replaced and explained one at a time.

## C. Architecture in simple language

- `backend/app/core/llm.py` is the only code that talks to a model. `call_structured` asks for a Pydantic model, repairs an invalid reply at most twice, caps temperature at 0.2 and measures usage.
- `backend/app/core/llm_router.py` chooses a tier (fast, smart, reasoning), falls back down a chain and opens a circuit breaker after repeated failures. It runs inside the backend; there is no gateway service.
- `agents/specialists/` holds the six agents. `agents/rules.py` holds the deterministic policy they must obey. `agents/prompts.py` holds every prompt and the shared security preamble.
- `rag/` supplies retrieval; `backend/app/tools/` supplies the permissioned tools.

## D. File-by-file

| File | What it does |
|---|---|
| `backend/app/schemas/workflow.py` | Agent output models, `TokenUsage` and `WorkflowState`. |
| `backend/app/core/llm.py` | `get_llm()`, `call_structured()`, the fake provider and the OpenAI-compatible provider used for `openai` and `euron`. |
| `backend/app/core/llm_router.py` | Tier routing, fallback chain, circuit breaker. |
| `rag/embeddings.py` | `FakeEmbeddings` (offline) and `EuronEmbeddings`. |
| `agents/rules.py` | Category, severity and escalation rules that always win over the model. |
| `agents/specialists/supervisor.py` | Classifies, scores severity, writes the ticket summary. |
| `agents/specialists/customer.py` | Loads customer, subscription, workspace, history and memory notes. No model call. |
| `agents/specialists/knowledge.py` | Cited evidence and similar resolved cases. |
| `agents/specialists/troubleshooting.py` | Probable causes and numbered steps, with playbook enrichment. |
| `agents/specialists/resolution.py` | Deterministic action plan, grounded customer reply, output validation. |
| `agents/specialists/escalation.py` | Policy escalation with the model used only for grey areas. |
| `datasets/eval_cases.json` | The 16 cases the evaluation uses. |

## E. Execution flow

A ticket's text is wrapped as untrusted. The supervisor combines `rule_category` with the model's answer; rules may raise severity but never lower it. The customer agent reads data. The knowledge agent retrieves, drops any chunk that looks like an instruction, and cites titles. The troubleshooting agent proposes steps. The resolution agent plans actions in code (never from ticket text), asks the model only for wording, keeps the sentences the evidence supports and validates the reply. The escalation agent applies policy rules first.

## F. Concepts

- **Rules first, model second.** Policy is code with tests; the model supplies judgement in grey areas.
- **Structured output.** Every agent returns a schema, so there is no free-text parsing.
- **Provenance.** Ids and amounts in tool arguments come from customer context, not ticket text.

## G. Decisions and trade-offs

The router is in process rather than a gateway (ADR 0010, accepted in limited form): less to run, no shared failover state. Actions are deterministic, which limits creativity but makes refunds auditable. The fake provider accepts rule results as hints so offline behaviour is realistic.

## H. Failure handling

An invalid model reply is repaired twice and then raises `LLMError` carrying the usage spent. A failing tier falls back; repeated failures open the breaker. A failing agent returns a status the node layer later turns into an escalation.

## I. Testing

`tests/agents/` has one test per specialist behaviour, `tests/unit/` covers the LLM layer and rules, `tests/rag/` covers embeddings, and `tests/evaluation/test_eval_cases.py` checks the dataset agrees with the rules. All run offline. Real-model behaviour was checked by hand only.

## J. Interview-ready explanation

"We split support into six agents with structured outputs. Policy lives in rules the model cannot override, and every model call goes through one function that validates, repairs, caps temperature and records usage."

## K. Next phase

Phase 10 joins these agents into a LangGraph workflow, adds routing, budgets and the trace.
