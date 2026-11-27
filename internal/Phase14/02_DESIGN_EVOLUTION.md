# Phase 14: system design evolution

> **Status of this phase:** in progress. P14-2 (Dockerfiles) and P14-3 (Compose) are written and statically checked, and on 2026-11-27 the stack was built and brought up in Docker once (backend, frontend, redis and qdrant healthy; see `MEMORY.md`, First Docker bring-up). P14-1, P14-4 and P14-5 are not started. Nothing is deployed.

---

## P14-2: Backend and frontend Dockerfiles

- **Reordering.** Built ahead of the graph (P10-5) at the owner's request, because `backend/` and `frontend/` already run. The task's Needs line now reads `P1-1`, `P12-1`.
- **Backend.** `backend/Dockerfile`, built from the repo root. A builder stage installs locked dependencies with `uv sync --frozen --no-dev`; the runtime stage copies the venv, `backend/`, `rag/`, `agents/`, `memory/`, `integrations/`, `sample_data/` and `database/` (the last four packages were added as COPY lines when they landed). Runs as non-root `app`, `/app/data` writable, `PYTHONPATH=/app/backend:/app`, HEALTHCHECK uses Python urllib on `/health/live` (no curl).
- **Frontend.** `frontend/Dockerfile`: deps, builder, runner stages on `node:22-alpine`, copies `.next/standalone` and `.next/static`, non-root `app`, wget HEALTHCHECK on `/api/health`. `NEXT_PUBLIC_API_URL` is a build ARG (inlined at build time).
- **Context hygiene.** Root `.dockerignore` and `frontend/.dockerignore` exclude `.env*`, `data/`, `.git`, virtualenvs and `node_modules`.
- **Base images** are pinned by tag only, each with a "pin by digest before production" comment.
- **Verified:** `tests/deployment/test_dockerfiles.py` (static text checks), and on 2026-11-27 both images built and ran healthy inside the Compose stack. **Not verified:** image size, `docker build --check`. When the task merged the Docker daemon was not running, so the first build came later.

---

## P14-3: Compose stack

- **Services.** `docker-compose.yml` (project `clouddesk`): `frontend` (:3000) depends on `backend` (:8000), which depends on `redis` (`redis:7-alpine`) and `qdrant` (`qdrant/qdrant:v1.12.4`), all with `condition: service_healthy`. Every service has a healthcheck and `restart: unless-stopped`. Tags only; pin by digest before production.
- **Healthchecks.** Backend and frontend reuse the Dockerfile probes; redis uses `redis-cli ping`; qdrant has no curl, so it uses a bash `/dev/tcp` probe on 6333 (unverified against the image).
- **Volumes.** `backend-data` at `/app/data` (SQLite DB and checkpoints), `redis-data`, `qdrant-storage`.
- **Config.** Offline demo defaults: `LLM_PROVIDER=fake`, `VECTOR_STORE=memory` (Qdrant runs for later), real Redis (`USE_FAKE_REDIS=false`). `JWT_SECRET` comes from `${JWT_SECRET:-change-me-demo-only}`; `.env` is an optional `env_file`.
- **Frontend API URL.** The build arg `NEXT_PUBLIC_API_URL` is `http://localhost:${BACKEND_PORT:-8000}`, the host port (8000 by default), because the browser makes the calls, not the container.
- **Verified:** `docker compose config -q` and `tests/deployment/test_compose.py`, and the stack came up healthy on 2026-11-27 (on host port 18000 through an override, because 8000 was busy), including the qdrant `/dev/tcp` probe. **Not verified:** a browser view, Postgres, real Qdrant use.
