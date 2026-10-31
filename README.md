# CloudDesk

> An autonomous customer-support and resolution platform. A ticket arrives, a team of AI agents
> investigates it and proposes a resolution, and a human approves anything that costs money or
> touches an account.

**Status**: Specification and planning complete; implementation not started (0 of 14 phases) | **Version**: 0.1.0

---

## Overview

CloudDesk is a support-resolution platform for a fictional SaaS company (team collaboration, cloud
file storage, billing, workspaces, API access). It is used by **support agents**, not by customers
directly.

Every ticket goes through one pipeline:

```text
Understand -> Classify -> Investigate -> Retrieve -> Troubleshoot -> Decide -> Resolve -> Act -> Escalate -> Remember
```

The design rests on one rule: **policy is decided by rules, judgement is added by the model.**
Cases such as payment disputes, account deletion, security incidents, and data loss are escalated by
deterministic, tested rules and are never left to the model's probabilities. Anything involving a
refund or an account change waits for recorded human approval.

## Planned Architecture

| Layer | Choice |
|---|---|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind |
| Backend | FastAPI, Pydantic v2, async SQLAlchemy 2 |
| Orchestration | LangGraph workflow coordinating six specialist agents |
| Retrieval | Hybrid semantic + keyword search with reranking, cited evidence |
| Data | PostgreSQL (SQLite for the demo), Redis (fakeredis offline), Qdrant (in-memory offline) |
| Safety | Prompt-injection defence, output validation, role-based access, audit log |
| Delivery | Docker, Terraform for AWS / Azure / GCP, GitHub Actions |

The six agents are the Support Supervisor, Customer, Knowledge, Troubleshooting, Resolution, and
Escalation agents.

The whole stack is designed to run **offline** with a fake LLM provider, so tests and the demo
need no API key.

## Current State

Nothing user-facing exists yet. What is in the repository today:

- a reproducible Python 3.12 environment managed by [uv](https://docs.astral.sh/uv/)
- pinned dependencies and a locked `uv.lock`
- build, lint (Ruff), and test (pytest) configuration
- a `clouddesk` command-line entry point that currently prints a greeting

Not yet built: the API, database, knowledge pipeline, agents, workflow, approval flow, memory,
and console. No cloud resources have been created and nothing is deployed.

## Build Plan

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

Sub-tasks, branches, and dependencies are in `TASKS.md`; the requirements and each phase's exit
criteria are in `PLAN.md`; the full design is in `CLAUDE.md`.

## Getting Started

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.12 if missing.

```bash
uv sync                 # create .venv and install locked dependencies
uv run clouddesk        # run the CLI entry point
```

Activate the environment instead of prefixing commands with `uv run`:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Secrets belong in a local `.env` file, which is git-ignored. Never commit real keys.

## Development

```bash
uv run ruff check .     # lint
uv run pytest           # tests (none written yet)
```

## Author

Built by **Mahesh Kumar**, Founder & CEO of **SaffronyxAI.in**.
