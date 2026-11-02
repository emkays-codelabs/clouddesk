# Product Requirements Document (PRD)
## Autonomous Customer Support & Resolution Platform (ACSRP)

| Field | Value |
|---|---|
| Document type | PRD |
| Version | 1.0 (Draft) |
| Date | 31 October 2026 |
| Owner | Anu — OrionVexa (Agentic AI Production Engineering, Project 1) |
| Status | Draft for review |
| Related docs | `01a_BRD_Autonomous_Customer_Support_Platform.md`, `02_HLD_Autonomous_Customer_Support_Platform.md`, `03_LLD_Autonomous_Customer_Support_Platform.md` |

---

> **Split note.** This document is one half of the combined PRD/BRD v1.0. Its wording is
> unchanged, and the original section numbers are kept, so references such as “PRD §8”,
> “FR-01–42” and “NFR-01–16” stay valid. Sections §3, §4, §5, §6, §7, §8, §9, §12, §13 are here;
> the rest are in `01a_BRD_Autonomous_Customer_Support_Platform.md`. §13 Glossary appears in both.

---

## 3. Personas

| Persona | Description | Key needs |
|---|---|---|
| **Maya — Customer** | Uses chat or email to get help | Quick answers, no repetition of context, clear next steps |
| **Ravi — L1 Support Agent** | Handles queue, reviews AI drafts | Ticket summary, suggested plan, one-click approve/edit |
| **Elena — Support Supervisor** | Owns SLA and quality | Approval queue, escalations, dashboards, QA sampling |
| **Sam — Support Ops Admin** | Configures the platform | Knowledge sources, policies, tool permissions, routing rules |
| **Priya — Platform Engineer** | Runs it in production | Health, traces, cost, deploy pipeline, incident tooling |

---

## 4. User Journeys

### J1 — Autonomous resolution (low risk)
1. Maya writes in chat: "I was charged twice for my October subscription."
2. Supervisor Agent classifies: *Billing / Duplicate charge / Severity P3 / Sentiment negative*.
3. Customer Agent loads profile, plan, last invoices, open tickets and memory.
4. Troubleshooting Agent confirms two captured charges for the same invoice.
5. Knowledge Agent retrieves the refund policy and three similar resolved tickets.
6. Resolution Agent proposes: refund duplicate charge (US$29), within auto-approve limit per policy.
7. Policy engine marks action **low risk → auto-approved**; MCP `billing.refund` executes.
8. Customer receives confirmation; ticket resolved, summary written, memory updated.

### J2 — Human-in-the-loop approval
Same flow, but refund is US$480 (above auto limit). The graph **pauses**, creates an approval request. Elena approves from the dashboard; the graph resumes from checkpoint and executes.

### J3 — Escalation
Customer reports suspected account takeover. Severity P1, risk *critical*. Escalation Agent hands off immediately to the security queue with a structured case brief; AI takes no account actions and tells the customer a specialist is on it.

### J4 — Agent copilot
Ravi opens a complex ticket the AI could not resolve. He sees: summary, timeline, retrieved evidence with citations, hypotheses tested, recommended next step, and a draft reply.

### J5 — Learning loop
After a ticket is closed with positive feedback, its resolution is distilled into a "resolution card" and indexed so future similar tickets retrieve it.

---

## 5. Functional Requirements

Priority: **M** = Must, **S** = Should, **C** = Could.

### 5.1 Intake & Understanding
| ID | Requirement | Pri |
|---|---|---|
| FR-01 | Accept requests from chat widget, email webhook, REST API and ticketing connector, normalised into one `Ticket` model | M |
| FR-02 | Detect language, intent, product area, category/subcategory and entities (order ID, invoice ID, device, error code) | M |
| FR-03 | Classify severity (P1–P4) and sentiment; detect urgency signals (outage, security, legal, churn threat) | M |
| FR-04 | Deduplicate / thread messages into existing tickets | S |
| FR-05 | Ask clarifying questions when required information is missing (max 2 turns before handoff) | M |

### 5.2 Investigation & Retrieval
| ID | Requirement | Pri |
|---|---|---|
| FR-06 | Search product documentation with hybrid retrieval (dense + BM25) and reranking | M |
| FR-07 | Search previously resolved tickets and resolution cards | M |
| FR-08 | Retrieve customer profile, subscriptions, orders, invoices, device/service status via tools | M |
| FR-09 | Agentic RAG: query rewriting, multi-hop retrieval, self-check of retrieved evidence sufficiency | M |
| FR-10 | Every factual claim in a customer reply is grounded with a citation to a source chunk | M |
| FR-11 | Check system status / known incidents before troubleshooting | S |

### 5.3 Troubleshooting & Resolution
| ID | Requirement | Pri |
|---|---|---|
| FR-12 | Generate hypotheses, run diagnostic tools, and record findings | M |
| FR-13 | Produce a structured **Resolution Plan** (steps, actions, risk, expected outcome, confidence) | M |
| FR-14 | Draft customer reply in brand tone, customer's language | M |
| FR-15 | Execute actions only through registered MCP tools with schema-validated arguments | M |
| FR-16 | All actions are idempotent (idempotency key per ticket+action) | M |
| FR-17 | Verify action outcome and report back to customer | M |

### 5.4 Human-in-the-Loop & Escalation
| ID | Requirement | Pri |
|---|---|---|
| FR-18 | Policy engine assigns each action a risk tier: *low / medium / high / prohibited* | M |
| FR-19 | Low = auto-execute; medium = agent approval; high = supervisor approval; prohibited = never | M |
| FR-20 | Graph pauses on approval and resumes from a durable checkpoint | M |
| FR-21 | Approvers can approve, reject, or edit arguments; decisions are audited | M |
| FR-22 | Escalate when: confidence < threshold, P1, security/legal/fraud, repeated failure, explicit human request, negative sentiment spike | M |
| FR-23 | Escalation creates a case brief (summary, evidence, attempted steps, recommended owner) and routes to a queue | M |
| FR-24 | SLA timers and approval timeouts with auto-escalation | S |

### 5.5 Memory & Learning
| ID | Requirement | Pri |
|---|---|---|
| FR-25 | Short-term (conversation) memory per ticket thread | M |
| FR-26 | Long-term customer memory: preferences, environment, past issues, promises made | M |
| FR-27 | Customer can request memory deletion (right to erasure) | M |
| FR-28 | Generate ticket summary on resolve/escalate | M |
| FR-29 | Distil successful resolutions into resolution cards, indexed for retrieval after review | S |
| FR-30 | Capture CSAT and agent feedback, linked to traces for evaluation | M |

### 5.6 Dashboard (Web)
| ID | Requirement | Pri |
|---|---|---|
| FR-31 | Ticket inbox with filters (status, severity, channel, assignee, AI state) | M |
| FR-32 | Ticket detail: conversation, AI timeline, evidence with citations, plan, actions | M |
| FR-33 | Approval queue with diff view of proposed action arguments | M |
| FR-34 | Escalation queue | M |
| FR-35 | Analytics: volume, autonomous rate, FRT, MTTR, CSAT, cost, escalation reasons | M |
| FR-36 | Admin: knowledge sources, ingestion jobs, policies, tool registry, users and roles | M |
| FR-37 | Customer-facing chat widget (embeddable) | M |
| FR-38 | Real-time updates (WebSocket/SSE) | S |

### 5.7 Administration
| ID | Requirement | Pri |
|---|---|---|
| FR-39 | Upload/connect knowledge sources (PDF, Markdown, HTML, URL crawl); scheduled re-index | M |
| FR-40 | Versioned prompts and policies with rollback | S |
| FR-41 | Feature flags per tenant (autonomy level: copilot-only / supervised / autonomous) | M |
| FR-42 | Multi-tenancy (tenant isolation at data and vector index level) | S |

---

## 6. Non-Functional Requirements

| Category | ID | Requirement |
|---|---|---|
| Performance | NFR-01 | Chat first token P95 < 3 s; full resolution plan P95 < 20 s (excluding approval waits) |
| | NFR-02 | Retrieval (hybrid + rerank) P95 < 800 ms |
| Scalability | NFR-03 | 50 concurrent conversations per API replica; horizontal scaling to 1,000+ |
| | NFR-04 | 100k tickets/month per tenant; 1M+ indexed chunks |
| Availability | NFR-05 | 99.9% API availability; graceful degradation to "human handoff" mode if LLM provider fails |
| Reliability | NFR-06 | Durable graph checkpoints; no lost tickets; at-least-once background processing with idempotency |
| Security | NFR-07 | OIDC/JWT auth, RBAC, TLS 1.2+, encryption at rest, secrets in cloud secret manager |
| | NFR-08 | OWASP API Top 10 controls; prompt-injection defences on all untrusted content |
| Privacy | NFR-09 | PII detection and redaction in logs/traces; data residency per tenant; retention policies |
| Rate limiting | NFR-10 | Per-tenant, per-user and per-IP limits; LLM token budgets per tenant |
| Observability | NFR-11 | Structured logs, metrics, distributed traces (OpenTelemetry) and LLM traces (Langfuse/LangSmith) with ticket correlation ID |
| Evaluation | NFR-12 | Offline eval suite gates every release; online quality monitoring |
| Cost | NFR-13 | Per-ticket token and cost accounting; model routing (small model for classification) |
| Portability | NFR-14 | Same images on AWS/Azure/GCP; cloud-specific code isolated behind adapters |
| Maintainability | NFR-15 | ≥ 80% unit test coverage on core services; typed contracts (Pydantic/TypeScript) |
| Accessibility | NFR-16 | Dashboard and widget meet WCAG 2.1 AA |

---

## 7. AI Requirements

| Area | Requirement |
|---|---|
| Structured outputs | All agent outputs validated against Pydantic schemas; retry with repair on validation failure |
| Guardrails (input) | Prompt-injection detection, PII detection, toxicity, off-topic filter, jailbreak patterns |
| Guardrails (output) | Groundedness check, policy compliance (no promises outside policy), PII leakage, tone |
| Guardrails (action) | Tool allow-list per agent, argument validation, risk-tier policy, spend limits |
| Model routing | Small/fast model for classification and guardrails; strong model for planning; embedding + reranker models configurable |
| Determinism | Temperature ≤ 0.2 for decisions; seeds/versions recorded in traces |
| Explainability | Every decision stores rationale, evidence IDs and confidence |
| Fallbacks | Provider failover; retrieval-only answer; human handoff |

---

## 8. Success Metrics & Evaluation

| Metric | Definition | Target |
|---|---|---|
| Autonomous resolution rate | Resolved without human touch / total eligible | ≥ 40% |
| Escalation precision | Escalations judged necessary by humans | ≥ 85% |
| Escalation recall | High-risk tickets that were escalated | ≥ 98% |
| Classification accuracy | Category & severity vs labelled set | ≥ 90% / ≥ 92% |
| Retrieval quality | Recall@10 / nDCG@5 on golden queries | ≥ 0.90 / ≥ 0.75 |
| Faithfulness | Answer claims supported by context (RAGAS-style) | ≥ 0.92 |
| Tool-call correctness | Correct tool + valid args on eval set | ≥ 95% |
| Unsafe action rate | Actions violating policy | 0 |
| CSAT (AI-resolved) | Post-resolution survey | ≥ 4.3 / 5 |
| Reopen rate | Reopened within 7 days | < 8% |
| Cost per ticket | LLM + embedding + rerank cost | < US$0.08 |

---

## 9. Release Plan (aligned to the series)

| Phase | Deliverables |
|---|---|
| 0. Problem & PRD | This document, success metrics, synthetic dataset spec |
| 1. Architecture | HLD, LLD, ADRs |
| 2. Foundations | Repo, FastAPI skeleton, Postgres schema, Redis, auth, Next.js shell |
| 3. Knowledge | Ingestion pipeline, hybrid retrieval, reranking, eval set |
| 4. Agents | LangGraph supervisor + 5 agents, structured outputs, tools |
| 5. MCP & Actions | MCP servers (CRM, billing, orders, ticketing, status), policy engine, HITL |
| 6. Memory & Learning | Short/long-term memory, summaries, resolution cards |
| 7. Guardrails & Security | Input/output/action guardrails, RBAC, rate limiting |
| 8. Testing & Evaluation | Unit, integration, agent evals, red-team set, CI gates |
| 9. Containerisation & IaC | Docker, Compose, Terraform modules per cloud |
| 10. CI/CD | GitHub Actions: build, test, eval, scan, deploy |
| 11. Multi-cloud deploy | AWS, Azure, GCP environments |
| 12. Observability & Ops | Dashboards, alerts, runbooks, cost monitoring |

**Autonomy rollout per tenant:** Copilot-only → Supervised (all actions need approval) → Autonomous (policy-based).

---

## 12. Acceptance Criteria (v1.0)
1. All **Must** functional requirements implemented and demonstrated on the reference tenant.
2. Offline eval suite passes all targets in §8 on the golden dataset.
3. Red-team suite: 0 successful prompt-injection-to-action exploits.
4. Load test meets NFR-01/03 on one cloud; smoke tests pass on all three clouds.
5. Dashboards and alerts live; runbooks written for top 5 failure modes.
6. Same Git commit deployed to AWS, Azure and GCP via CI/CD.

---

## 13. Glossary
| Term | Meaning |
|---|---|
| Agentic RAG | Retrieval where an agent decides what/when/how to retrieve, rewrites queries and checks sufficiency |
| HITL | Human-in-the-loop approval of agent actions |
| MCP | Model Context Protocol — standard interface exposing tools/resources to agents |
| Resolution card | Distilled, reviewed record of how a past issue was resolved |
| Risk tier | Policy classification controlling whether an action needs approval |
| Checkpoint | Persisted LangGraph state allowing pause/resume |
