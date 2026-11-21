# Phase 14: system design evolution

> **Status of this phase:** in progress. P14-2 (Dockerfiles) is written and statically checked; it has not been built. P14-1, P14-3, P14-4 and P14-5 are not started. Nothing is deployed.

---

## P14-2: Backend and frontend Dockerfiles

- **Reordering.** Built ahead of the graph (P10-5) at the owner's request, because `backend/` and `frontend/` already run. The task's Needs line now reads `P1-1`, `P12-1`.
- **Backend.** `backend/Dockerfile`, built from the repo root. A builder stage installs locked dependencies with `uv sync --frozen --no-dev`; the runtime stage copies only the venv, `backend/`, `rag/`, `sample_data/` and `database/` (the agents, memory and integrations packages do not exist yet and need COPY lines when they land). Runs as non-root `app`, `/app/data` writable, `PYTHONPATH=/app/backend:/app`, HEALTHCHECK uses Python urllib on `/health/live` (no curl).
- **Frontend.** `frontend/Dockerfile`: deps, builder, runner stages on `node:22-alpine`, copies `.next/standalone` and `.next/static`, non-root `app`, wget HEALTHCHECK on `/api/health`. `NEXT_PUBLIC_API_URL` is a build ARG (inlined at build time).
- **Context hygiene.** Root `.dockerignore` and `frontend/.dockerignore` exclude `.env*`, `data/`, `.git`, virtualenvs and `node_modules`.
- **Base images** are pinned by tag only, each with a "pin by digest before production" comment.
- **Verified:** `tests/deployment/test_dockerfiles.py` (static text checks). **Not verified:** `docker build`, image health, image size. The Docker daemon was not running; `docker build --check` also needs it.
