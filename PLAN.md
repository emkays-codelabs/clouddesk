# PLAN.md — CloudDesk Project 1

Build plan for the autonomous support-resolution platform. `CLAUDE.md` is the spec. `TASKS.md` is the order of work, and the phase exit criteria are at the end of this file. This file is the requirement catalog and the exit bar for the whole project.

## Goal

Ship an agent console where a support agent opens a CloudDesk ticket, runs one workflow, inspects every step, and approves anything that spends money or changes an account. The same codebase runs offline with no API key.

## Users

| Actor | Outcome |
|---|---|
| Viewer | Can read tickets, customers, knowledge, and audit, and cannot run, reply, or approve |
| Agent | Can run the workflow, reply, request information, approve or reject, and escalate from one ticket screen |
| Admin | Can reindex knowledge and change settings |
| Platform | Records an audit row for every state-changing request and an event for every node, tool call, and model call |

## Non-goals for v1

- Real email delivery and real refunds.
- Languages other than English.
- A customer-facing chat widget.
- A separate worker process for workflows.
- Applying Terraform to a live cloud account.
- The Stage 17 deployment agent (`../deployment-agent/`).

## System requirements

### Functional

| ID | The system shall | Proven by | Phase |
|---|---|---|---|
| F1 | Create a ticket from email, chat, web, or API via `POST /api/v1/tickets` | API ticket-create test | 4 |
| F2 | Classify the ticket into one of the ten categories and write a one-line summary | Supervisor agent test; classification accuracy ≥ 0.80 | 9, 14 |
| F3 | Assign severity `low`/`medium`/`high`/`critical` with a reason; rules may only raise it | Rules test; `CD-1010` stays low | 7, 9 |
| F4 | Load customer, subscription, workspace, previous tickets, and up to 10 memory notes | Customer agent test | 4, 8, 9 |
| F5 | Attach cited evidence from hybrid retrieval, reranked, one hit per article | RAG tests; hit-rate@3 ≥ 0.75 | 5, 9, 14 |
| F6 | Attach similar previously resolved cases | `KnowledgeAgent.similar_cases` test | 5, 9 |
| F7 | Produce probable causes and numbered troubleshooting steps | Troubleshooting agent test | 9 |
| F8 | Produce a resolution plan: summary, customer reply, internal notes, and actions | Resolution agent test; grounding rate ≥ 0.90 | 9, 14 |
| F9 | Hold consequential actions for a recorded human approval | Policy unit test; `CD-1002` pause and resume | 6, 11 |
| F10 | Escalate policy cases to a named team; rules override the model | Escalation correctness ≥ 0.90; `CD-1005`, `CD-1006`, `CD-1009`, `CD-1011` | 7, 11, 14 |
| F11 | Write a ticket summary and update customer memory after every completed run | Workflow end-state test; memory scrub test | 8, 10 |
| F12 | Let an agent approve, reject, escalate, reply, and request information from one screen | Frontend tests plus a browser pass of `/tickets/[id]` | 12, 13 |
| F13 | Record every node, tool call, and model call with timing, tokens, and cost | `GET /tickets/{id}/events` test | 10 |
| F14 | Complete a run in `DEMO_MODE` with the fake provider and no API key | Offline pytest and `make demo` | 1, 14 |

### Non-functional

| ID | The system shall | Proven by | Phase |
|---|---|---|---|
| N1 | Authenticate with Supabase-compatible JWT (HS256) | Auth API tests | 3 |
| N2 | Rate-limit clients with a fixed window in Redis | Rate-limit test; demo ceiling 120/min | 3 |
| N3 | Send `X-Request-ID` on every response | Request-id test | 1 |
| N4 | Treat ticket text as data and contain prompt injection | `CD-1013` test | 7, 11 |
| N5 | Validate customer-facing output before a reply is shown | Guardrail unit test; failed validation raises risk to `high` | 7 |
| N6 | Audit every non-GET request | Audit middleware test | 3 |
| N7 | Keep secrets out of memory notes | Scrub test with card, key, and password fixtures | 7, 8 |
| N8 | Build as containers that can be deployed to AWS, Azure, and GCP | Dockerfile and compose tests; Terraform validate | 14 |

### Quality bar

| Metric | Threshold |
|---|---|
| Classification accuracy | ≥ 0.80 |
| Retrieval hit-rate@3 | ≥ 0.75 |
| Escalation correctness | ≥ 0.90 |
| Citation rate | ≥ 0.90 |
| Grounding rate (steps present in the reply) | ≥ 0.90 |

Pytest uses `asyncio_mode = "auto"` and `loop_scope = "session"`. Do not add `@pytest.mark.asyncio` with a different scope.

## Build phases

`TASKS.md` holds the sub-tasks, branches, dependencies, and merge order. Exit criteria for each phase are at the end of this file. Phases 4, 5, 6, and 7 can start together once Phase 2 (and Phase 3, for Phase 4) has merged.

| Phase | Name | Status |
|---|---|---|
| 1 | Runtime skeleton | not started |
| 2 | Persistence and demo data | not started |
| 3 | Identity and request guards | not started |
| 4 | Support API | not started |
| 5 | Knowledge pipeline | not started |
| 6 | Tools and mocks | not started |
| 7 | Rules and guardrails | not started |
| 8 | Memory | not started |
| 9 | Specialist agents | not started |
| 10 | Workflow graph and trace | not started |
| 11 | Approval and escalation | not started |
| 12 | Console shell | not started |
| 13 | Ticket workflow screen | not started |
| 14 | Evaluation and delivery | not started |

Stages 13–16 of the course (containers, observability, CI, multi-cloud) are represented inside Phase 14 as files and local validation. Stage 17 stays optional and unbuilt.

## Request path the plan must preserve

1. `POST /api/v1/tickets/{id}/run` returns **202** `{workflow_id}`.
2. A background task runs the graph. After every node, state is saved. The UI polls `/workflow` every 2 seconds.
3. `human_approval` interrupts. The service writes `approval_requests` and sets the ticket to `waiting_on_approval`.
4. `POST /approvals/{id}/approve` or reject resumes the graph.
5. The tail is `execute_resolution` → `ticket_summary` → `memory_update` → END.
6. “Send reply” is a separate `POST /tickets/{id}/reply`.

## Acceptance for the whole project

- Every `F` and `N` row above has at least one test.
- `make test` passes with no network and no API key.
- `make demo` pauses on `CD-1002` and escalates `CD-1005` by rule.
- `CD-1013` does not export records and does not change the route the graph takes.
- Viewer tokens receive 403 on run, reply, and approve.
- `docker compose config -q` succeeds.
- The honest status in `MEMORY.md` still says cloud apply and GitHub execution have not happened, until they have.
- `README.md` matches §14 commands once that file exists.

## Risks to watch while building

- Two sources of ticket categories. The schema module is the only place a category is introduced.
- Model-written tool calls. Actions stay on the deterministic plan.
- Side effects before `interrupt()`, which re-run on resume.
- Reducer fields overwritten instead of appended, which drops `completed_nodes` and breaks the UI.
- Embedding changes without a reindex, which silently empties retrieval.
- Service-role key imported into the frontend.
- Calling a phase “deployed” because the Terraform files exist.

## Definition of done for any single change

- The requirement id is named in the test.
- The layer rules in `CLAUDE.md` §4.2 hold.
- Contract, backend schema, and `frontend/lib/types.ts` match if the HTTP shape changed.
- Offline tests for that area pass.
- The honest-status table is still true.

---

## Phase exit criteria

Each phase states its goal, requirements, files, tests, demo checkpoint, and exit criteria. Do not start a phase until the phases it depends on (see `TASKS.md`) have passed their exit criteria. After `make demo` exists, every later phase keeps that checkpoint working. Status values: `not started`, `in progress`, `implemented`, `validated locally`. “Validated locally” means the phase’s tests passed on this machine; it does not mean deployed.

### Phase 1 — Runtime skeleton

Tasks: `TASKS.md`, Phase 1.

**Goal.** A process that boots offline, logs JSON with `request_id`, and answers health probes.

**Requirements.** F14 (settings hook), N3.

**Files.** `backend/app/main.py`, `backend/app/core/` (`config`, `logging`, `database` stubs), `backend/app/middleware/`, `.env.example`, `pyproject.toml`, `Makefile`, `tests/conftest.py`, `tests/api/test_health.py`.

**Tests.** `/health` and `/health/live` respond without I/O. Every response carries `X-Request-ID`. Settings read `DEMO_MODE` and `LLM_PROVIDER` from the environment. The test harness sets the offline env vars before importing the app.

**Demo checkpoint.** `make backend` serves `/health/live`. `make demo` is not available yet.

**Exit.** Health tests pass offline. `.env.example` lists every variable in `CLAUDE.md` §10.1 with placeholders only.

### Phase 2 — Persistence and demo data

Tasks: `TASKS.md`, Phase 2.

**Goal.** One portable data model and a demo database that loads when empty.

**Requirements.** Data model in `CLAUDE.md` §6. Supports F1 and F4.

**Files.** `backend/app/models/entities.py`, `backend/app/repositories/`, `database/schema.sql`, `database/rls_policies.sql`, `database/seed.sql`, `database/migrations/`, `sample_data/*.json`, `sample_data/knowledge_base/*.md`, seed bootstrap in the lifespan.

**Tests.** Startup on an empty SQLite file with `DEMO_MODE=true` loads 13 tickets and 8 customers. Models and `schema.sql` agree on tables and column types. A second startup does not duplicate rows.

**Demo checkpoint.** `make seed` loads sample data. Ticket `CD-1002` and customer records are readable from the database.

**Exit.** `database/schema.sql` is the authority for table count. The table-count question under Open questions is closed there.

### Phase 3 — Identity and request guards

Tasks: `TASKS.md`, Phase 3.

**Goal.** JWT auth, role checks, rate limiting, and audit, in the documented middleware order.

**Requirements.** N1, N2, N6. Viewer prohibition in §18.1.

**Files.** `backend/app/core/security.py`, auth router, rate-limit and audit middleware, demo token issuer.

**Tests.** Missing and bad tokens are rejected. `vic.viewer` receives 403 on a mutating route. An agent token is accepted. A non-GET request writes `audit_logs`. The limiter uses fakeredis.

**Demo checkpoint.** Demo login issues an 8-hour token for the three demo users.

**Exit.** Middleware order is CORS → RequestId → RateLimit → Audit. No service-role secret is returned to the client.

### Phase 4 — Support API

Tasks: `TASKS.md`, Phase 4.

**Goal.** Agents can create and read the records the workflow will consume.

**Requirements.** F1, F4 (read side), contract rule in §12.

**Files.** `backend/app/api/` ticket and customer routers, `backend/app/schemas/`, `backend/app/services/`, `docs/API_CONTRACT.md`, `tests/api/` ticket tests.

**Tests.** `POST /api/v1/tickets` accepts email, chat, web, and API channels. List, get, and 404 behave as the contract says. Customer, subscription, workspace, and previous tickets load for a known demo customer. Duplicate run-while-waiting is specified now and enforced in Phase 11.

**Demo checkpoint.** `make seed` then an API call creates a ticket and fetches `CD-1001` through `CD-1013`.

**Exit.** Contract, schemas, and the future `frontend/lib/types.ts` shapes are written together for every route added here.

### Phase 5 — Knowledge pipeline

Tasks: `TASKS.md`, Phase 5.

**Goal.** Fifteen articles are chunked, indexed, and retrievable offline.

**Requirements.** F5, F6 (retrieval half).

**Files.** `rag/chunking.py`, `rag/vector_store.py`, `rag/retriever.py`, `rag/ingest.py`, `make ingest`, knowledge search and admin reindex routes.

**Tests.** `tests/rag/` covers ingest count, the expected article for the key queries, `hybrid` / `semantic` / `keyword`, cache, RRF, rerank, and filters. Chunks are heading-split, then 900/150, and prefixed with `"{title} - {heading}"`. Reindex is admin-only and recreates the collection.

**Demo checkpoint.** `make ingest` reports the article and chunk counts. A query for the MFA recovery article returns `CD-1012`’s expected article in the top 3.

**Exit.** Retrieval hit-rate@3 is measured, even if the full eval suite waits for Phase 14. Customer-facing policy claims have an article to cite.

### Phase 6 — Tools and mocks

Tasks: `TASKS.md`, Phase 6.

**Goal.** Every side effect the agents can take is a registered tool with an explicit approval bit.

**Requirements.** F9 (policy half).

**Files.** `backend/app/tools/` (`policy.py`, registry, tool functions), `integrations/protocols.py`, `integrations/mock/services.py`, `integrations/factory.py`.

**Tests.** `tests/unit/` tool policy: reads need no approval; `update_ticket` needs none; `reset_demo_setting` and `create_refund_request` need approval; unknown tools need approval; a tool exception returns `ToolResult(ok=False)`; timeout uses `TOOL_TIMEOUT_SECONDS`.

**Demo checkpoint.** A direct registry call to `create_refund_request` without `approved=True` does not write a refund.

**Exit.** The same execute path is the one Phase 11 will call after a human approval. No tool bypasses the registry.

### Phase 7 — Rules and guardrails

Tasks: `TASKS.md`, Phase 7.

**Goal.** Policy and safety are deterministic before any specialist calls a model.

**Requirements.** F3 (rules), F10 (rule table), N4, N5, N7 (scrub function).

**Files.** `agents/rules.py`, `agents/prompts.py` (`SECURITY_PREAMBLE`, `wrap_untrusted`), `backend/app/core/` guardrails (`scan_for_injection`, `validate_customer_output`, `scrub`).

**Tests.** Category and severity rules. Severity never lowers a model score. Escalation rules match dispute, deletion, security, data loss, legal, and enterprise outage, each with a named team. `CD-1013` is flagged and wrapped as data. Output validation rejects internal URLs, secrets, and another customer’s data, and that failure is defined as risk `high`. `scrub` removes card numbers, API keys, and passwords.

**Demo checkpoint.** A unit run of the escalation rules on `CD-1005`, `CD-1006`, `CD-1009`, and `CD-1011` returns escalation required without a model call.

**Exit.** Grey-area model judgement is the only path left for Phase 9. Policy cases already have a decision.

### Phase 8 — Memory

Tasks: `TASKS.md`, Phase 8.

**Goal.** Every completed run recalls prior notes and writes scrubbed, de-duplicated memory.

**Requirements.** F4 (notes), F11 (write), N7.

**Files.** `memory/short_term.py`, `memory/long_term.py`, `memory/memory_service.py`, `customer_context` recall, `memory_update` node.

**Tests.** Recall returns at most 10 notes. A completed run writes a past issue, the first three troubleshooting steps, and a resolution note. Exact duplicates are skipped. Card numbers, API keys, passwords, and raw ticket bodies are absent from `customer_memory`. Retrieval cache keys match `rag:{mode}:{category}:{top_k}:{query}` and expire in 300 seconds. Short-term TTL is 24 hours. Tests use fakeredis.

**Demo checkpoint.** Running `CD-1002` through approval twice does not duplicate the resolution note.

**Exit.** Memory facades are the only writers of `customer_memory`. Notes never include another customer’s data.

### Phase 9 — Specialist agents

Tasks: `TASKS.md`, Phase 9.

**Goal.** Six specialists each return their Pydantic model through `call_structured`, using the fake provider.

**Requirements.** F2, F3, F4, F5, F6, F7, F8, F14.

**Files.** `agents/specialists/`, `agents/prompts.py`, `backend/app/schemas/workflow.py`, `backend/app/core/llm.py` fake provider, `tests/agents/`, `datasets/eval_cases.json` (initial cases).

**Tests.** One test per specialist: classification plus one-line summary, severity with reason, customer context with no model call, evidence plus similar cases, diagnosis with numbered steps, resolution plan whose actions come from `plan_actions` and whose reply is grounded and validated. Fake provider cost is `0.0`.

**Demo checkpoint.** Each specialist can be invoked on `CD-1002` and `CD-1010` offline. `CD-1010` remains low severity.

**Exit.** No specialist writes SQL. No specialist calls a tool except through `ToolRegistry`. Eval cases use a valid `expected_category`.

### Phase 10 — Workflow graph and trace

Tasks: `TASKS.md`, Phase 10.

**Goal.** One graph runs a low-risk ticket to the end, persists state after every node, and records inspectable events.

**Requirements.** F11 (summary node), F13, graph shape in §7.3.

**Files.** `agents/state.py`, `agents/graph.py`, `agents/checkpointer.py`, `agents/nodes/`, workflow service (`create_run`, `start_workflow`), `GET /tickets/{id}/workflow`, `GET /tickets/{id}/events`.

**Tests.** `tests/workflow/` graph shape, routing, and risk levels. A low-risk ticket completes `execute_resolution` → `ticket_summary` → `memory_update` → END. Events include node start/complete, tool, and llm records with duration. Reducers append `errors` and `completed_nodes`. Checkpointer uses `:memory:` under pytest.

**Demo checkpoint.** `POST /tickets/{id}/run` on a low-risk ticket returns 202, and polling `/workflow` reaches the end.

**Exit.** Telemetry failures do not fail the run. Raw prompts are not present in `workflow_events`.

### Phase 11 — Approval and escalation

Tasks: `TASKS.md`, Phase 11.

**Goal.** Money and account changes pause for a human. Policy cases escalate by rule.

**Requirements.** F9, F10, N4 on the live path. 409 behaviour in §10.

**Files.** `human_approval` node, `approval_service.decide`, approval routes, `EscalationAgent`, `execute_resolution`, ticket status transitions.

**Tests.** `CD-1002` pauses with `waiting_on_approval` and an `approval_requests` row; approve resumes and runs the refund tool once; reject routes to escalation. A second run during the pause returns 409. Resume of a run that is not paused returns 409. `CD-1005`, `CD-1006`, `CD-1009`, and `CD-1011` escalate without an approval wait. `CD-1013` does not take an export action. Risk is `high` for approval-required plans, policy escalation, critical severity, injection, and failed output validation.

**Demo checkpoint.** `make demo` pauses on `CD-1002`. `make demo TICKET=CD-1005` escalates.

**Exit.** Code before `interrupt()` is idempotent. The approved path and the automatic path share `ToolRegistry.execute`. A viewer token receives 403 on run, approve, and reject.

### Phase 12 — Console shell

Tasks: `TASKS.md`, Phase 12.

**Goal.** A logged-in, role-aware console shell with read-only list pages, built against the written API contract. It does not wait for the agents.

**Requirements.** UI rules in §11. Prepares F12.

**Files.** `frontend/app/` (layout and the pages `/login`, `/dashboard`, `/tickets`, `/customers`, `/customers/[id]`, `/knowledge`, `/escalations`, `/agents`, `/audit`, `/settings`, `/api/health`), `frontend/components/` (including `layout/nav.ts` and the hand-written `ui/` kit), `frontend/lib/` (`api.ts`, `types.ts`, `hooks.ts`, `format.ts`, `cn.ts`).

**Tests.** The API helper redirects a 401 to `/login?reason=expired`; the network-error banner retries; StatusPill and EmptyState render. Viewer action controls render disabled.

**Demo checkpoint.** With the backend running, log in as each of the three demo users and open every list page.

**Exit.** `NEXT_PUBLIC_*` values are treated as build-time. The service-role key is absent from the frontend. No UI-library dependency and no gradients; the hand-written kit is the only chrome. Navigation is declared once.

### Phase 13 — Ticket workflow screen

Tasks: `TASKS.md`, Phase 13.

**Goal.** One ticket screen covers F12: the agent runs the workflow, watches every step, and approves, rejects, replies, or escalates.

**Requirements.** F12. UI rules in §11.

**Files.** `frontend/app/(dashboard)/tickets/[id]/page.tsx`, the ticket components (messages and composer, customer panel, workflow panel), `usePolling` in `frontend/lib/hooks.ts`, `frontend/__tests__/`.

**Tests.** WorkflowSteps step derivation. Approve and Reject render only when `approval_status` is `pending`. Viewer action controls stay disabled.

**Demo checkpoint.** Browser pass, with the backend running: log in as the agent, open `CD-1002`, run the workflow, watch the twelve steps poll, approve, and send the reply. Repeat as the viewer and confirm the actions stay disabled. Check the ticket list and the customer page still show the same ticket state.

**Exit.** The three-column layout holds: messages and composer, customer context, and the workflow panel with evidence, diagnosis, planned actions, and an editable reply.

### Phase 14 — Evaluation and delivery

Tasks: `TASKS.md`, Phase 14.

**Goal.** The offline quality bar fails the build when missed, and the delivery files exist without claiming a real deployment.

**Requirements.** F2, F5, F8, F10 thresholds; F14; N8. Honest status in §15.1.

**Files.** `tests/evaluation/`, `datasets/eval_cases.json`, `tests/deployment/`, `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `deployment/{aws,azure,gcp}`, `deployment/kubernetes`, `deployment/scripts/`, `.github/workflows/` (`test.yml`, `security.yml`, `docker-build.yml`, `terraform-validate.yml`, `_deploy.yml`).

**Tests.** Eval metrics meet the thresholds in `PLAN.md`. Deployment tests check compose services, non-root Dockerfiles, `HEALTHCHECK`, `.env.example` coverage, and that no `.env` is committed. `docker compose config -q` passes. `make terraform-validate` passes locally. `BASE_URL=http://localhost:8000 make smoke` passes against the local stack.

**Demo checkpoint.** `make test`, then `make demo` for `CD-1002` and `make demo TICKET=CD-1005`.

**Exit.** Core Project 1 is complete only when phases 1–14 are validated locally. The honest status in `MEMORY.md` may say implemented and validated locally. It still says no cloud credentials, nothing applied, and workflows not executed on GitHub, until those things are true. Stage 17 is not required and is not started by this phase.

---

## Status and decisions

The honest status, locked decisions, open questions, and the update protocol live in [`MEMORY.md`](MEMORY.md), so the facts that change are kept apart from the plan that does not.
