# Phase 9: infrastructure design evolution

> **Status:** the Euron settings and the Docker pass-through are implemented and were exercised once against the real Euron API on 2026-11-27. No cloud resource exists.

## A. Overview

Phase 9 adds no service. It adds model configuration to the backend container and a second tier of environment variables.

## B. Initial design

The stack was `frontend`, `backend`, `redis` and `qdrant` from Phase 8, with `LLM_PROVIDER=fake` fixed in `docker-compose.yml`.

## C. Evolution

1. `LLM_BASE_URL` joined `Settings` for any OpenAI-compatible endpoint.
2. The Euron router added `LLM_MODEL_FAST`, `LLM_MODEL_SMART` and `LLM_MODEL_REASONING`; each falls back to `LLM_MODEL`.
3. The Euron embeddings provider added `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS` and `EMBEDDING_BASE_URL`.
4. `docker-compose.yml` passes these through to the backend, so the container can run on Euron while `pytest` stays on the fake provider.

## D. Docker

No Dockerfile change in this phase beyond the earlier COPY lines. The backend image already contains `agents/`, `rag/` and `memory/`.

## E. Networking

The backend calls the Euron HTTPS endpoint outbound. No inbound port was added.

## F. Wiring

`get_llm()` reads settings once (`get_settings()` is cached), so changing `.env` needs a container restart.

## G. Lifecycle commands

`BACKEND_PORT=18000 docker compose up --build -d backend` rebuilds with the new variables. `docker compose logs backend` shows each `llm call ok` line with provider, schema, tier and token count.

## H. Environment variables and secrets

The Euron key lives only in the git-ignored `.env`. It is never printed, logged or written to a document. `tests/unit/test_env_settings.py` keeps the variable list and `Settings` in step.

## I. Persistent storage

Unchanged: `backend-data` holds SQLite and checkpoints.

## J. Health checks and resilience

`/health/ready` reports the llm check. The router's circuit breaker stops a failing tier from being called on every request.

## K. Observability

Every model call logs provider, schema, attempts, tier, served tier, model and token totals as JSON. Cost for the fake provider is 0.0; real costs are estimates.

## L. Final infrastructure

Same four containers; the backend now has outbound access to Euron when configured.

## M. Verification

Run: `docker compose config -q`, the Euron calls during the bring-up (classification returned in about 30 seconds per call on the real model). Not run: a load test, a failover drill against a real outage.


---

## Model switch, 2026-11-27

The three tier variables (`LLM_MODEL_FAST`, `LLM_MODEL_SMART`, `LLM_MODEL_REASONING`) now name `openai/gpt-oss-120b-Turbo`, set in the git-ignored `.env`; `LLM_MODEL` stays the fallback. One real run took 71 seconds against 163 to 174 before. The model's price is in `backend/app/core/llm.py` so its cost is an estimate; the plan-hosted `euri-*` models publish no per-token price. Restarting every container kept all data: the same tickets, approvals, escalations, workflow runs and customers came back from the `backend-data` volume (checked 2026-11-27). Not checked: answer quality at scale, a restart during a running workflow.
