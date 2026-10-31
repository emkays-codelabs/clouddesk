# CloudDesk Support — Task tracker

> Concise checklist for GitHub-visible progress.
> Full plan and phase exit criteria: `PLAN.md` · Spec: `CLAUDE.md`

**Branch convention:** `feature/<name>` (one feature branch per sub-task; open the PR against `development`)
**Status:** `Pending ❌` · `Completed ✅`

Sub-tasks in the same phase that do not share files can be open at the same time. Do not stack a branch on another feature branch. Merge the listed predecessor first when a row names one.

`PLAN.md` holds each phase's exit criteria. This file is the execution order, arranged so a phase waits only on the contract it uses.

---

## Phase 1 — Runtime skeleton

> Depends on: nothing. Unblocks: every later phase.
> Merge order: P1-1 first. P1-2 and P1-4 in parallel after it. P1-3 after P1-2.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P1-1 · Settings and JSON logging | F14 | `feature/backend-config-logging` | Pending ❌ |
| P1-2 · Health routes and request-id middleware | N3 | `feature/backend-health-request-id` | Pending ❌ |
| P1-3 · Offline pytest harness | F14 | `feature/test-harness-offline` | Pending ❌ |
| P1-4 · Makefile and `.env.example` | F14 | `feature/makefile-env-example` | Pending ❌ |

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

---

## Phase 6 — Tools and mocks

> Depends on: P2-3. Parallel with: Phases 4, 5, 7, and 12.
> Merge order: P6-1 and P6-4 in parallel. P6-2 and P6-3 in parallel after both. P6-5 after P6-2.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P6-1 · Tool registry and policy | F9 | `feature/tool-registry-policy` | Pending ❌ |
| P6-2 · Read-only support tools | F4, F5, F7 | `feature/tools-read-only` | Pending ❌ |
| P6-3 · Approval-gated write tools | F9 | `feature/tools-approval-gated` | Pending ❌ |
| P6-4 · Mock integrations | — | `feature/integrations-mock` | Pending ❌ |
| P6-5 · MCP read-only server and `/mcp/tools` | — | `feature/mcp-server` | Pending ❌ |

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

---

## Phase 8 — Memory

> Depends on: P2-3, P3-3 (the Redis client), and P7-4. Parallel with: Phase 12. Does not wait for the graph.
> Merge order: P8-1 and P8-2 in parallel. P8-3 after both.

| Task | Covers | Branch | Status |
|------|--------|--------|--------|
| P8-1 · Short-term Redis facade | F11 | `feature/memory-short-term` | Pending ❌ |
| P8-2 · Long-term customer memory | F4, F11 | `feature/memory-long-term` | Pending ❌ |
| P8-3 · Recall and record service | F4, F11, N7 | `feature/memory-service` | Pending ❌ |

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
| 1 | Runtime skeleton | 4 | 0 |
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
| **Total** | | **67** | **0** |
