# CloudDesk AI architecture

_Last updated: 2026-11-27 22:43 +0530_

Target architecture for the autonomous support-resolution platform. `CLAUDE.md` wins if this document disagrees with it.

These are CloudDesk's own diagrams, for the single-tenant v1 this repository builds. The upstream
high-level and low-level designs for the full product are [`03_HLD.md`](../03_HLD.md) and [`04_LLD.md`](../04_LLD.md) one folder up;
`CLAUDE.md` §1.1 tables where the two differ and §20 lists the decisions still open.

This is the design, and v1 of it is built: all 14 phases exist and run locally in Docker on real services (PostgreSQL, Redis, a local Qdrant container, Euron embeddings and chat). What is not built: row-level security enforced at runtime, the approval timeout, and the decisions D2, D3, D5 and D6 in `CLAUDE.md` §20. The Terraform and the GitHub workflows are written and validated only: no cloud account has been applied, no workflow has run, and nothing in these diagrams is deployed.

The product is used by support agents of the fictional software as a service (SaaS) **CloudDesk**. A ticket is understood, classified, investigated, and turned into a resolution plan. A human approves anything that spends money or changes an account. v1 integrations are mocks: the platform does not send real email and does not issue real refunds.

## How to create the diagrams in Eraser

Eraser cloud-architecture diagrams use [Eraser diagram-as-code](https://docs.eraser.io/architecture-diagram-syntax), not Mermaid. Mermaid pasted into a Cloud Architecture diagram will not lay out.

For each diagram below:

1. In [Eraser](https://app.eraser.io), create a diagram and set the type to **Cloud architecture**.
2. Open **Diagram as code**.
3. Paste one fenced `eraser` block, without the fence.
4. Leave the Mermaid block for a flowchart, sequence, or ER tool. Eraser can also generate those if you choose **Flow chart**, **Sequence diagram**, or **Entity relationship** and paste the matching block when the type is Mermaid-compatible. The `eraser` blocks are the ones that produce the component and infrastructure pictures.

Create one Eraser diagram per block. Do not paste two blocks into the same diagram; node names would collide.

| Diagram | Eraser type | What it shows |
|---|---|---|
| 1 | Cloud architecture | Complete logical system |
| 2 | Cloud architecture | Backend components and layers |
| 3 | Cloud architecture | LangGraph nodes |
| 4 | Cloud architecture | Local Docker Compose |
| 5 | Cloud architecture | Amazon Web Services (AWS) |
| 6 | Cloud architecture | Azure |
| 7 | Cloud architecture | Google Cloud Platform (GCP) |
| 8 | Cloud architecture | CI/CD |
| 9 | Sequence diagram | Run, pause, approve, reply |
| M1–M4 | Mermaid | The same flows, plus the data model |

---

## 1. System context

Three roles share one console. The browser talks only to Next.js. Next.js calls FastAPI. FastAPI owns the workflow. Data stores and the model sit behind the backend.

| Actor | Enters through | May do |
|---|---|---|
| Viewer | Console | Read tickets, customers, knowledge, and audit |
| Agent | Console | Run a workflow, reply, request information, approve or reject, escalate |
| Admin | Console | Reindex knowledge. Settings are read-only in v1 |

Role rank is `viewer 1 < agent 2 < admin 3`, enforced by `require_role`. Demo users are `admin@clouddesk.demo`, `sam.agent@clouddesk.demo`, and `vic.viewer@clouddesk.demo`.

```eraser
direction down

Viewer [icon: users, color: grey, label: "Viewer"]
Agent [icon: users, color: blue, label: "Agent"]
Admin [icon: users, color: blue, label: "Admin"]

Console [icon: next, color: blue, label: "Next.js 15 console :3000"]

Platform [icon: fastapi, color: green, label: "FastAPI :8000"] {
  Edge [icon: shield, label: "JWT, rate limit, audit, request id"]
  Workflow [icon: langgraph, label: "LangGraph workflow"]
}

Stores [icon: postgres, color: blue, label: "Data stores"] {
  SQL [icon: postgres, label: "PostgreSQL or SQLite"]
  Cache [icon: redis, label: "Redis or fakeredis"]
  Vectors [icon: qdrant, label: "Qdrant or in-memory"]
}

Outside [icon: openai, color: purple, label: "External"] {
  Model [icon: openai, label: "LLM or fake provider"]
  Smith [icon: langgraph, label: "LangSmith optional"]
}

Viewer > Console: "read"
Agent > Console: "act"
Admin > Console: "reindex and settings"
Console > Edge: "HTTPS REST /api/v1"
Edge > Workflow: "background run"
Workflow > SQL: "tickets, events, memory"
Workflow > Cache: "session, limit, RAG cache"
Workflow > Vectors: "knowledge search"
Workflow > Model: "call_structured"
Workflow --> Smith: "optional traces"
```

```mermaid
flowchart TB
  subgraph people [People]
    Viewer[Viewer]
    AgentUser[Agent]
    Admin[Admin]
  end

  Console["Next.js 15 console :3000"]

  subgraph platform [FastAPI :8000]
    Edge["JWT, rate limit, audit, request id"]
    Workflow[LangGraph workflow]
  end

  subgraph stores [Data stores]
    SQL["PostgreSQL or SQLite"]
    Cache["Redis or fakeredis"]
    Vectors["Qdrant or in-memory"]
  end

  subgraph outside [External]
    Model["LLM or fake provider"]
    Smith["LangSmith optional"]
  end

  Viewer -->|read| Console
  AgentUser -->|act| Console
  Admin -->|reindex and settings| Console
  Console -->|"HTTPS REST /api/v1"| Edge
  Edge -->|background run| Workflow
  Workflow --> SQL
  Workflow --> Cache
  Workflow --> Vectors
  Workflow -->|call_structured| Model
  Workflow -.->|optional traces| Smith
```

![System context: the browser, the console, the API, the workflow and the data stores](diagrams/01-system-context.svg)

---

## 2. Component architecture

The workflow is one component inside a normal web application. Hypertext Transfer Protocol (HTTP), Structured Query Language (SQL), prompts, retrieval, and tools stay in separate folders.

| Layer | Folder | Does | Must not |
|---|---|---|---|
| Frontend | `frontend/` | Pages, polling, typed client | Hold the service-role key |
| Application programming interface (API) | `backend/app/api/` | HTTP, validation, auth, role-based access control (RBAC), background tasks | Contain business rules |
| Services | `backend/app/services/` | Orchestrate repositories and the graph | Talk HTTP |
| Repositories | `backend/app/repositories/` | SQL through SQLAlchemy | Call a model |
| Core | `backend/app/core/` | Config, large language model (LLM) factory, security, logging, Redis, guardrails, database | Import `agents/` |
| Tools | `backend/app/tools/` | `@tool` functions, `ToolPolicy`, `ToolRegistry` | Bypass the registry |
| Agents | `agents/` | State, graph, nodes, specialists, rules, prompts | Write SQL |
| Retrieval-augmented generation (RAG) | `rag/` | Chunk, embed, retrieve, ingest | Know about tickets |
| Memory | `memory/` | Short-term and long-term facades | Store secrets |
| Integrations | `integrations/` | Protocols, mock adapters, Model Context Protocol (MCP) server | Be imported by `core` |

### 2.1 Frontend

Next.js 15 App Router. The backend is reached only through `frontend/lib/api.ts`. The bearer token lives in `localStorage`. A 401 sends the user to `/login?reason=expired`. The ticket screen polls `/workflow` every 2 seconds.

Pages: `/login`, `/dashboard`, `/tickets`, `/tickets/[id]`, `/customers`, `/customers/[id]`, `/knowledge`, `/escalations`, `/agents`, `/audit`, `/settings`, `/api/health`.

The ticket screen is three columns: messages and composer, customer context, and the workflow panel. The workflow panel shows the twelve graph steps, evidence, diagnosis, planned actions, and an editable reply. Viewer action buttons stay disabled. Approve and Reject render only when `approval_status` is `pending`.

### 2.2 Backend edge

Middleware order, outermost first: Cross-Origin Resource Sharing (CORS), then RequestId, then RateLimit, then Audit. (`create_app()` adds them in the reverse order, Audit first, because the last one added is the outermost.)

| Concern | Behaviour |
|---|---|
| N1 JSON Web Token (JWT) | Hash-based message authentication code (HMAC) with SHA-256 (HS256), Supabase-compatible. Demo tokens last 8 hours |
| N2 Rate limit | Fixed window in Redis. Demo ceiling is 120 requests per minute |
| N3 Request id | `X-Request-ID` on every response |
| N6 Audit | One `audit_logs` row for every non-GET request |

Health routes are unprefixed: `/health`, `/health/live` (no I/O, used by probes), `/health/ready` (database, Redis, vector store, LLM).

### 2.3 Specialists

Every specialist returns a Pydantic model. Every model call goes through `call_structured`. Policy is decided in `agents/rules.py` before the model is trusted.

| Agent | Node | Produces | Tools |
|---|---|---|---|
| Supervisor | `understand_ticket`, `classify_severity`, `ticket_summary` | Category, summary, severity | None. Rules classify, score severity, and scan for injection |
| Customer | `customer_context` | Customer, subscription, workspace, history, notes | `get_customer`, `get_subscription`, `get_ticket_history`. No model call |
| Knowledge | `knowledge_retrieval` | Cited evidence, similar cases | `search_docs` |
| Troubleshooting | `troubleshooting` | Probable causes and numbered steps | `check_service_status` |
| Resolution | `resolution_planning` | Summary, customer reply, internal notes, actions | Plans `update_ticket`, `create_refund_request`, `reset_demo_setting` |
| Escalation | `risk_check`, `escalation` | Escalation decision and named team | `create_escalation` |

Planned actions come from `ResolutionAgent.plan_actions`. The model does not invent tool calls.

### 2.4 Tools

All execution goes through `ToolRegistry.execute`. Unknown tools require approval. A tool exception becomes `ToolResult(ok=False)` and does not crash the graph. Timeout is `TOOL_TIMEOUT_SECONDS`.

| Tool | Writes | Needs approval |
|---|---|---|
| `get_customer`, `get_subscription`, `get_ticket_history` | No | No |
| `search_docs`, `check_service_status` | No | No |
| `update_ticket` | Tickets | No |
| `reset_demo_setting` | Workspace admin | Yes |
| `create_refund_request` | Billing | Yes. `MAX_REFUND_WITHOUT_APPROVAL` defaults to 0 |
| `create_escalation` | Escalations | No. This is the safe path |

`assess_risk()` returns `high` when the plan needs approval, a policy escalation fired, severity is critical, injection was detected, or output validation failed.

### 2.5 Complete logical diagram

Paste this into one Cloud Architecture diagram. It is the full component picture.

```eraser
direction down

People [icon: users, color: blue, label: "Support org"] {
  Viewer [icon: users, label: "Viewer"]
  AgentUser [icon: users, label: "Agent"]
  AdminUser [icon: users, label: "Admin"]
}

Frontend [icon: next, color: blue, label: "Next.js 15"] {
  ApiClient [icon: react, label: "lib/api.ts"]
  TicketPage [icon: next, label: "Ticket screen"]
  OtherPages [icon: react, label: "Lists, knowledge, audit, settings"]
}

Backend [icon: fastapi, color: green, label: "FastAPI"] {
  Middleware [icon: shield, label: "CORS, request id, rate limit, audit"]
  Routers [icon: server, label: "API routers"]
  Services [icon: workflow, label: "Services"]
  Repos [icon: postgres, label: "Repositories"]
  CoreBox [icon: python, label: "Core and guardrails"]
}

GraphBox [icon: langgraph, color: orange, label: "LangGraph"] {
  Supervisor [icon: users, label: "Supervisor"]
  CustomerAg [icon: users, label: "Customer agent"]
  KnowledgeAg [icon: qdrant, label: "Knowledge agent"]
  TroubleAg [icon: workflow, label: "Troubleshooting agent"]
  ResolveAg [icon: workflow, label: "Resolution agent"]
  EscalateAg [icon: shield, label: "Escalation agent"]
  RulesBox [icon: shield, label: "Policy rules"]
}

Capabilities [icon: workflow, color: grey, label: "Capabilities"] {
  Registry [icon: workflow, label: "ToolRegistry"]
  Retriever [icon: qdrant, label: "Hybrid retriever"]
  MemoryBox [icon: redis, label: "Memory facades"]
  Mocks [icon: server, label: "Mock integrations"]
  MCPSrv [icon: workflow, label: "MCP read-only server"]
}

DataPlane [icon: postgres, color: blue, label: "Data plane"] {
  SQL [icon: postgres, label: "PostgreSQL or SQLite"]
  Cache [icon: redis, label: "Redis or fakeredis"]
  Vectors [icon: qdrant, label: "Qdrant or in-memory"]
  CheckDB [icon: sqlite, label: "Checkpoint SQLite"]
}

Models [icon: openai, color: purple, label: "Model plane"] {
  LLM [icon: openai, label: "LLM or fake provider"]
  Smith [icon: langgraph, label: "LangSmith optional"]
}

Viewer > ApiClient: "read"
AgentUser > TicketPage: "run, approve, reply"
AdminUser > OtherPages: "reindex, settings"
ApiClient > Middleware: "Bearer JWT"
Middleware > Routers
Routers > Services
Services > Repos
Services > Supervisor: "astream"
RulesBox > Supervisor: "policy wins"
Supervisor > CustomerAg
CustomerAg > KnowledgeAg
KnowledgeAg > TroubleAg
TroubleAg > ResolveAg
ResolveAg > EscalateAg
ResolveAg > Registry
KnowledgeAg > Retriever
CustomerAg > MemoryBox
Registry > Mocks
MCPSrv --> Registry: "read-only"
Repos > SQL
MemoryBox > Cache
MemoryBox > SQL
Retriever > Vectors
Services > CheckDB: "interrupt state"
CoreBox > LLM: "call_structured"
CoreBox --> Smith: "optional"
```

### 2.6 Backend internals

Paste this when you want the layer rules as their own diagram.

```eraser
direction right

HTTP [icon: monitor, label: "Browser"]

Edge [icon: shield, color: orange, label: "Middleware"] {
  CORS [icon: shield, label: "CORS"]
  ReqId [icon: workflow, label: "Request id"]
  Limit [icon: shield, label: "Rate limit"]
  Audit [icon: lock, label: "Audit"]
  AuthN [icon: lock, label: "JWT RBAC"]
}

Layers [icon: fastapi, color: green, label: "Layers"] {
  API [icon: server, label: "api"]
  Svc [icon: workflow, label: "services"]
  Repo [icon: postgres, label: "repositories"]
  Core [icon: python, label: "core"]
}

Domain [icon: langgraph, color: orange, label: "Domain"] {
  Agents [icon: langgraph, label: "agents"]
  Tools [icon: workflow, label: "tools"]
  RAG [icon: qdrant, label: "rag"]
  Mem [icon: redis, label: "memory"]
  Integ [icon: server, label: "integrations"]
}

HTTP > CORS
CORS > ReqId > Limit > Audit > AuthN > API
API > Svc
Svc > Repo
Svc > Agents
Agents > Tools
Agents > RAG
Agents > Mem
Tools > Integ
Core > API: "settings, llm, guardrails"
Repo > Agents: "repositories only"
```

---

## 3. Workflow

Every ticket follows one path. Rules decide policy cases. The model judges only the grey area.

```text
Understand → Classify → Investigate → Retrieve → Troubleshoot → Decide → Resolve → Act → Escalate → Remember
```

Node order in `agents/graph.py`:

```text
understand_ticket → classify_severity → customer_context → knowledge_retrieval
  → troubleshooting → resolution_planning → risk_check
      ├─ escalation_required → escalation
      ├─ approval pending → human_approval
      │     ├─ approved → execute_resolution
      │     └─ rejected → escalation
      └─ low risk → execute_resolution
  → ticket_summary → memory_update → END
```

`human_approval` calls `interrupt()`. Code before `interrupt()` re-runs on resume, so it stays small and idempotent. The checkpointer stores state under `thread_id`. Tests use `InMemorySaver` when `CHECKPOINT_DB_PATH=:memory:`. A file-backed run uses `AsyncSqliteSaver`.

A second `POST /run` while the ticket is `waiting_on_approval` returns 409. Resuming a run that is not paused returns 409.

Runs are bounded so none can loop: at most 12 graph steps, 2 investigation cycles and 2 clarifying
questions, and escalation below 0.6 confidence. A run that exhausts a budget escalates. Retrieved
chunks are scanned for instructions like ticket text, and a reply scoring below 0.8 groundedness is
revised once and then escalated (`CLAUDE.md` §7.2, §9).

Rejection of an approval routes to escalation. `create_escalation` does not need a second approval.

```eraser
direction right

Understand [icon: workflow, label: "understand_ticket"]
Classify [icon: workflow, label: "classify_severity"]
Customer [icon: users, label: "customer_context"]
Knowledge [icon: qdrant, label: "knowledge_retrieval"]
Trouble [icon: workflow, label: "troubleshooting"]
Plan [icon: workflow, label: "resolution_planning"]
Risk [icon: shield, color: orange, label: "risk_check"]
Escalate [icon: shield, color: red, label: "escalation"]
Approve [icon: lock, color: orange, label: "human_approval"]
Execute [icon: workflow, color: green, label: "execute_resolution"]
Summary [icon: workflow, label: "ticket_summary"]
Remember [icon: redis, label: "memory_update"]
Done [icon: workflow, color: green, label: "END"]

Understand > Classify > Customer > Knowledge > Trouble > Plan > Risk
Risk > Escalate: "policy or reject"
Risk > Approve: "needs approval"
Risk > Execute: "low risk"
Approve > Execute: "approved"
Approve > Escalate: "rejected"
Escalate > Summary
Execute > Summary
Summary > Remember > Done
```

```mermaid
flowchart LR
  Understand[understand_ticket] --> Classify[classify_severity]
  Classify --> Customer[customer_context]
  Customer --> Knowledge[knowledge_retrieval]
  Knowledge --> Trouble[troubleshooting]
  Trouble --> Plan[resolution_planning]
  Plan --> Risk{risk_check}
  Risk -->|policy or reject| Escalate[escalation]
  Risk -->|needs approval| Approve[human_approval]
  Risk -->|low risk| Execute[execute_resolution]
  Approve -->|approved| Execute
  Approve -->|rejected| Escalate
  Escalate --> Summary[ticket_summary]
  Execute --> Summary
  Summary --> Remember[memory_update]
  Remember --> Done[END]
```

![The support workflow: its steps and routes](diagrams/02-workflow.svg)

### 3.1 Run, pause, approve, reply

1. The console calls `POST /api/v1/tickets/{id}/run`.
2. `workflow_service.create_run()` writes `workflow_runs` and returns **202** `{workflow_id}`.
3. `BackgroundTasks` starts the graph. v1 runs the workflow in-process. A separate worker is a later extension.
4. After every node, state is saved. The console polls `GET /tickets/{id}/workflow` every 2 seconds.
5. `human_approval` interrupts. The service writes `approval_requests` and sets the ticket to `waiting_on_approval`.
6. `POST /approvals/{id}/approve` or reject calls `approval_service.decide()` and resumes with `Command(resume=…)`.
7. The tail is `execute_resolution`, then `ticket_summary`, then `memory_update`, then END.
8. Send reply is a separate call: `POST /tickets/{id}/reply`. The reply has already passed `validate_customer_output`.

Paste the next block into an Eraser **Sequence diagram**.

```eraser
Agent [icon: users, color: blue]
UI [icon: next, color: blue]
API [icon: fastapi, color: green]
RunSvc [icon: workflow, color: green]
Graph [icon: langgraph, color: orange]
DB [icon: postgres, color: blue]
Checkpoint [icon: sqlite, color: grey]

Agent > UI: Open ticket and run
UI > API: POST /tickets/id/run
activate API
API > RunSvc: create_run
RunSvc > DB: insert workflow_runs
API --> UI: 202 workflow_id
API > Graph: BackgroundTasks start_workflow
deactivate API

loop [label: every node, color: orange] {
  Graph > DB: save state
  Graph > DB: workflow_events
  UI > API: GET /workflow every 2s
}

Graph > Checkpoint: interrupt human_approval
Graph > DB: approval_requests and waiting_on_approval

Agent > UI: Approve or reject
UI > API: POST /approvals/id/approve or reject
API > Graph: Command resume
Graph > DB: execute_resolution then summary then memory
Agent > UI: Send reply
UI > API: POST /tickets/id/reply
API > DB: ticket message
```

```mermaid
sequenceDiagram
  actor Agent
  participant UI as Next.js
  participant API as FastAPI
  participant Svc as workflow_service
  participant Graph as LangGraph
  participant DB as PostgreSQL or SQLite

  Agent->>UI: Open ticket and run
  UI->>API: POST /tickets/{id}/run
  API->>Svc: create_run
  Svc->>DB: insert workflow_runs
  API-->>UI: 202 workflow_id
  API->>Graph: BackgroundTasks start
  loop every node
    Graph->>DB: save state and workflow_events
    UI->>API: GET /workflow every 2s
  end
  Graph->>DB: interrupt, approval_requests, waiting_on_approval
  Agent->>UI: Approve or reject
  UI->>API: POST /approvals/{id}/approve or reject
  API->>Graph: Command resume
  Graph->>DB: execute, summary, memory
  Agent->>UI: Send reply
  UI->>API: POST /tickets/{id}/reply
```

![Run, pause, approve and reply, step by step](diagrams/03-run-pause-approve-reply.svg)

---

## 4. Knowledge and memory

### 4.1 RAG

`sample_data/knowledge_base/*.md` holds 15 articles. Front matter is `title`, `category`, `tags`, `summary`.

Chunk on headings, then 900-character windows with 150-character overlap. Each chunk is prefixed with `"{title} - {heading}"`.

Retrieval is semantic union BM25, then reciprocal rank fusion with `k=60`, then a heuristic rerank, then an optional model rerank, then one hit per article. Modes are `hybrid` (default), `semantic`, and `keyword`.

Offline embeddings are a hashed bag-of-words, 384 dimensions. Changing the embedding model requires admin `POST /knowledge/reindex`, which recreates the collection.

Customer-facing policy claims cite these articles. Evidence carries `id`, `title`, `source` (`kb://slug#section`), `snippet`, `score`, `url` (`/knowledge/<id>`), and `article_id`.

The vector store is selected by `VECTOR_STORE`: `memory` or `qdrant`. Nothing outside `rag/` knows which one is live.

### 4.2 Memory

| Tier | Store | Holds | Lifetime |
|---|---|---|---|
| Short-term | Redis or fakeredis | Conversation per ticket, workflow state, retrieval cache | 24 hours. Cache entries last 300 seconds |
| Long-term | `customer_memory` | `preference`, `past_issue`, `troubleshooting`, `note` | Permanent, de-duplicated |

`customer_context` recalls up to 10 notes. `memory_update` writes the past issue, the first three troubleshooting steps, and a resolution note. Every note passes `scrub()`. Exact duplicates are skipped.

Never stored: card numbers, API keys, passwords, raw ticket bodies, or anything about another customer. Cache key shape is `rag:{mode}:{category}:{top_k}:{query}`.

---

## 5. Data model

Two forms on purpose. SQLAlchemy models in `backend/app/models/entities.py` use JavaScript Object Notation (JSON) columns and `String(36)` universally unique identifiers (UUIDs) so the same code runs on SQLite and Postgres. `database/schema.sql` is the Postgres data definition language (DDL). `schema.sql` is the authority for the table list: 17 tables, the 16 below plus `tenants`.

`profiles`, `customers`, `subscriptions`, `workspaces`, `products`, `tickets`, `ticket_messages`, `support_articles`, `incidents`, `workflow_runs`, `workflow_events`, `resolution_actions`, `approval_requests`, `escalations`, `customer_memory`, `audit_logs`.

The workflow itself is data: `workflow_runs.state` is the `WorkflowState` JSON, plus events, approvals, and resolution actions.

Categories, defined first in `backend/app/schemas/common.py`: `login_issue`, `billing`, `api_failure`, `workspace_permissions`, `storage_quota`, `integration`, `feature_request`, `account`, `security`, `other`.

Statuses: `new`, `in_progress`, `waiting_on_customer`, `waiting_on_approval`, `escalated`, `resolved`, `closed`.

Severity: `low`, `medium`, `high`, `critical`. Channels: `email`, `chat`, `web`, `api`.

```mermaid
erDiagram
  profiles ||--o{ audit_logs : "actor"
  customers ||--o{ subscriptions : has
  customers ||--o{ workspaces : owns
  customers ||--o{ tickets : opens
  customers ||--o{ customer_memory : remembers
  products ||--o{ subscriptions : prices
  tickets ||--o{ ticket_messages : contains
  tickets ||--o{ workflow_runs : runs
  tickets ||--o{ resolution_actions : plans
  tickets ||--o{ approval_requests : gates
  tickets ||--o{ escalations : routes
  workflow_runs ||--o{ workflow_events : records
  incidents ||--o{ tickets : "may affect"
  support_articles ||--o{ workflow_events : "cited as evidence"
```

![The data model: the main tables and how they relate](diagrams/04-data-model.svg)

Every data table also carries `tenant_id` (`String(36)`, not null, indexed, and first in every
composite index), and row-level security (RLS) is keyed on it: `USING (tenant_id = current_setting('app.tenant_id')::uuid)`,
with the API issuing `SET LOCAL app.tenant_id` per transaction. One tenant is seeded and v1 builds no
tenant features (decision D1, `CLAUDE.md` §6). Repositories are the only place the filter lives, so
on SQLite — which has no RLS — that filter is the boundary.

Most relationships above are foreign keys in `backend/app/models/entities.py` and `database/schema.sql`. Four are logical only, with no foreign key: `profiles` to `audit_logs` (the actor is a text field), `products` to `subscriptions`, `incidents` to `tickets`, and `support_articles` to `workflow_events` (evidence is stored inside the event). The backend
uses the service-role key on the server. The browser receives only the anon key.

---

## 6. Security boundaries

| Boundary | Rule |
|---|---|
| Browser | Anon key and the user JWT only. No service-role key |
| Ticket text | Untrusted data. `wrap_untrusted` and `SECURITY_PREAMBLE`. CD-1013 must not export records |
| Model | Adds judgement in grey areas. Escalation, severity floor, refunds, deletions, disputes, security, and data loss are code |
| Severity | Rules may raise the model score. They never lower it |
| Tenant | Every data table carries `tenant_id`; RLS in Postgres and the repository filter on SQLite. One enforcement point, never a per-query `WHERE` in a router or agent (D1) |
| Tools | Registry only. Refunds and setting resets require a recorded approval. Arguments need provenance: an id or amount comes from customer context or a tool result, never from ticket text. Every action carries an idempotency key and is read back |
| Customer reply | `validate_customer_output` blocks internal uniform resource locators (URLs), secrets, and another customer's data before the reply is shown |
| Memory | `scrub()` removes card numbers, API keys, and passwords |
| Logs and events | Decisions, tool results, evidence scores, timings, tokens, errors. No raw prompts, hidden chain-of-thought, other customers, or secrets |
| Deploy | Prod uses a reviewed plan and the prod var-file. `--auto-approve` is refused for staging and prod |

---

## 7. Local infrastructure

The Docker stack runs on real services and needs only your Euron key in `.env`. The offline test suite needs no key, no network and no containers.

| Setting | Docker stack | Offline tests |
|---|---|---|
| `DEMO_MODE` | `true` | `true` |
| `LLM_PROVIDER` | `euron` (from `.env`) | `fake` |
| `EMBEDDING_PROVIDER` | `euron`, `euri-embedding`, 1024 dimensions | `fake`, 384 dimensions |
| `VECTOR_STORE` | `qdrant` (local container, no key) | `memory` |
| `DATABASE_URL` | `postgresql+asyncpg://…@postgres:5432/clouddesk` | temporary SQLite file |
| Redis | real (`USE_FAKE_REDIS=false`) | fakeredis |
| `CHECKPOINT_DB_PATH` | `/app/data/checkpoints.db` (volume) | `:memory:` |
| Frontend | `:3000` | n/a |
| Backend | `:8000` (`BACKEND_PORT` moves it) | n/a |

Compose is `frontend → backend → postgres, redis, qdrant`, with `depends_on: service_healthy`, named volumes, and `restart: unless-stopped`. On start the backend creates its tables, seeds the demo data and fills Qdrant when it is empty.

Images: backend `python:3.12-slim`, non-root user `app`, `HEALTHCHECK` on `/health/live`, build context the repository root. Frontend `node:22-alpine`, `output: "standalone"`, non-root, `HEALTHCHECK` on `/api/health`.

```eraser
direction right

Dev [icon: monitor, color: blue, label: "Developer browser"]

Compose [icon: docker, color: blue, label: "Docker Compose"] {
  Web [icon: next, label: "frontend :3000"]
  Api [icon: fastapi, label: "backend :8000"]
  PgC [icon: postgres, label: "postgres"]
  RedisC [icon: redis, label: "redis"]
  QdrantC [icon: qdrant, label: "qdrant"]
  Vol [icon: docker, label: "named volumes"]
}

HostFiles [icon: sqlite, color: grey, label: "Checkpoint file: backend-data volume at /app/data"] {
  Checkpoint [icon: sqlite, label: "checkpoints.db"]
}

Dev > Web: "HTTPS localhost"
Web > Api: "REST"
Api > RedisC: "cache and rate limit"
Api > QdrantC: "knowledge vectors"
Api > PgC: "tickets, customers, approvals, audit"
Api > Checkpoint: "paused graphs"
PgC > Vol
RedisC > Vol
QdrantC > Vol
```

```mermaid
flowchart LR
  Dev[Developer browser] --> Web["frontend :3000"]
  Web --> Api["backend :8000"]
  Api --> PgC[postgres]
  Api --> RedisC[redis]
  Api --> QdrantC[qdrant]
  Api --> Checkpoint["checkpoints.db (backend-data volume)"]
  PgC --> Vol[named volumes]
  RedisC --> Vol
  QdrantC --> Vol
```

![The local Docker stack](diagrams/05-local-docker-stack.svg)

Offline tests skip Compose. They use SQLite, fakeredis, the in-memory vector store, the fake LLM, and an in-memory checkpointer. Row-level security is applied to a real Postgres in a separate check, but the API does not yet set `app.tenant_id`, so at runtime the repository filter is the boundary.

---

## 8. Cloud infrastructure

Terraform is one root per cloud, `deployment/aws`, `deployment/azure` and `deployment/gcp`, each with the same concerns in flat files: networking, container registry, secrets, compute, load balancing, monitoring and Redis (Terraform modules cannot be shared across providers, so what is shared is the per-environment var-files, the scripts and the workflows). Environments are var-files, `deployment/environments/{dev,staging,prod}.tfvars`, not copies of the code. Remote state uses a git-ignored `backend.hcl`. Secrets enter only as `TF_VAR_*`. The roots are validated with `make terraform-validate` and never applied. They do not yet provision the application database, a frontend service, Hypertext Transfer Protocol Secure (HTTPS) or Qdrant; AWS (Elastic Container Registry (ECR), Elastic Container Service (ECS) Fargate, Application Load Balancer (ALB)) is the first target.

These products stay outside every cloud account: **Supabase** (Postgres and JWT), **Qdrant Cloud**, and the **LLM API**.

v1 background work stays inside the backend process. A restart can drop an in-memory pause. File checkpoints survive only if that file is on a volume. A separate worker is not part of v1.

Image tags equal the git Secure Hash Algorithm (SHA). The image that was tested is the image that ships.

### 8.1 AWS

| Module | Service |
|---|---|
| Networking | Virtual private cloud (VPC) |
| Container registry | ECR |
| Compute | ECS Fargate, frontend and backend tasks |
| Load balancer | ALB |
| Secrets | Secrets Manager |
| Monitoring | CloudWatch |
| Redis | ElastiCache, from the shared redis module |
| External | Supabase, Qdrant Cloud, LLM API |

```eraser
direction down

Users [icon: users, color: blue, label: "Support agents"]
GH [icon: github-actions, color: grey, label: "GitHub Actions OIDC"]

AWS [icon: aws-vpc, color: orange, label: "AWS VPC"] {
  ALB [icon: aws-elastic-load-balancing, label: "ALB"]
  ECS [icon: aws-fargate, label: "ECS Fargate"] {
    WebTask [icon: next, label: "Frontend task"]
    ApiTask [icon: fastapi, label: "Backend task"]
  }
  Cache [icon: aws-elasticache, label: "ElastiCache Redis"]
  Secrets [icon: aws-secrets-manager, label: "Secrets Manager"]
  Logs [icon: aws-cloudwatch, label: "CloudWatch"]
  Registry [icon: aws-elastic-container-registry, label: "ECR"]
}

External [icon: supabase, color: purple, label: "Outside the account"] {
  Supa [icon: supabase, label: "Supabase Postgres and JWT"]
  QdrantCloud [icon: qdrant, label: "Qdrant Cloud"]
  LLMApi [icon: openai, label: "LLM API"]
}

Users > ALB: HTTPS
ALB > WebTask
ALB > ApiTask
WebTask > ApiTask: REST
GH > Registry: "push git SHA"
Registry > ECS: "pull image"
ApiTask > Secrets: "read TF_VAR secrets"
ApiTask > Cache
ApiTask > Supa
ApiTask > QdrantCloud
ApiTask > LLMApi
ApiTask --> Logs: "JSON logs"
```

```mermaid
flowchart TB
  Users[Support agents] --> ALB
  GH[GitHub Actions OIDC] -->|push git SHA| ECR
  ECR -->|pull image| ECS
  subgraph vpc [AWS VPC]
    ALB[ALB]
    subgraph ecs [ECS Fargate]
      WebTask[Frontend task]
      ApiTask[Backend task]
    end
    Cache[ElastiCache Redis]
    Secrets[Secrets Manager]
    Logs[CloudWatch]
  end
  ALB --> WebTask
  ALB --> ApiTask
  WebTask -->|REST| ApiTask
  ApiTask --> Cache
  ApiTask --> Secrets
  ApiTask --> Supa[Supabase]
  ApiTask --> QdrantCloud[Qdrant Cloud]
  ApiTask --> LLMApi[LLM API]
  ApiTask -.-> Logs
```

![The Amazon Web Services target](diagrams/06-aws-target.svg)

### 8.2 Azure

| Module | Service |
|---|---|
| Container registry | Azure Container Registry (ACR) |
| Compute | Container Apps, frontend and backend |
| Secrets | Key Vault |
| Monitoring | Log Analytics |
| Redis | Azure Cache for Redis |
| Load balancer | Load-balancer module in front of Container Apps ingress |
| External | Supabase, Qdrant Cloud, LLM API |

```eraser
direction down

Users [icon: users, color: blue, label: "Support agents"]
GH [icon: github-actions, color: grey, label: "GitHub Actions OIDC"]

Azure [icon: azure-container-apps-environments, color: blue, label: "Azure"] {
  Ingress [icon: shield, label: "Load balancer module"]
  Apps [icon: azure-container-apps-environments, label: "Container Apps"] {
    WebApp [icon: next, label: "Frontend app"]
    ApiApp [icon: fastapi, label: "Backend app"]
  }
  Cache [icon: azure-cache-redis, label: "Azure Cache for Redis"]
  Vault [icon: azure-key-vaults, label: "Key Vault"]
  Logs [icon: azure-log-analytics-workspaces, label: "Log Analytics"]
  Registry [icon: azure-container-registries, label: "ACR"]
}

External [icon: supabase, color: purple, label: "Outside the account"] {
  Supa [icon: supabase, label: "Supabase Postgres and JWT"]
  QdrantCloud [icon: qdrant, label: "Qdrant Cloud"]
  LLMApi [icon: openai, label: "LLM API"]
}

Users > Ingress: HTTPS
Ingress > WebApp
Ingress > ApiApp
WebApp > ApiApp: REST
GH > Registry: "push git SHA"
Registry > Apps: "pull image"
ApiApp > Vault
ApiApp > Cache
ApiApp > Supa
ApiApp > QdrantCloud
ApiApp > LLMApi
ApiApp --> Logs: "JSON logs"
```

### 8.3 GCP

| Module | Service |
|---|---|
| Networking | VPC |
| Container registry | Artifact Registry |
| Compute | Cloud Run, frontend and backend services |
| Load balancer | Cloud Load Balancing |
| Secrets | Secret Manager |
| Monitoring | Cloud Logging |
| Redis | Managed Redis from the shared redis module |
| External | Supabase, Qdrant Cloud, LLM API |

```eraser
direction down

Users [icon: users, color: blue, label: "Support agents"]
GH [icon: github-actions, color: grey, label: "GitHub Actions OIDC"]

GCP [icon: gcp-virtual-private-cloud, color: green, label: "GCP VPC"] {
  GLB [icon: gcp-cloud-load-balancing, label: "Cloud Load Balancing"]
  Run [icon: gcp-cloud-run, label: "Cloud Run"] {
    WebSvc [icon: next, label: "Frontend service"]
    ApiSvc [icon: fastapi, label: "Backend service"]
  }
  Cache [icon: redis, label: "Managed Redis"]
  Secrets [icon: gcp-secret-manager, label: "Secret Manager"]
  Logs [icon: gcp-cloud-logging, label: "Cloud Logging"]
  Registry [icon: gcp-artifact-registry, label: "Artifact Registry"]
}

External [icon: supabase, color: purple, label: "Outside the account"] {
  Supa [icon: supabase, label: "Supabase Postgres and JWT"]
  QdrantCloud [icon: qdrant, label: "Qdrant Cloud"]
  LLMApi [icon: openai, label: "LLM API"]
}

Users > GLB: HTTPS
GLB > WebSvc
GLB > ApiSvc
WebSvc > ApiSvc: REST
GH > Registry: "push git SHA"
Registry > Run: "pull image"
ApiSvc > Secrets
ApiSvc > Cache
ApiSvc > Supa
ApiSvc > QdrantCloud
ApiSvc > LLMApi
ApiSvc --> Logs: "JSON logs"
```

---

## 9. Delivery pipeline

GitHub Actions, when the workflows exist and the repository is pushed with OpenID Connect (OIDC) configured:

| Workflow | Does |
|---|---|
| `test.yml` | ruff, pytest, npm lint, test, and build |
| `security.yml` | gitleaks, pip-audit, Trivy, checkov |
| `docker-build.yml` | Image build |
| `terraform-validate.yml` | `terraform validate` |
| `_deploy.yml` | `bootstrap-registry` → `build-and-push` → `plan` → human approval → `apply` → `smoke` |

Prod apply uses the GitHub Environment `prod-apply` with required reviewers. Cloud auth is OIDC. There are no long-lived cloud keys.

Scripts under `deployment/scripts/` are `deploy`, `build_and_push`, `smoke_test`, `rollback`, and `destroy`. Each takes `<cloud> <env>`. The script itself refuses `--auto-approve` for staging and prod.

```eraser
direction right

Dev [icon: users, label: "Engineer"]
Git [icon: github, label: "GitHub"]

CI [icon: github-actions, color: grey, label: "Pull request"] {
  Test [icon: github-actions, label: "test.yml"]
  Sec [icon: shield, label: "security.yml"]
  Image [icon: docker, label: "docker-build.yml"]
  Tf [icon: terraform, label: "terraform-validate.yml"]
}

Release [icon: github-actions, color: orange, label: "Deploy"] {
  Boot [icon: docker, label: "bootstrap-registry"]
  Push [icon: docker, label: "build-and-push"]
  Plan [icon: terraform, label: "terraform plan"]
  Gate [icon: lock, color: red, label: "prod-apply reviewers"]
  Apply [icon: terraform, label: "terraform apply"]
  Smoke [icon: shield, label: "smoke"]
}

Cloud [icon: aws-fargate, label: "AWS or Azure or GCP"]

Dev > Git: "push SHA"
Git > Test
Git > Sec
Git > Image
Git > Tf
Image > Boot
Boot > Push > Plan > Gate > Apply > Smoke
Apply > Cloud: "same SHA that was tested"
```

Stage 17, the deployment agent in `../deployment-agent/`, is optional and is not required to finish the support platform. It may only call allow-listed scripts, never shell commands composed by a model. One session is one project, one cloud, and one environment.

---

## 10. Observability

JSON logs include `request_id` and `workflow_id` on every line.

`WorkflowTracer` writes `workflow_events` and never raises. Event names: `node_started`, `node_completed`, `tool_called`, `llm_called`, `approval_requested`, `approval_resolved`, `error`, `workflow_completed`.

Operators can see decisions, tool calls and results, evidence with scores, node timings, token counts, and errors. They cannot see raw prompts, hidden chain-of-thought, other customers' data, or secrets.

Token cost is an estimate. The fake provider records `0.0`. LangSmith is off unless `LANGCHAIN_TRACING_V2` and `LANGCHAIN_API_KEY` are set. The project name is `clouddesk-support`.

Business metrics are tracked and are not hard-coded: share of tickets resolved without a human edit, median time to first response, escalation precision, and refund approvals per week. Refunds are never zero-touch.

---

## 11. What is intentionally absent

- A customer-facing chat widget.
- Real email delivery and real refunds.
- Languages other than English.
- A separate workflow worker.
- A durable checkpoint service outside the backend task.
- The Stage 17 deployment agent, until stages 13–16 exist.
- Any claim that these diagrams have been applied to a live account.
