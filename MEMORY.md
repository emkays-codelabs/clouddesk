# MEMORY.md — CloudDesk

_Last updated: 2026-11-02 20:52 +0530_

Durable facts for this repository: what is really done, what has been decided, and what is still open. `CLAUDE.md` wins if this file drifts. Update it in place when a decision or the status changes. Do not store secrets, customer payloads, or raw ticket bodies here.

---

## Working agreements

- Planning files: `CLAUDE.md` (spec, wins any disagreement), `PLAN.md` (requirements and phase exit criteria), `TASKS.md` (tasks and order), and this file (status and decisions).
- One phase numbering: the 14 phases in `TASKS.md`. `PLAN_PHASE.md` was merged into `PLAN.md` and removed on 2026-10-31.
- The project runs as a service with uvicorn (`[tool.uv] package = false`); there is no installable package and no CLI entry point.
- Git flow: `feature/<name>` → `development` → `testing` → `main`, by pull request, with no direct pushes (`docs/07_GIT_WORKFLOW.md`).
- Nothing is pushed to GitHub, and no pull request is opened or closed, until the owner says so (2026-10-31).
- Updating `TASKS.md` is part of finishing every task (owner's rule, 2026-10-31): the task's pull request sets its row to Completed ✅ and updates the Progress summary, and adds a line to the Honest status below.

## Honest status

Update each row in place. Do not mark a row done from intention.

| Surface | State on 2026-10-31 |
|---|---|
| Repository contents | Specification and planning documents (`CLAUDE.md`, `PLAN.md`, `TASKS.md`, `MEMORY.md`, `README.md`, `docs/`), the `clouddesk-support` skill and shared permissions in `.claude/`, plus the cost-governance setup there (7 agents, 7 skills, 3 rules, a pre-commit hook and pinned model ids), and `pyproject.toml` with `uv.lock`. Application code so far is Phase 1: `backend/app/` (settings, JSON logging, health routes, request-id middleware, readiness checks, the app factory) with its tests under `tests/`, plus `Makefile`, `.env.example` and `.gitattributes`. The `uv init` stubs were removed. |
| Implemented | Phase 1 (runtime skeleton), all four tasks, is on `development` (PRs #3 to #7): P1-1 settings and JSON logging, P1-3 offline test harness, P1-2 health routes and request-id middleware, P1-4 Makefile and `.env.example`. Nothing from Phase 2 onward. A first Phase 1 attempt (commits `6b5a53f`, `ffa6a46`, `4066c11`) was rolled back on 2026-10-31; its branch was deleted and the commits remain reachable through the ref of closed PR #1 (`refs/pull/1/head`). |
| Validated locally | Phase 1: 97 tests pass offline and `ruff check` is clean, re-run through `make lint` and `make test` on the merged `development`. Deliberate breaks of the code under test are each caught (P1-1: 6, P1-3: 10, P1-2: 12). With GNU Make 4.4.1 on Windows PowerShell, `make lint`, `make test` and `make setup` (run twice) exit 0, and `make backend` served `/health/live` and `/health/ready` with HTTP 200 and an `X-Request-ID`. `uvicorn` was also probed with `curl`: echoed and replaced ids, 404, CORS, and JSON access logs carrying the id. Not run on GitHub Actions. |
| Cloud credentials | None used. |
| Applied to a real account | Nothing. |
| GitHub Actions | Workflow files are not in the repo. None have been executed. |
| Phase plan | Phase 1 (runtime skeleton) is complete and validated locally: all four tasks are merged (4 of 67). Phases 2–14 are not started. |
| Claude Code setup | Written 2026-11-02 from the cost-governance prompt, with every key checked against the official docs. Validated: `settings.json` parses and no existing permission was dropped; `bash -n` passes on the hook. Prompt caching was measured on 2026-11-02 with two headless sessions: the second read 14,619 tokens from the cache, but it rewrote 31,204 of about 45,800, so roughly a third of the starting context is reused between sessions, and a fresh session starts at about 45,800 tokens. A follow-up of about 40 calls found the cause is user-level, not this repository: any one of the output style or a plugin cuts cross-session reuse to 51–69%, while inside one conversation reuse is 100% and later turns cost about a tenth of the first. **Not verified:** the mechanism, that the hook fires in a live session, `omitClaudeMd` (needs Claude Code 2.1.271 or later; the CLI on this PATH is 2.1.104), and that skills named `plan`, `review` and `test` do not collide with built-in commands. The cache TTL is left at the default. |
| Docs folder | `docs/` uses numbered short names: `01_BRD`, `02_PRD`, `03_HLD`, `04_LLD` (the upstream design, in dependency order), then `05_ARCHITECTURE`, `06_API_CONTRACT`, `07_GIT_WORKFLOW`, `08_CLAUDE_SETUP`. `09_PROMPT_COST` is a local prompt note that is not tracked. References were updated by path only, and `tests/unit/test_docs_folder.py` fails on any old name. The HLD and LLD still name the author's original files inside their own text, by design. |
| GitHub | `main`, `development` and `testing` exist, and there are no other branches. `development` holds the planning documents and all of Phase 1. Pull requests #3 to #7 are merged; #1 and #2 are closed. |

## Locked decisions

Carried over from the earlier attempt. They are design decisions, not claims about code.

- 2026-10-25, F14 and observability: process settings come from a cached `get_settings()` in `backend/app/core/config.py`. JSON logs come from `setup_logging()` and `log_context()` in `backend/app/core/logging.py`, and every line carries `request_id` and `workflow_id` (`null` when unset). `model_dump()` redacts secrets and URL passwords; connection code reads the attributes.
- 2026-10-25, N3: `RequestIdMiddleware` echoes a safe `X-Request-ID` or assigns a UUID, binds `log_context`, and sets the header on application responses, including 404 and 500. CORS sits outside it and exposes the header. `/health` and `/health/live` do no dependency I/O. `/health/ready` returns 200 `ready` or 503 `degraded` from configuration checks until the database, Redis, vector store, and LLM clients exist, and its details never include a URL, password, or API key.

- 2026-11-02, D1 (multi-tenancy, upstream NFR-07 and LLD §3.2): every data table carries `tenant_id`
  (`String(36)`, not null, indexed, first in every composite index) and the RLS policies are keyed on
  it from P2-1. One `tenants` row is seeded; v1 creates no second tenant and builds no tenant
  features (no CRUD, routing, per-tenant budgets or console switching). Reasons: `CLAUDE.md` §6
  already promised RLS on all data tables with no column to key it on, so the spec contradicted
  itself; the column costs one field and one index now but a 16-table migration later; and
  repositories own the filter, so SQLite's lack of RLS still leaves one enforcement point. Settled by
  Claude on the owner's instruction, not by a separate review — overrule it here if that is wrong.
- 2026-11-02, scope: the upstream documents (`docs/01`–`03`) describe ACSRP, the full multi-tenant product; this repo builds CloudDesk, a single-tenant v1 of the same architecture. The differences are tabled in `CLAUDE.md` §1.1. CloudDesk's own vocabulary (severity `low`/`medium`/`high`/`critical`, `waiting_on_*` statuses, the `web` channel, unprefixed environment variables) is built and under test, and is not renamed to match upstream without changing `CLAUDE.md` §5 or §10.1, the model, the schema and the tests together.
- 2026-11-02, Claude Code cost governance: the default session model is Sonnet. Opus runs only in `planner` and `opus-consultant`; Haiku runs `Explore` and `log-triage`. At most 3 agents run in parallel, one worktree each, and never on the same file. Model ids are pinned in `.claude/settings.json` for the first-party API (`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`). `CLAUDE.md` is a protected file in this setup: proposed edits go to `docs/08_CLAUDE_SETUP.md`. The source prompt departs from the official docs in several places, listed in that file, and the docs won.

## Open questions

- `CLAUDE.md` §15 says environments are committed var-files (`environments/{dev,staging,prod}/terraform.tfvars`) while §18 says never to commit `terraform.tfvars`. Decide which holds before Phase 14.
- The upstream PRD, HLD and LLD are in `docs/` (`CLAUDE.md` §1.1, copied in 2026-11-02). The remaining course documents and the `../deployment-agent/` and `../shared-infrastructure/` paths are still outside this repo.
- Table counts disagree across the course notes (16 in the database doc, 15 data tables in the RLS note). `database/schema.sql` becomes the authority once it is written.
- Course documents 00 and 04–17 are not in this repo.
- D1 (multi-tenancy) is settled; see Locked decisions above and `CLAUDE.md` §6. **D2–D6 in `CLAUDE.md` §20 are still open**: a `prohibited` risk tier, write-capable MCP servers, model tiering, Kubernetes, and the harder eval bar. None blocks Phase 2.
- Cross-session cache reuse is partial because of user-level settings (the output style and plugins), not this repository; inside one conversation it is complete. Decide whether to disable plugins this project does not need (section "Caching" in `docs/08_CLAUDE_SETUP.md` has the measured sizes). The TTL is left at the default; every write observed was a one-hour write, which is the subscription default.

## Update protocol

- Record a new locked decision with the date and the requirement id it serves.
- With every task, in the same pull request: set its `TASKS.md` row to Completed ✅, update the Progress summary, and add one line under Honest status.
- When a phase exits, also set its status in the Build phases table in `PLAN.md`.
- When a demo ticket’s expected behaviour changes, change `CLAUDE.md` §5 and the matching test together.
- Leave secrets, tokens, connection strings, and ticket bodies out of this file.
