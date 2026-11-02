# CloudDesk

_Last updated: 2026-11-02 20:52 +0530_

> An autonomous customer-support and resolution platform. A ticket arrives, a team of AI agents
> investigates it and proposes a resolution, and a human approves anything that costs money or
> touches an account.

**Status**: In Development - phase 1 of 14 complete (runtime skeleton, validated locally) | **Version**: 0.1.0

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

Phase 1 (the runtime skeleton) is complete and validated locally. The service boots offline and answers health probes. What exists today:

- `GET /health`, `GET /health/live` (no dependency I/O) and `GET /health/ready` (configuration probes, `503` when degraded)
- an `X-Request-ID` on every response, including errors, echoed when safe and bound to every log line of the request
- cached settings for every variable in `.env.example`, with secrets and URL passwords redacted
- JSON logging with `request_id` and `workflow_id`
- an offline test suite (97 tests: no network, no API key), lint (Ruff), and a `Makefile`
- a Claude Code setup in `.claude/`: seven agents, seven skills, three rules, and a hook that runs lint and tests before Claude commits (see [Working with Claude Code](#working-with-claude-code); not yet exercised in a live session)
- the specification and plan: `CLAUDE.md`, `PLAN.md`, `TASKS.md`, `MEMORY.md` (status and decisions), and `docs/`

Not yet built: the database and demo data, authentication, the support API, the knowledge pipeline, tools, agents, the workflow, approvals, memory, and the console. No cloud resources have been created and nothing is deployed. Tests have not been run on GitHub Actions.

## Build Plan

| Phase | Name | Status |
|---|---|---|
| 1 | Runtime skeleton | validated locally |
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
criteria are in `PLAN.md`; the implementation spec is in `CLAUDE.md`.

The upstream design documents this is built from are in `docs/`: a BRD and PRD
(`01`, `02`), a high-level design (`03`) and a low-level design (`04`), written by the course
author. They specify the full multi-tenant product; this repo is a single-tenant v1 of the same
architecture, and `CLAUDE.md` §1.1 tables the differences.

## Getting Started

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.12 if missing.

```bash
make setup              # uv sync, and copy .env.example to .env if there is none
make backend            # FastAPI on http://localhost:8000 (reloads on edits)
curl http://localhost:8000/health/ready
```

`make` is not part of Windows; `winget install ezwinports.make` adds it. Without it, run the same steps through uv:

```bash
uv sync
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
```

Routes so far: `GET /health`, `GET /health/live`, `GET /health/ready`. The next phase starts at task `P2-1` in `TASKS.md`.

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
make test               # pytest, fully offline (or: uv run pytest)
make lint               # ruff (or: uv run ruff check .)
make format             # ruff format
```

### Working with Claude Code

The `.claude/` folder is committed, so a clone gets the same setup. Sonnet is the default model. Opus runs
only for planning and for one-off design questions, and Haiku handles search and log digests, which keeps
routine work cheap.

| Command | What it does |
|---|---|
| `/plan P2-1` | Writes a plan for a `TASKS.md` task to `docs/plans/` |
| `/implement docs/plans/p2-1.md` | Executes an approved plan, test first |
| `/test`, `/review` | Targeted tests with a digest; a ranked review of the diff |
| `/pr-review 10`, `/consult-opus`, `/cost-report` | Review a pull request; ask one design question; show cost and cache health |

A hook runs `ruff` and `pytest` before Claude runs `git commit` and blocks the commit if either fails. It
does not run when you commit by hand. Setup notes, the open checks, and proposed `CLAUDE.md` edits are in
[`docs/08_CLAUDE_SETUP.md`](docs/08_CLAUDE_SETUP.md). Prompt caching works: inside
one conversation it is complete, and only a new session's first request pays full price. The cache TTL is left at the default.

## Author

Built by **Mahesh Kumar**, Founder & CEO of **SaffronyxAI.in**.
