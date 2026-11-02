# Business Requirements Document (BRD)
## Autonomous Customer Support & Resolution Platform (ACSRP)

| Field | Value |
|---|---|
| Document type | BRD |
| Version | 1.0 (Draft) |
| Date | 31 October 2026 |
| Owner | Anu — OrionVexa (Agentic AI Production Engineering, Project 1) |
| Status | Draft for review |
| Related docs | `01b_PRD_Autonomous_Customer_Support_Platform.md`, `02_HLD_Autonomous_Customer_Support_Platform.md`, `03_LLD_Autonomous_Customer_Support_Platform.md` |

---

> **Split note.** This document is one half of the combined PRD/BRD v1.0. Its wording is
> unchanged, and the original section numbers are kept, so references such as “PRD §8”,
> “FR-01–42” and “NFR-01–16” stay valid. Sections §1, §2, §10, §11, §13 are here;
> the rest are in `01b_PRD_Autonomous_Customer_Support_Platform.md`. §13 Glossary appears in both.

---

## 1. Executive Summary

Businesses receive support requests through email, live chat, ticketing systems and in-app widgets. Most "AI support" products stop at **generating an answer**. They do not investigate, do not take action, do not know when to stop and hand off, and do not learn from what was resolved yesterday.

ACSRP is a multi-agent platform that behaves like a **production AI Customer Resolution Engineer**. For every request it can:

> **Understand → Investigate → Retrieve → Decide → Act → Escalate → Remember**

It classifies and prioritises the request, retrieves the right documentation and similar past tickets, pulls customer context, troubleshoots, builds a resolution plan, executes approved actions through governed tools (MCP), escalates high-risk cases to humans, and stores what it learned for the next customer.

The same application is deployed on **AWS, Azure and GCP** using Terraform, so learners see how one architecture maps to three clouds.

---

## 2. Business Context (BRD)

### 2.1 Problem Statement

| # | Problem | Business impact |
|---|---|---|
| P1 | High ticket volume, much of it repetitive (password resets, billing questions, order status, how-to) | Agent cost scales linearly with volume |
| P2 | Slow first response and resolution times | CSAT drop, churn, SLA penalties |
| P3 | Knowledge spread across docs, wikis, old tickets and agent heads | Inconsistent answers, long onboarding |
| P4 | Chatbots answer but cannot act (refund, reset, reship, update account) | Customers still wait for a human |
| P5 | No reliable judgement on when AI should stop | Risky automated actions or over-escalation |
| P6 | Resolved cases are not reused | The same investigation is repeated many times |
| P7 | No auditability of AI decisions | Compliance and trust blockers |

### 2.2 Business Objectives

| ID | Objective | Target (12 weeks post go-live, reference tenant) |
|---|---|---|
| BO-1 | Automate resolution of routine tickets end-to-end | ≥ 40% autonomous resolution rate (L1 categories) |
| BO-2 | Reduce first response time | P50 < 30 s, P95 < 2 min for chat/app channels |
| BO-3 | Reduce mean time to resolution (MTTR) | −35% vs baseline |
| BO-4 | Keep quality high | CSAT ≥ 4.3/5 on AI-resolved tickets; reopen rate < 8% |
| BO-5 | Zero unsafe autonomous actions | 0 high-risk actions executed without approval |
| BO-6 | Make human agents faster | Agent handle time −25% via summaries and draft plans |
| BO-7 | Control AI cost | Average LLM cost per ticket < US$0.08 |

### 2.3 Stakeholders

| Stakeholder | Interest |
|---|---|
| Customers / end users | Fast, correct, consistent resolution |
| Support agents (L1/L2) | Copilot, summaries, fewer repetitive tickets |
| Support supervisors / team leads | Queue health, SLA, approvals, quality |
| Support operations / admin | Configuration, policies, knowledge base, integrations |
| Engineering / SRE | Reliability, deployability, observability |
| Security & compliance | PII handling, audit trails, RBAC |
| Finance | AI and cloud cost per ticket |
| Learners (series audience) | A reference architecture they can rebuild and extend |

### 2.4 Scope

**In scope (v1.0)**
- Ingestion from web chat widget, email (inbound webhook), REST API (apps), and a ticketing-system connector (mock Zendesk/Jira-style adapter)
- Six-agent LangGraph system (Supervisor, Customer, Knowledge/RAG, Troubleshooting, Resolution, Escalation)
- Advanced + agentic RAG over product docs and resolved tickets (hybrid search + reranking)
- Action execution via MCP tool servers with human-in-the-loop approvals
- Customer memory (short-term + long-term)
- Support dashboard (Next.js) for agents, supervisors and admins
- Auth, RBAC, rate limiting, guardrails, logging, tracing, evaluation
- Docker, Terraform, CI/CD, deployment to AWS, Azure and GCP

**Out of scope (v1.0)**
- Voice/telephony channel (planned v2)
- Native integrations with every commercial helpdesk (one reference adapter only)
- Fine-tuning of foundation models
- Multi-language UI (agents may still answer in the customer's language)
- Real payment processing (refund tool hits a sandboxed billing service)

### 2.5 Assumptions & Constraints
- LLM access through a provider-agnostic gateway (OpenAI / Anthropic / Azure OpenAI / Vertex AI / Bedrock); model is configuration, not code.
- Reference tenant uses synthetic but realistic data (product docs, ~5–10k historical tickets, customer and order records).
- All sensitive actions run against sandboxed back-office systems.
- Each cloud deployment must use the same container images and the same application configuration contract.

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Hallucinated policies or promises | M | H | Grounding checks, citations, policy guardrail, low temperature |
| Prompt injection via email/attachments/docs | H | H | Content isolation, injection classifier, tool allow-lists, no tool args from untrusted text without validation |
| Wrong or duplicate action (e.g. double refund) | M | H | Risk tiers, HITL, idempotency keys, spend caps, post-action verification |
| PII leakage to logs/LLM | M | H | Redaction, data minimisation, provider data controls |
| LLM provider outage / latency | M | M | Gateway failover, timeouts, handoff mode |
| Cost runaway (loops) | M | M | Max graph steps, token budgets, loop detection |
| Knowledge staleness | M | M | Scheduled re-index, doc versioning, freshness metadata |
| Over-escalation reduces value | M | M | Threshold tuning with eval data, supervisor feedback |
| Multi-cloud drift | M | M | Single Terraform module interface, identical images, conformance tests |

---

## 11. Compliance & Governance
- Audit log for every AI decision, tool call, approval and data access (immutable, append-only).
- Data retention configurable per tenant (default: conversations 1 year, traces 30 days, audit 7 years).
- Right to access / erasure for customer memory.
- Model and prompt version recorded per decision.
- Alignment targets: GDPR/PIPEDA principles, SOC 2-style controls (reference implementation, not certification).

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
