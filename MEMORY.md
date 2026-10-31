# MEMORY.md — CloudDesk

Durable facts for this repository: what is really done, what has been decided, and what is still open. `CLAUDE.md` wins if this file drifts. Update it in place when a decision or the status changes. Do not store secrets, customer payloads, or raw ticket bodies here.

---

## Working agreements

- Planning files: `CLAUDE.md` (spec, wins any disagreement), `PLAN.md` (requirements and phase exit criteria), `TASKS.md` (tasks and order), and this file (status and decisions).
- One phase numbering: the 14 phases in `TASKS.md`. `PLAN_PHASE.md` was merged into `PLAN.md` and removed on 2026-10-31.
- The project runs as a service with uvicorn (`[tool.uv] package = false`); there is no installable package and no CLI entry point.
- Git flow: `feature/<name>` → `development` → `testing` → `main`, by pull request, with no direct pushes (`docs/Git_GitHub_Workflow_Guide.md`).
- Nothing is pushed to GitHub, and no pull request is opened or closed, until the owner says so (2026-10-31).
- Updating `TASKS.md` is part of finishing every task (owner's rule, 2026-10-31): the task's pull request sets its row to Completed ✅ and updates the Progress summary, and adds a line to the Honest status below.

## Honest status

Update each row in place. Do not mark a row done from intention.

| Surface | State on 2026-10-31 |
|---|---|
| Repository contents | Specification and planning documents (`CLAUDE.md`, `PLAN.md`, `TASKS.md`, `MEMORY.md`, `README.md`, `docs/`), the `clouddesk-support` skill in `.claude/`, and `pyproject.toml` with `uv.lock`. The `uv init` stubs (`main.py`, `src/clouddesk/`) were removed. Application code so far is P1-1 only (`backend/app/core/config.py` and `logging.py`) with its tests. |
| Implemented | P1-1 (cached settings and JSON logging). The code is on `development` (pushed directly, without a pull request); its extra tests are in open pull request #3. Nothing else. A Phase 1 attempt (commits `ffa6a46` and `4066c11` on `feature/phase-1-runtime-skeleton`) was rolled back on 2026-10-31 to restart from scratch. |
| Validated locally | P1-1 only: 29 tests pass offline and `ruff check` is clean on this machine. Not run on GitHub Actions. |
| Cloud credentials | None used. |
| Applied to a real account | Nothing. |
| GitHub Actions | Workflow files are not in the repo. None have been executed. |
| Phase plan | Phase 1 is in progress: P1-1 is complete (1 of 67 tasks). Phases 2–14 are not started. |
| GitHub | `main`, `development`, and `testing` exist. `development` holds the planning documents and the P1-1 code. The branches `docs/consolidate-planning`, `feature/backend-config-logging` and `feature/phase-1-runtime-skeleton` (rolled back) are also pushed. Pull requests #1 and #2 are closed; #3 is open. |

## Locked decisions

Carried over from the earlier attempt. They are design decisions, not claims about code.

- 2026-10-25, F14 and observability: process settings come from a cached `get_settings()` in `backend/app/core/config.py`. JSON logs come from `setup_logging()` and `log_context()` in `backend/app/core/logging.py`, and every line carries `request_id` and `workflow_id` (`null` when unset). `model_dump()` redacts secrets and URL passwords; connection code reads the attributes.
- 2026-10-25, N3: `RequestIdMiddleware` echoes a safe `X-Request-ID` or assigns a UUID, binds `log_context`, and sets the header on application responses, including 404 and 500. CORS sits outside it and exposes the header. `/health` and `/health/live` do no dependency I/O. `/health/ready` returns 200 `ready` or 503 `degraded` from configuration checks until the database, Redis, vector store, and LLM clients exist, and its details never include a URL, password, or API key.

## Open questions

- `CLAUDE.md` §15 says environments are committed var-files (`environments/{dev,staging,prod}/terraform.tfvars`) while §18 says never to commit `terraform.tfvars`. Decide which holds before Phase 14.
- The course paths `../docs/`, `../deployment-agent/`, and `../shared-infrastructure/` sit outside this repo and are not copied in.
- Table counts disagree across the course notes (16 in the database doc, 15 data tables in the RLS note). `database/schema.sql` becomes the authority once it is written.
- Stage documents 00–17 are not in this repo. This plan is derived from `CLAUDE.md`, not from those missing files.

## Update protocol

- Record a new locked decision with the date and the requirement id it serves.
- With every task, in the same pull request: set its `TASKS.md` row to Completed ✅, update the Progress summary, and add one line under Honest status.
- When a phase exits, also set its status in the Build phases table in `PLAN.md`.
- When a demo ticket’s expected behaviour changes, change `CLAUDE.md` §5 and the matching test together.
- Leave secrets, tokens, connection strings, and ticket bodies out of this file.
