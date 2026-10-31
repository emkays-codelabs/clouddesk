# CloudDesk Support — Task tracker

> Concise checklist for GitHub-visible progress.
> Full plan and phase exit criteria: `PLAN.md` · Status and decisions: `MEMORY.md` · Spec: `CLAUDE.md`

**Branch convention:** `feature/<name>` (one feature branch per sub-task; open the PR against `development`)
**Status:** `Pending ❌` · `Completed ✅`

Sub-tasks in the same phase that do not share files can be open at the same time. Do not stack a branch on another feature branch. Merge the listed predecessor first when a row names one.

`PLAN.md` holds each phase's exit criteria. This file is the execution order, arranged so a phase waits only on the contract it uses.

---

## Beginning to end

**Start at `P1-1`. The project is finished when every task below is Completed ✅ and the “Finished when” list near the end of this file is true.**

Work every task the same way:

1. Create `feature/<name>` (the branch in the task's row) from an up-to-date `development`.
2. Read the task's definition below, the phase in `PLAN.md`, and the matching section of `CLAUDE.md`.
3. Write the test first and name the requirement (F1–F14, N1–N8) it proves. Watch it fail.
4. Implement until the test passes. Keep the layers in `CLAUDE.md` §4.2.
5. Run the checks for the area (`make test`, `make lint`, and the frontend commands for UI work).
6. Open a pull request into `development`. **The same pull request must update this file:** set the task's row to Completed ✅ and update the Progress summary (its phase count and the total). Add a line to the Honest status in `MEMORY.md`, saying only what was run. When a whole phase is done, also update the Build phases table in `PLAN.md`. A task is not done until its pull request includes this; it counts as complete when the pull request merges.

**Order.** A task can start once everything it **Needs** has merged. Tasks in the same wave have no dependency on each other and can run in parallel; each task's **Needs** line is authoritative.

**Expected small conflicts.** Most tasks add packages, so `pyproject.toml` and `uv.lock` will conflict when branches overlap: rebase, then run `uv lock`. Every API task registers a router in `main.py`, and several tasks add a `Makefile` target. Resolve these by keeping both sides.

| Wave | Tasks that can start |
|---|---|
| 1 | `P1-1` |
| 2 | `P1-3`, `P1-4`, `P2-1` |
| 3 | `P1-2`, `P2-2`, `P2-3`, `P4-1`, `P7-1`, `P7-2`, `P7-3`, `P7-4` |
| 4 | `P2-4`, `P3-1`, `P3-3`, `P6-1`, `P6-4`, `P8-2`, `P12-1`, `P12-2` |
| 5 | `P3-2`, `P3-4`, `P4-2`, `P4-3`, `P5-1`, `P6-3`, `P8-1` |
| 6 | `P4-4`, `P4-5`, `P5-2`, `P8-3`, `P12-3` |
| 7 | `P5-3`, `P12-4` |
| 8 | `P5-4`, `P6-2` |
| 9 | `P6-5`, `P9-1` |
| 10 | `P9-2`, `P9-3`, `P9-4`, `P9-5`, `P9-6`, `P9-7`, `P9-8`, `P10-1` |
| 11 | `P10-2`, `P10-3`, `P10-4`, `P10-6` |
| 12 | `P10-5` |
| 13 | `P10-7`, `P11-1`, `P11-3`, `P13-1`, `P14-2` |
| 14 | `P11-2`, `P11-4`, `P11-6`, `P13-2`, `P14-3`, `P14-4` |
| 15 | `P11-5`, `P13-3`, `P14-5` |
| 16 | `P13-4`, `P14-1` |

The longest dependency chain is 16 tasks long.

---

## Phase 1 — Runtime skeleton

> Depends on: nothing. Unblocks: every later phase.
> Merge order: P1-1 first. P1-3 and P1-4 in parallel after it. P1-2 after P1-3, because its tests use the harness's `client` fixture.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P1-1 · Settings and JSON logging | F14 | `feature/backend-config-logging` | Completed ✅ |
| P1-2 · Health routes and request-id middleware | N3 | `feature/backend-health-request-id` | Completed ✅ |
| P1-3 · Offline pytest harness | F14 | `feature/test-harness-offline` | Completed ✅ |
| P1-4 · Makefile and `.env.example` | F14 | `feature/makefile-env-example` | Pending ❌ |

#### Task definitions

**P1-1 · Settings and JSON logging**
- **Needs:** nothing
- **Build:** Cached `get_settings()` with every variable in `CLAUDE.md` §10.1 (secrets and URL passwords redacted in `model_dump()`), and JSON logging with `request_id` and `workflow_id` bound through `log_context()`.
- **Files:** `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/core/logging.py`, `tests/unit/test_config_logging.py`, `pyproject.toml` (the `pydantic-settings` dependency, pytest `pythonpath`, and Ruff `src` so `app` imports resolve)
- **Done when:** Settings read `DEMO_MODE` and `LLM_PROVIDER` from the environment; `model_dump()` hides secrets and URL passwords; every log line carries `request_id` and `workflow_id` (`null` when unset).

**P1-2 · Health routes and request-id middleware**
- **Needs:** `P1-1`, `P1-3`
- **Build:** `GET /health`, `GET /health/live` (no I/O), `GET /health/ready` (configuration probes, 503 when degraded), and `RequestIdMiddleware` that echoes a safe `X-Request-ID` (1–128 chars of `A-Za-z0-9._:-`) or issues a UUID. CORS is outermost and exposes the header.
- **Files:** `backend/app/main.py`, `backend/app/api/health.py`, `backend/app/schemas/health.py`, `backend/app/core/readiness.py`, `backend/app/middleware/request_id.py` (plus the `__init__.py` files), `tests/api/test_health.py`
- **Done when:** Every response, including 404 and 500, carries `X-Request-ID`; `/health` and `/health/live` call no dependency; `/health/ready` returns 503 when a check fails and never shows a URL, password, or key.

**P1-3 · Offline pytest harness**
- **Needs:** `P1-1`
- **Build:** The offline test harness: environment fixed before `app` is imported (`DEMO_MODE=true`, `LLM_PROVIDER=fake`, `VECTOR_STORE=memory`, `USE_FAKE_REDIS=true`, temp SQLite, `CHECKPOINT_DB_PATH=:memory:`), every credential blanked so a key exported in the shell cannot reach a test, a guard that fails any attempt to reach a non-local host (loopback still works), a `client` fixture that imports `create_app` lazily and skips with a clear reason until the app exists (so the harness can land first), and pytest `asyncio_mode = "auto"` with session loop scope.
- **Files:** `tests/conftest.py`, `tests/unit/test_harness.py`, `pyproject.toml` (pytest `asyncio_mode` and session loop scope, and the `pytest-asyncio` and `httpx` dev dependencies; `pythonpath` already set by P1-1)
- **Done when:** `pytest` passes with no network and no API key; a test that changes env vars sees the change after `get_settings.cache_clear()`.

**P1-4 · Makefile and `.env.example`**
- **Needs:** `P1-1`
- **Build:** `.env.example` listing every §10.1 variable with placeholders only, and a `Makefile` with `setup`, `backend`, `test`, and `lint` (later phases add `seed`, `ingest`, `demo`, `mcp`, `smoke`, `terraform-validate`).
- **Files:** `.env.example`, `Makefile`, `.gitattributes` (keeps the Makefile on LF), `tests/unit/test_env_example.py`
- **Done when:** A test proves `.env.example` covers every variable in the spec and every `Settings` field, and holds no real key; `make test` and `make lint` run.

---

## Phase 2 — Persistence and demo data

> Depends on: P1-1. Unblocks: Phases 3, 4, 5, 6, and 8.
> Merge order: P2-1 first. P2-2 and P2-3 in parallel after it. P2-4 after P2-3.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P2-1 · SQLAlchemy entities and category enum | F1 | `feature/sqlalchemy-entities` | Pending ❌ |
| P2-2 · Postgres schema, RLS, and migrations | — | `feature/postgres-schema-rls` | Pending ❌ |
| P2-3 · Repository layer | F4 | `feature/repository-layer` | Pending ❌ |
| P2-4 · Sample data and demo bootstrap | F4 | `feature/sample-data-bootstrap` | Pending ❌ |

#### Task definitions

**P2-1 · SQLAlchemy entities and category enum**
- **Needs:** `P1-1`
- **Build:** Async SQLAlchemy 2 models for the 16 tables, portable across SQLite and Postgres (JSON not JSONB, `String(36)` UUIDs). Categories, statuses, severities, and channels are defined first in `schemas/common.py`.
- **Files:** `backend/app/models/entities.py`, `backend/app/schemas/common.py`, `backend/app/core/database.py`
- **Done when:** Tables create on an empty SQLite file; a test asserts exactly the 10 categories, 7 statuses, 4 severities, and 4 channels.

**P2-2 · Postgres schema, RLS, and migrations**
- **Needs:** `P2-1`
- **Build:** The Postgres side: `schema.sql` (with the `set_updated_at()` trigger), `rls_policies.sql` (RLS on every data table), and an additive migration folder.
- **Files:** `database/schema.sql`, `database/rls_policies.sql`, `database/seed.sql`, `database/migrations/0001_*.sql`
- **Done when:** A test shows `schema.sql` and the models agree on tables and column types; `schema.sql` becomes the authority for the table count.

**P2-3 · Repository layer**
- **Needs:** `P2-1`
- **Build:** The repository layer: all SQL goes through repositories for tickets, messages, customers, subscriptions, workspaces, memory, workflow runs and events, approvals, escalations, and audit logs.
- **Files:** `backend/app/repositories/`, `tests/unit/` repository tests
- **Done when:** Repository tests pass on SQLite; nothing under `repositories/` imports a model client or `agents/`.

**P2-4 · Sample data and demo bootstrap**
- **Needs:** `P2-3`
- **Build:** Demo data and bootstrap: 13 tickets (`CD-1001`–`CD-1013`), 8 customers, subscriptions, workspaces, incidents, previous resolutions, and products; `bootstrap_demo_data()` loads them when the database is empty and `DEMO_MODE=true`; `make seed`.
- **Files:** `sample_data/*.json`, `backend/app/services/seed_service.py`, lifespan hook in `main.py`, `Makefile`
- **Done when:** Startup on an empty SQLite file loads 13 tickets and 8 customers; a second startup adds no rows; `CD-1002` and its customer are readable.

---

## Phase 3 — Identity and request guards

> Depends on: P1-2 and P2-1. P3-4 also needs P2-3 (it writes `audit_logs` through the repositories). Unblocks: protected routes in Phase 4 and Phase 12.
> Merge order: P3-1 and P3-3 in parallel. P3-2 after P3-1. P3-4 last (it owns middleware order).

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P3-1 · JWT and `require_role` | N1 | `feature/jwt-rbac` | Pending ❌ |
| P3-2 · Demo auth routes and tokens | N1 | `feature/auth-demo-tokens` | Pending ❌ |
| P3-3 · Redis rate limit | N2 | `feature/rate-limit-redis` | Pending ❌ |
| P3-4 · Audit middleware and middleware order | N6 | `feature/audit-middleware` | Pending ❌ |

#### Task definitions

**P3-1 · JWT and `require_role`**
- **Needs:** `P1-2`, `P2-1`
- **Build:** JWT handling (HS256 via PyJWT, Supabase secret preferred when set) and `require_role` with the ranking `viewer 1 < agent 2 < admin 3`.
- **Files:** `backend/app/core/security.py`, `tests/api/test_auth.py`
- **Done when:** Missing and bad tokens are rejected; an agent token is accepted; `vic.viewer` receives 403 on a mutating route (N1).

**P3-2 · Demo auth routes and tokens**
- **Needs:** `P3-1`
- **Build:** Demo authentication: `POST /auth/demo-login` (only when `DEMO_MODE=true`) and `GET /auth/me`; 8-hour tokens for `admin@`, `sam.agent@`, and `vic.viewer@clouddesk.demo`.
- **Files:** `backend/app/api/auth.py`, `backend/app/schemas/auth.py`
- **Done when:** Demo login issues a token for each of the three users; no service-role secret is ever returned to the client.

**P3-3 · Redis rate limit**
- **Needs:** `P1-2`
- **Build:** The Redis client (real Redis, or fakeredis when `REDIS_URL` is empty or `USE_FAKE_REDIS`) and a fixed-window rate limiter per client at `RATE_LIMIT_PER_MINUTE` (demo 120).
- **Files:** `backend/app/core/redis.py`, `backend/app/middleware/rate_limit.py`, `tests/api/test_rate_limit.py`
- **Done when:** With fakeredis the request after the limit returns 429; the limit resets on the next window (N2).

**P3-4 · Audit middleware and middleware order**
- **Needs:** `P3-1`, `P3-3`, `P2-3`
- **Build:** `AuditMiddleware` writing one `audit_logs` row for every non-GET request, and the final middleware order, outermost first: CORS → RequestId → RateLimit → Audit.
- **Files:** `backend/app/middleware/audit.py`, `backend/app/main.py`, `tests/api/test_audit.py`
- **Done when:** A non-GET request writes an audit row with actor and request id; a test asserts the middleware order (N6).

---

## Phase 4 — Support API

> Depends on: P2-3 and P3-1. Unblocks: Phase 12. Does not block Phases 5, 6, or 7.
> `docs/API_CONTRACT.md` already describes every route, so P4-1 reviews it against the schemas.
> Merge order: P4-1 first, so ticket and customer work share a written contract. P4-2 and P4-3 in parallel after it. P4-4 after P4-2. P4-5 after P2-3 and P3-1.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P4-1 · Ticket and customer API contract | F1 | `feature/api-contract-docs` | Pending ❌ |
| P4-2 · Ticket API | F1 | `feature/api-tickets` | Pending ❌ |
| P4-3 · Customer API | F4 | `feature/api-customers` | Pending ❌ |
| P4-4 · Ticket actions API (reply, request-info, escalate, update) | F12 | `feature/api-ticket-actions` | Pending ❌ |
| P4-5 · Dashboard, audit, and settings read APIs | F12, N6 | `feature/api-dashboard-audit-settings` | Pending ❌ |

#### Task definitions

**P4-1 · Ticket and customer API contract**
- **Needs:** `P2-1`
- **Build:** Review `docs/API_CONTRACT.md` against the Pydantic schemas and write the request and response models for tickets and customers. Contract, schemas, and `frontend/lib/types.ts` change together from here on.
- **Files:** `backend/app/schemas/` (ticket, customer), `docs/API_CONTRACT.md`
- **Done when:** Schemas serialize to the shapes in the contract (`TicketSummary`, `Ticket`, `TicketDetail`, `Customer`, `CustomerDetail`) with tests.

**P4-2 · Ticket API**
- **Needs:** `P4-1`, `P2-3`, `P3-1`
- **Build:** Ticket API: `POST /tickets` (email, chat, web, api), `GET /tickets` (status, severity, search, paging), `GET /tickets/{id}` as `TicketDetail`. It does not start the workflow.
- **Files:** `backend/app/api/tickets.py`, `backend/app/services/ticket_service.py`, `tests/api/test_tickets.py`
- **Done when:** F1 test: all four channels create a ticket and a first message; list, get, and 404 follow the contract; a viewer gets 403 on create; `CD-1001`–`CD-1013` are fetchable after `make seed`.

**P4-3 · Customer API**
- **Needs:** `P4-1`, `P2-3`, `P3-1`
- **Build:** Customer API: `GET /customers` (search, paging) and `GET /customers/{id}` with subscription, workspace, tickets, and memory.
- **Files:** `backend/app/api/customers.py`, `backend/app/services/customer_service.py`, `tests/api/test_customers.py`
- **Done when:** A known demo customer loads with subscription, workspace, previous tickets, and memory notes; unknown id returns 404.

**P4-4 · Ticket actions API (reply, request-info, escalate, update)**
- **Needs:** `P4-2`
- **Build:** Ticket actions: `POST /tickets/{id}/reply`, `/request-info` (sets `waiting_on_customer`), `/escalate`, and `PATCH /tickets/{id}`.
- **Files:** `backend/app/api/tickets.py` (action routes), `backend/app/services/ticket_service.py`, `tests/api/test_ticket_actions.py`
- **Done when:** Each route behaves as in the contract; a viewer gets 403 on all four; status transitions are recorded.

**P4-5 · Dashboard, audit, and settings read APIs**
- **Needs:** `P2-3`, `P3-1`, `P3-4`
- **Build:** Read APIs for the console: `GET /dashboard/summary`, `GET /audit` (paging, actor, action filters), and `GET /settings` (redacted).
- **Files:** `backend/app/api/dashboard.py`, `audit.py`, `settings.py`, matching schemas and tests
- **Done when:** Responses match the contract; `/settings` reports `api_key_configured` as a boolean and never a key.

---

## Phase 5 — Knowledge pipeline

> Depends on: P2-4 and P3-3 (the retrieval cache uses the Redis client). P5-4 also needs P3-1 (admin-only reindex). Parallel with: Phases 4, 6, 7, and 12.
> Merge order: P5-1, then P5-2, then P5-3, then P5-4. This phase is a pipeline; the surrounding phases are not.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P5-1 · Knowledge articles and chunking | F5 | `feature/rag-chunking` | Pending ❌ |
| P5-2 · Vector store and fake embeddings | F5 | `feature/rag-vector-store` | Pending ❌ |
| P5-3 · Hybrid retriever | F5, F6 | `feature/rag-hybrid-retriever` | Pending ❌ |
| P5-4 · Ingest command and knowledge API | F5 | `feature/rag-ingest-api` | Pending ❌ |

#### Task definitions

**P5-1 · Knowledge articles and chunking**
- **Needs:** `P2-4`
- **Build:** Fifteen knowledge articles with YAML front-matter (`title`, `category`, `tags`, `summary`) and the chunker: split on headings, then 900-character windows with 150 overlap, each chunk prefixed `"{title} - {heading}"`.
- **Files:** `sample_data/knowledge_base/*.md`, `rag/chunking.py`, `tests/rag/test_chunking.py`
- **Done when:** Loading yields 15 articles; every chunk carries the title–heading prefix and respects the window and overlap sizes.

**P5-2 · Vector store and fake embeddings**
- **Needs:** `P5-1`
- **Build:** Vector store behind a protocol (`add_documents`, `search`, `delete`, `count`, `health`) with `InMemoryVectorStore` and `QdrantVectorStore` chosen by `VECTOR_STORE`, plus 384-dimension hashed bag-of-words fake embeddings.
- **Files:** `rag/vector_store.py`, `rag/embeddings.py`, `tests/rag/test_vector_store.py`
- **Done when:** The in-memory store passes add, search, delete, and count; the selector returns the right class; nothing outside `rag/` knows which store is live.

**P5-3 · Hybrid retriever**
- **Needs:** `P5-2`, `P3-3`
- **Build:** Hybrid retriever: semantic ∪ BM25 → reciprocal rank fusion (k=60) → heuristic rerank → optional LLM rerank → one hit per article. Modes `hybrid`, `semantic`, `keyword`; results cached 300 s under `rag:{mode}:{category}:{top_k}:{query}`.
- **Files:** `rag/retriever.py`, `tests/rag/test_retriever.py`
- **Done when:** Key queries return the expected article in the top 3 (hit-rate@3 is measured); each mode, the cache, RRF, rerank, and the category filter have tests.

**P5-4 · Ingest command and knowledge API**
- **Needs:** `P5-3`, `P3-1`
- **Build:** Ingest and the knowledge API: `make ingest`, `GET /knowledge/articles`, `GET /knowledge/articles/{id}`, `POST /knowledge/search`, and admin-only `POST /knowledge/reindex` that recreates the collection.
- **Files:** `rag/ingest.py`, `backend/app/api/knowledge.py`, `Makefile`, `tests/api/test_knowledge.py`
- **Done when:** `make ingest` reports article and chunk counts; the MFA lockout query returns its article in the top 3; non-admins get 403 on reindex.

---

## Phase 6 — Tools and mocks

> Depends on: P2-3. P6-2 also needs P5-3 (`search_docs` calls the retriever) and P2-4 (`check_service_status` reads the incident data). Parallel with: Phases 4, 5, 7, and 12.
> Merge order: P6-1 and P6-4 in parallel. P6-2 and P6-3 in parallel after both. P6-5 after P6-2.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P6-1 · Tool registry and policy | F9 | `feature/tool-registry-policy` | Pending ❌ |
| P6-2 · Read-only support tools | F4, F5, F7 | `feature/tools-read-only` | Pending ❌ |
| P6-3 · Approval-gated write tools | F9 | `feature/tools-approval-gated` | Pending ❌ |
| P6-4 · Mock integrations | — | `feature/integrations-mock` | Pending ❌ |
| P6-5 · MCP read-only server and `/mcp/tools` | — | `feature/mcp-server` | Pending ❌ |

#### Task definitions

**P6-1 · Tool registry and policy**
- **Needs:** `P2-3`
- **Build:** The tool registry and policy: `ToolPolicy` with an explicit approval bit per tool, `ToolRegistry.execute(name, args, approved=…)`, unknown tools requiring approval, `TOOL_TIMEOUT_SECONDS`, and exceptions turned into `ToolResult(ok=False)`.
- **Files:** `backend/app/tools/policy.py`, `backend/app/tools/registry.py`, `tests/unit/test_tool_policy.py`
- **Done when:** Reads and `update_ticket` need no approval; `reset_demo_setting` and `create_refund_request` do; unknown tools do; a raising tool returns `ok=False`; a slow tool times out.

**P6-2 · Read-only support tools**
- **Needs:** `P6-1`, `P6-4`, `P5-3`, `P2-4`
- **Build:** The read-only tools: `get_customer`, `get_subscription`, `get_ticket_history`, `search_docs`, `check_service_status`. Each is an async `@tool` whose docstring is its description.
- **Files:** `backend/app/tools/read_tools.py`, `tests/unit/test_read_tools.py`
- **Done when:** Every tool runs only through the registry and returns the documented shape; none writes.

**P6-3 · Approval-gated write tools**
- **Needs:** `P6-1`, `P6-4`
- **Build:** The write tools: `update_ticket` and `create_escalation` (no approval), `reset_demo_setting` and `create_refund_request` (approval required; `APPROVAL_REQUIRED_FOR_REFUNDS`, `MAX_REFUND_WITHOUT_APPROVAL` default 0).
- **Files:** `backend/app/tools/write_tools.py`, `tests/unit/test_write_tools.py`
- **Done when:** A direct registry call to `create_refund_request` without `approved=True` writes nothing; with it, the refund is recorded once (F9).

**P6-4 · Mock integrations**
- **Needs:** `P2-3`
- **Build:** Integration protocols and mock adapters: no real email, no real refunds. `core` never imports `integrations`.
- **Files:** `integrations/protocols.py`, `integrations/mock/services.py`, `integrations/factory.py`
- **Done when:** The factory returns mocks in demo mode; a test fails if anything under `core/` imports `integrations`.

**P6-5 · MCP read-only server and `/mcp/tools`**
- **Needs:** `P6-2`
- **Build:** A read-only MCP server exposing the read tools, a client example, `make mcp`, and `GET /mcp/tools`.
- **Files:** `integrations/mcp/server.py`, `integrations/mcp/client_example.py`, `backend/app/api/mcp.py`, `Makefile`
- **Done when:** `/mcp/tools` lists `name`, `description`, and `requires_approval`; no write tool is exposed.

---

## Phase 7 — Rules and guardrails

> Depends on: P2-1. Parallel with: Phases 4, 5, 6, and 12.
> Merge order: all four branches can be open together. They live in separate modules.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P7-1 · Escalation and severity rules | F3, F10 | `feature/policy-rules` | Pending ❌ |
| P7-2 · Injection wrapping and security preamble | N4 | `feature/guardrail-injection` | Pending ❌ |
| P7-3 · Customer output validation | N5 | `feature/guardrail-output-validation` | Pending ❌ |
| P7-4 · Secret scrub | N7 | `feature/guardrail-secret-scrub` | Pending ❌ |

#### Task definitions

**P7-1 · Escalation and severity rules**
- **Needs:** `P2-1`
- **Build:** Deterministic policy: category and severity rules (severity may rise, never fall) and `ESCALATION_RULES` for dispute, deletion, security, data loss, legal, and enterprise outage, each with a named team.
- **Files:** `agents/rules.py`, `tests/unit/test_rules.py`
- **Done when:** `CD-1005`, `CD-1006`, `CD-1009`, and `CD-1011` return escalation required with no model call; `CD-1010` stays low (F3, F10).

**P7-2 · Injection wrapping and security preamble**
- **Needs:** `P2-1`
- **Build:** Prompt-injection defence: `SECURITY_PREAMBLE`, `wrap_untrusted`, and `scan_for_injection`.
- **Files:** `agents/prompts.py` (`SECURITY_PREAMBLE`, `wrap_untrusted`), `backend/app/core/injection_guard.py` (`scan_for_injection`), `tests/unit/test_injection.py`
- **Done when:** `CD-1013` is flagged and its text is wrapped as data, never as instruction (N4).

**P7-3 · Customer output validation**
- **Needs:** `P2-1`
- **Build:** `validate_customer_output`, which blocks internal URLs, secrets, and another customer's data; a failure raises risk to `high`.
- **Files:** `backend/app/core/output_validation.py`, `tests/unit/test_output_validation.py`
- **Done when:** Each blocked pattern is rejected and the failure is reported as high risk (N5).

**P7-4 · Secret scrub**
- **Needs:** `P2-1`
- **Build:** `scrub()` and `SECRET_PATTERNS` for card numbers, API keys, and passwords.
- **Files:** `backend/app/core/scrub.py`, `tests/unit/test_scrub.py`
- **Done when:** Card, key, and password fixtures are removed; clean text is unchanged (N7).

---

## Phase 8 — Memory

> Depends on: P2-3, P3-3 (the Redis client), and P7-4. Parallel with: Phase 12. Does not wait for the graph.
> Merge order: P8-1 and P8-2 in parallel. P8-3 after both.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P8-1 · Short-term Redis facade | F11 | `feature/memory-short-term` | Pending ❌ |
| P8-2 · Long-term customer memory | F4, F11 | `feature/memory-long-term` | Pending ❌ |
| P8-3 · Recall and record service | F4, F11, N7 | `feature/memory-service` | Pending ❌ |

#### Task definitions

**P8-1 · Short-term Redis facade**
- **Needs:** `P3-3`, `P7-4`
- **Build:** Short-term memory on Redis: conversation per ticket and workflow state (24 h TTL) and the retrieval cache (300 s).
- **Files:** `memory/short_term.py`, `tests/unit/test_short_term.py`
- **Done when:** With fakeredis, entries expire at the stated TTLs and the cache key shape matches `rag:{mode}:{category}:{top_k}:{query}`.

**P8-2 · Long-term customer memory**
- **Needs:** `P2-3`, `P7-4`
- **Build:** Long-term memory in `customer_memory`: types `preference`, `past_issue`, `troubleshooting`, `note`; permanent and de-duplicated.
- **Files:** `memory/long_term.py`, `tests/unit/test_long_term.py`
- **Done when:** Recall returns at most 10 notes; an exact duplicate is skipped.

**P8-3 · Recall and record service**
- **Needs:** `P8-1`, `P8-2`
- **Build:** The memory service: `recall_customer()` and `record_resolution()` (past issue, first three troubleshooting steps, resolution note). Every note passes `scrub()`.
- **Files:** `memory/memory_service.py`, `tests/unit/test_memory_service.py`
- **Done when:** Card numbers, keys, passwords, and raw ticket bodies never reach `customer_memory`; nothing from another customer is stored (N7).

---

## Phase 9 — Specialist agents

> Depends on: Phases 5, 6, 7, and 8. Parallel with: nothing required inside the phase after P9-1.
> Merge order: P9-1 first. P9-2 through P9-8 in parallel after it. Each agent branch carries its own test.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P9-1 · Workflow schemas and fake LLM | F14 | `feature/workflow-schemas-fake-llm` | Pending ❌ |
| P9-2 · Supervisor agent | F2, F3 | `feature/agent-supervisor` | Pending ❌ |
| P9-3 · Customer agent | F4 | `feature/agent-customer` | Pending ❌ |
| P9-4 · Knowledge agent | F5, F6 | `feature/agent-knowledge` | Pending ❌ |
| P9-5 · Troubleshooting agent | F7 | `feature/agent-troubleshooting` | Pending ❌ |
| P9-6 · Resolution agent | F8 | `feature/agent-resolution` | Pending ❌ |
| P9-7 · Escalation agent | F10 | `feature/agent-escalation` | Pending ❌ |
| P9-8 · Eval case dataset | F2 | `feature/agent-eval-cases` | Pending ❌ |

#### Task definitions

**P9-1 · Workflow schemas and fake LLM**
- **Needs:** `P5-4`, `P6-3`, `P7-1`, `P7-2`, `P7-3`, `P7-4`, `P8-3`
- **Build:** Workflow schemas and the LLM layer: `Classification`, `SeverityAssessment`, `CustomerContext`, `Evidence`, `PreviousCase`, `Diagnosis`, `ResolutionPlan`, `EscalationDecision`, `WorkflowState`; `get_llm()` with the fake provider; `call_structured` for telemetry, usage, and retry.
- **Files:** `backend/app/schemas/workflow.py`, `backend/app/core/llm.py`, `tests/unit/test_llm.py`
- **Done when:** The fake provider returns valid structured output with cost `0.0`; no code calls a model except through `call_structured`.

**P9-2 · Supervisor agent**
- **Needs:** `P9-1`
- **Build:** Supervisor agent: classify into one of the 10 categories with a one-line summary, assess severity (rules may raise it), and write the ticket summary.
- **Files:** `agents/specialists/supervisor.py`, `tests/agents/test_supervisor.py`
- **Done when:** Classification, summary, and severity with reason are produced; `CD-1010` stays low (F2, F3).

**P9-3 · Customer agent**
- **Needs:** `P9-1`
- **Build:** Customer agent: loads customer, subscription, workspace, previous tickets, and up to 10 memory notes through the read tools. It makes no model call.
- **Files:** `agents/specialists/customer.py`, `tests/agents/test_customer.py`
- **Done when:** A known demo customer returns a full `CustomerContext` with no model call (F4).

**P9-4 · Knowledge agent**
- **Needs:** `P9-1`
- **Build:** Knowledge agent: cited evidence through `search_docs` and similar resolved cases by Jaccard overlap.
- **Files:** `agents/specialists/knowledge.py`, `tests/agents/test_knowledge.py`
- **Done when:** Evidence carries `id`, `title`, `source`, `snippet`, and `score`; similar cases are returned (F5, F6).

**P9-5 · Troubleshooting agent**
- **Needs:** `P9-1`
- **Build:** Troubleshooting agent: probable causes and numbered steps, enriched by a playbook per category and `check_service_status`.
- **Files:** `agents/specialists/troubleshooting.py`, `tests/agents/test_troubleshooting.py`
- **Done when:** A `Diagnosis` with causes and numbered steps is produced (F7).

**P9-6 · Resolution agent**
- **Needs:** `P9-1`
- **Build:** Resolution agent: summary, customer reply, internal notes, and actions. Actions come from the deterministic `plan_actions`, never invented by the model; the reply is grounded and validated.
- **Files:** `agents/specialists/resolution.py`, `tests/agents/test_resolution.py`
- **Done when:** Actions equal `plan_actions` output; the reply passes `validate_customer_output`; grounding is measurable (F8).

**P9-7 · Escalation agent**
- **Needs:** `P9-1`
- **Build:** Escalation agent: policy rules always win; a vague model escalation is distrusted unless severity is high with enough confidence; uses `create_escalation`.
- **Files:** `agents/specialists/escalation.py`, `tests/agents/test_escalation.py`
- **Done when:** Policy cases escalate to the named team; a low-confidence model escalation does not (F10).

**P9-8 · Eval case dataset**
- **Needs:** `P9-1`
- **Build:** The evaluation dataset: one case per demo ticket at least, each with a valid `expected_category`, expected escalation, and expected article.
- **Files:** `datasets/eval_cases.json`
- **Done when:** A test rejects any case whose `expected_category` is not one of the 10 categories.

---

## Phase 10 — Workflow graph and trace

> Depends on: Phase 9. Unblocks: Phase 11.
> Merge order: P10-1 first. P10-2, P10-3, P10-4, and P10-6 in parallel. P10-5 last (it wires the nodes). P10-7 after P10-5.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P10-1 · Support state and checkpointer | F11 | `feature/graph-state-checkpointer` | Pending ❌ |
| P10-2 · Supervisor graph nodes | F2, F3 | `feature/graph-nodes-supervisor` | Pending ❌ |
| P10-3 · Investigate graph nodes | F4, F5, F7 | `feature/graph-nodes-investigate` | Pending ❌ |
| P10-4 · Resolution and risk nodes | F9, F10 | `feature/graph-nodes-resolution` | Pending ❌ |
| P10-5 · Graph wiring and run API | F11 | `feature/graph-run-api` | Pending ❌ |
| P10-6 · Workflow tracer and events API | F13 | `feature/workflow-tracer-events` | Pending ❌ |
| P10-7 · Agents overview API (`GET /agents`) | F13 | `feature/api-agents` | Pending ❌ |

#### Task definitions

**P10-1 · Support state and checkpointer**
- **Needs:** `P9-1`
- **Build:** `SupportState` with reducers (`errors` and `completed_nodes` append, `token_usage` sums via `merge_usage`) and the checkpointer (`InMemorySaver` for `:memory:`, `AsyncSqliteSaver` for a file).
- **Files:** `agents/state.py`, `agents/checkpointer.py`, `tests/workflow/test_state.py`
- **Done when:** Reducers never overwrite; the right saver is chosen from `CHECKPOINT_DB_PATH`.

**P10-2 · Supervisor graph nodes**
- **Needs:** `P10-1`, `P9-2`
- **Build:** Graph nodes for the supervisor: `understand_ticket`, `classify_severity`, `ticket_summary`, each in the standard node shape with tracer start and finish.
- **Files:** `agents/nodes/supervisor.py`, `tests/workflow/test_nodes_supervisor.py`
- **Done when:** Each node returns a partial state dict with its id in `completed_nodes`.

**P10-3 · Investigate graph nodes**
- **Needs:** `P10-1`, `P9-3`, `P9-4`, `P9-5`
- **Build:** Graph nodes that investigate: `customer_context`, `knowledge_retrieval`, `troubleshooting`.
- **Files:** `agents/nodes/investigate.py`, `tests/workflow/test_nodes_investigate.py`
- **Done when:** Each node records its tool calls and model usage and returns a partial state dict.

**P10-4 · Resolution and risk nodes**
- **Needs:** `P10-1`, `P9-6`, `P9-7`
- **Build:** Graph nodes for the decision: `resolution_planning`, `risk_check` (`assess_risk()` returns `high` for approval-required plans, policy escalation, critical severity, injection, or failed output validation), `execute_resolution` (runs the planned actions that need no approval through `ToolRegistry.execute`), and `memory_update`.
- **Files:** `agents/nodes/decision.py`, `tests/workflow/test_risk.py`, `tests/workflow/test_execute_resolution.py`
- **Done when:** Risk is `high` in each listed case and `low` for `CD-1010`; a low-risk plan's actions run through the registry and nothing that needs approval runs.

**P10-5 · Graph wiring and run API**
- **Needs:** `P10-2`, `P10-3`, `P10-4`
- **Build:** Wire the graph and the run API: `agents/graph.py` (with `GRAPH_NODES` and `GRAPH_EDGES`), `workflow_service`, `POST /tickets/{id}/run` (202) and `GET /tickets/{id}/workflow`. State is saved after every node. The approval and escalation branches are named edges to nodes that P11-1 and P11-3 add; until then a ticket that is not low risk ends the run as `failed` with an error and executes nothing.
- **Files:** `agents/graph.py`, `backend/app/services/workflow_service.py`, `backend/app/api/workflow.py`, `tests/workflow/test_graph.py`
- **Done when:** A low-risk ticket runs to END; polling `/workflow` reaches `completed`; a ticket that is not low risk executes no action; graph shape and routing are tested.

**P10-6 · Workflow tracer and events API**
- **Needs:** `P10-1`
- **Build:** `WorkflowTracer` writing `workflow_events` and never raising (`node_started`, `node_completed`, `tool_called`, `llm_called`, `approval_requested`, `approval_resolved`, `error`, `workflow_completed`) and `GET /tickets/{id}/events`.
- **Files:** `backend/app/core/observability.py`, `backend/app/api/events.py`, `tests/workflow/test_trace.py`
- **Done when:** Events include duration, tokens, and cost; a failing tracer does not fail the run; raw prompts are never stored (F13).

**P10-7 · Agents overview API (`GET /agents`)**
- **Needs:** `P10-5`
- **Build:** `GET /agents`: agent info, the graph nodes and edges, recent runs, and run statistics.
- **Files:** `backend/app/api/agents.py`, `tests/api/test_agents.py`
- **Done when:** The response matches the contract and the graph comes from `GRAPH_NODES` and `GRAPH_EDGES`.

---

## Phase 11 — Approval and escalation

> Depends on: P6-3 and Phase 10. Unblocks: the ticket action screen and `make demo`.
> Merge order: P11-1 and P11-3 in parallel. P11-2 after P11-1. P11-4 after P11-1 and P11-3. P11-5 last. P11-6 after P11-3.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P11-1 · Human approval interrupt | F9 | `feature/workflow-human-approval` | Pending ❌ |
| P11-2 · Approval decide and resume API | F9 | `feature/api-approvals-resume` | Pending ❌ |
| P11-3 · Escalation routing | F10 | `feature/workflow-escalation-routing` | Pending ❌ |
| P11-4 · Execute resolution on the shared tool path | F9 | `feature/workflow-execute-resolution` | Pending ❌ |
| P11-5 · Demo script for CD-1002 and CD-1005 | F9, F10 | `feature/demo-approval-escalation` | Pending ❌ |
| P11-6 · Escalations API (list and update) | F10 | `feature/api-escalations` | Pending ❌ |

#### Task definitions

**P11-1 · Human approval interrupt**
- **Needs:** `P10-5`, `P6-3`
- **Build:** The `human_approval` node calls `interrupt()`; the service writes `approval_requests` and sets the ticket to `waiting_on_approval`. `POST /tickets/{id}/run` returns 409 while the ticket is `waiting_on_approval`. Code before `interrupt()` is idempotent.
- **Files:** `agents/nodes/human_approval.py`, `tests/workflow/test_approval_interrupt.py`
- **Done when:** `CD-1002` pauses with a pending approval row and the ticket in `waiting_on_approval`; a second run during the pause returns 409 (F9).

**P11-2 · Approval decide and resume API**
- **Needs:** `P11-1`
- **Build:** Approval API: `GET /approvals`, `GET /approvals/{id}`, `POST /approvals/{id}/approve` and `/reject`, resuming with `Command(resume=…)`.
- **Files:** `backend/app/api/approvals.py`, `backend/app/services/approval_service.py`, `tests/api/test_approvals.py`
- **Done when:** Approve resumes and finishes the run; reject routes to escalation; resuming a run that is not paused returns 409; a viewer gets 403.

**P11-3 · Escalation routing**
- **Needs:** `P10-5`
- **Build:** Escalation routing: policy cases and rejected approvals go to `escalation`, which records a named team, without an approval wait.
- **Files:** `agents/nodes/escalation.py`, `tests/workflow/test_escalation_routing.py`
- **Done when:** `CD-1005`, `CD-1006`, `CD-1009`, and `CD-1011` escalate by rule; `CD-1013` takes no export action.

**P11-4 · Execute resolution on the shared tool path**
- **Needs:** `P11-1`, `P11-3`
- **Build:** Extend `execute_resolution` (built for low-risk plans in P10-4) so that after a human approval the approved actions run through the same `ToolRegistry.execute` with `approved=True`. The automatic and approved paths stay one code path.
- **Files:** `agents/nodes/decision.py`, `tests/workflow/test_execute_resolution.py`
- **Done when:** The refund tool runs exactly once after approval; nothing runs unapproved.

**P11-5 · Demo script for CD-1002 and CD-1005**
- **Needs:** `P11-2`, `P11-4`
- **Build:** The terminal demo: `make demo` runs `CD-1002` end to end and pauses for approval; `make demo TICKET=CD-1005` escalates.
- **Files:** `scripts/demo.py`, `Makefile`
- **Done when:** Both demos behave as stated, offline, with the fake provider.

**P11-6 · Escalations API (list and update)**
- **Needs:** `P11-3`, `P3-1`
- **Build:** Escalations API: `GET /escalations?status=` and `PATCH /escalations/{id}` (`open`, `acknowledged`, `resolved`, with a note).
- **Files:** `backend/app/api/escalations.py`, `tests/api/test_escalations.py`
- **Done when:** Responses and status changes match the contract.

---

## Phase 12 — Console shell

> Depends on: P4-1 and P3-2. Parallel with: Phases 5 through 11.
> Each P12-4 page needs its API: dashboard, audit, and settings after P4-5; tickets and customers after P4-2 and P4-3; knowledge after P5-4; agents after P10-7; escalations after P11-6. Build a page when its API lands.
> Merge order: P12-1 and P12-2 in parallel. P12-3 after both. P12-4 after P12-3.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P12-1 · Next.js app shell and navigation | F12 | `feature/frontend-app-shell` | Pending ❌ |
| P12-2 · Typed API client | F12 | `feature/frontend-api-client` | Pending ❌ |
| P12-3 · Login and role-aware layout | F12, N1 | `feature/frontend-auth-layout` | Pending ❌ |
| P12-4 · Read-only list pages | F12 | `feature/frontend-read-pages` | Pending ❌ |

#### Task definitions

**P12-1 · Next.js app shell and navigation**
- **Needs:** `P4-1`
- **Build:** The Next.js 15 App Router shell with TypeScript and Tailwind, the hand-written `components/ui/` kit (no UI library, no gradients), navigation declared once, and `/api/health`.
- **Files:** `frontend/app/`, `frontend/components/`, `frontend/components/layout/nav.ts`
- **Done when:** `npm run lint` and `npm run build` pass; the app shows the navigation.

**P12-2 · Typed API client**
- **Needs:** `P4-1`
- **Build:** The typed API client: bearer token in `localStorage`, a 401 redirects to `/login?reason=expired`, a `NetworkError` banner with auto-retry, types mirroring `API_CONTRACT.md`, and the `usePolling` hook.
- **Files:** `frontend/lib/api.ts`, `types.ts`, `hooks.ts`, `format.ts`, `cn.ts`, `frontend/__tests__/`
- **Done when:** Tests cover the 401 redirect and the retry; the service-role key appears nowhere in the frontend.

**P12-3 · Login and role-aware layout**
- **Needs:** `P12-1`, `P12-2`, `P3-2`
- **Build:** Login with the demo users and a role-aware layout: the role comes from `/auth/me`, and a viewer sees action buttons disabled (`canAct`).
- **Files:** `frontend/app/login/`, layout components
- **Done when:** Each of the three demo users can log in; viewer controls render disabled.

**P12-4 · Read-only list pages**
- **Needs:** `P12-3`, `P4-2`, `P4-3`, `P4-5`
- **Build:** Read-only pages: `/dashboard`, `/tickets`, `/customers`, `/customers/[id]`, `/knowledge`, `/escalations`, `/agents`, `/audit`, `/settings`. Build each page when its API has merged.
- **Files:** `frontend/app/(dashboard)/`
- **Done when:** Every page loads against the running backend with real data or a clear empty state.

---

## Phase 13 — Ticket workflow screen

> Depends on: Phase 11 and Phase 12. P13-3 also needs P4-4 (the reply, request-info, and escalate routes). This is the only UI phase that waits on the graph.
> Merge order: P13-1 first. P13-2 and P13-3 in parallel after it. P13-4 after both.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P13-1 · Ticket detail layout | F12 | `feature/frontend-ticket-layout` | Pending ❌ |
| P13-2 · Workflow steps and polling | F12, F13 | `feature/frontend-workflow-panel` | Pending ❌ |
| P13-3 · Approve, reject, reply, and escalate actions | F12, F9 | `feature/frontend-ticket-actions` | Pending ❌ |
| P13-4 · Frontend unit tests | F12 | `feature/frontend-unit-tests` | Pending ❌ |

#### Task definitions

**P13-1 · Ticket detail layout**
- **Needs:** `P12-4`, `P10-5`
- **Build:** The ticket detail layout at `/tickets/[id]`: three columns — messages and composer, customer panel, workflow panel.
- **Files:** `frontend/app/(dashboard)/tickets/[id]/page.tsx`, ticket components
- **Done when:** A ticket opens with its messages, customer context, and an empty workflow panel.

**P13-2 · Workflow steps and polling**
- **Needs:** `P13-1`, `P10-6`
- **Build:** The workflow panel: twelve steps polled every 2 s, chips, evidence, diagnosis, planned actions, and an editable reply.
- **Files:** ticket workflow components, `deriveSteps`
- **Done when:** Running a workflow shows each step finish in order until `completed`.

**P13-3 · Approve, reject, reply, and escalate actions**
- **Needs:** `P13-1`, `P11-2`, `P4-4`
- **Build:** Actions on the ticket screen: Approve and Reject (only when `approval_status` is `pending`), send reply, request info, and escalate.
- **Files:** ticket action components
- **Done when:** As the agent, `CD-1002` can be approved and replied to; as the viewer, every action stays disabled (F12).

**P13-4 · Frontend unit tests**
- **Needs:** `P13-2`, `P13-3`
- **Build:** Frontend unit tests: StatusPill, EmptyState, `WorkflowSteps.deriveSteps`, and the API helpers.
- **Files:** `frontend/__tests__/`
- **Done when:** `npm run lint`, `npm run test -- --run`, and `npm run build` all pass.

---

## Phase 14 — Evaluation and delivery

> Depends on: Phase 11 for the eval suite and the demo. Image and Terraform files do not import the graph.
> Merge order: P14-1 after Phase 11. P14-2, P14-3, and P14-4 in parallel once the app boots. P14-5 after P14-2 and P14-3.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P14-1 · Evaluation thresholds | F2, F5, F8, F10 | `feature/eval-thresholds` | Pending ❌ |
| P14-2 · Backend and frontend Dockerfiles | N8 | `feature/docker-images` | Pending ❌ |
| P14-3 · Compose stack | N8 | `feature/docker-compose` | Pending ❌ |
| P14-4 · Terraform and CI scaffolds | N8 | `feature/delivery-terraform-ci` | Pending ❌ |
| P14-5 · Deployment hygiene tests | N8 | `feature/deployment-hygiene-tests` | Pending ❌ |

#### Task definitions

**P14-1 · Evaluation thresholds**
- **Needs:** `P11-5`, `P9-8`
- **Build:** The evaluation suite over `datasets/eval_cases.json` with thresholds that fail the build: classification ≥ 0.80, retrieval hit-rate@3 ≥ 0.75, escalation correctness ≥ 0.90, citation rate ≥ 0.90, grounding rate ≥ 0.90.
- **Files:** `tests/evaluation/`
- **Done when:** The suite passes offline and fails when any threshold is missed.

**P14-2 · Backend and frontend Dockerfiles**
- **Needs:** `P10-5`
- **Build:** Dockerfiles: the backend is multi-stage `python:3.12-slim`, non-root user `app`, `HEALTHCHECK` on `/health/live`, built from the repo root; the frontend is `node:22-alpine` with `output: "standalone"`, non-root, `HEALTHCHECK` on `/api/health`.
- **Files:** `backend/Dockerfile`, `frontend/Dockerfile`
- **Done when:** Both images build and report healthy.

**P14-3 · Compose stack**
- **Needs:** `P14-2`
- **Build:** The Compose stack: frontend → backend → redis and qdrant, `depends_on: service_healthy`, named volumes, `restart: unless-stopped`.
- **Files:** `docker-compose.yml`
- **Done when:** `docker compose config -q` succeeds and the stack comes up healthy.

**P14-4 · Terraform and CI scaffolds**
- **Needs:** `P14-2`
- **Build:** Terraform for AWS, Azure, and GCP from shared modules (networking, container registry, secrets, compute, load balancer, monitoring, redis) with `environments/{dev,staging,prod}` var-files, the five deploy scripts (`--auto-approve` refused for staging and prod), and five GitHub workflows (`test`, `security`, `docker-build`, `terraform-validate`, `_deploy`).
- **Files:** `deployment/`, `.github/workflows/`, `Makefile`
- **Done when:** `make terraform-validate` passes locally. Nothing is applied and no workflow is claimed to have run.

**P14-5 · Deployment hygiene tests**
- **Needs:** `P14-2`, `P14-3`
- **Build:** Deployment hygiene tests: compose services, non-root Dockerfiles with `HEALTHCHECK`, `.env.example` coverage, no committed `.env`; and `BASE_URL=http://localhost:8000 make smoke`.
- **Files:** `tests/deployment/`, `deployment/scripts/smoke_test.sh`
- **Done when:** The tests pass and the smoke test passes against the local stack.

---

## Finished when

The whole project is finished only when all of these are true. The first three are the acceptance bar from `PLAN.md`:

- Every requirement F1–F14 and N1–N8 has at least one passing test (the **Covers** column maps each to its tasks).
- `make test` passes with no network and no API key, and the five evaluation thresholds are met.
- `make demo` pauses on `CD-1002` for approval and escalates `CD-1005` by rule; `CD-1013` exports nothing; a viewer gets 403 on run, reply, and approve.
- `docker compose config -q` and `make terraform-validate` pass locally.
- All 67 tasks are Completed ✅ and the Progress summary reads 67 of 67.
- The Honest status in `MEMORY.md` is still true: it must keep saying no cloud credentials were used, nothing was applied, and no GitHub Actions run happened, until they really have.

---

## Dependency overview

```text
P1 Runtime
  └─► P2 Data
        ├─► P3 Identity ─► P4 Support API ─► P12 Console shell ─┐
        ├─► P5 Knowledge ─────────────────────────────────────┐ │
        ├─► P6 Tools ─────────────────────────────────────────┤ │
        └─► P7 Guardrails ─► P8 Memory ───────────────────────┤ │
                              │                               │ │
                              └─► P9 Specialists ◄────────────┘ │
                                    └─► P10 Graph                │
                                          └─► P11 Approval       │
                                                └─► P13 Ticket UI ◄┘
                                                      └─► P14 Eval and delivery
```

Phases 4, 5, 6, and 7 start together once Phase 2 has merged. Phase 4 also waits for P3-1, and Phase 5 for P3-3 (and P3-1 for P5-4). Phase 12 starts when the API contract exists and does not wait for agents. Phase 13 is the join of the console shell and the approval workflow.

---

## Progress summary

| Phase | Name | Tasks | Completed |
|-------|------|-------|-----------|
| 1 | Runtime skeleton | 4 | 3 |
| 2 | Persistence and demo data | 4 | 0 |
| 3 | Identity and request guards | 4 | 0 |
| 4 | Support API | 5 | 0 |
| 5 | Knowledge pipeline | 4 | 0 |
| 6 | Tools and mocks | 5 | 0 |
| 7 | Rules and guardrails | 4 | 0 |
| 8 | Memory | 3 | 0 |
| 9 | Specialist agents | 8 | 0 |
| 10 | Workflow graph and trace | 7 | 0 |
| 11 | Approval and escalation | 6 | 0 |
| 12 | Console shell | 4 | 0 |
| 13 | Ticket workflow screen | 4 | 0 |
| 14 | Evaluation and delivery | 5 | 0 |
| **Total** | | **67** | **3** |
