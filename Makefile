.PHONY: setup backend test lint format seed ingest mcp

# `uv run` uses .venv and the pytest `pythonpath` setting, so no PYTHONPATH juggling is needed.
# Not built yet, each added by the task named: demo (P11-5), terraform-validate (P14-4), smoke (P14-5).
# `seed` and `ingest` run the service modules directly and `mcp` starts the read-only MCP server over stdio.

# Recipes only call `uv`, so they work in cmd.exe, PowerShell and sh alike (no `test`/`cp`/`&&`).
# `.env` is created by hand (git-ignored; there is no committed template). The variables are listed in CLAUDE.md section 10.1.
setup:
	uv sync
	git config core.hooksPath .githooks

backend:
	uv run uvicorn app.main:app --app-dir backend --reload --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

seed: export PYTHONPATH = backend
seed:
	uv run python -m app.services.seed_service

ingest: export PYTHONPATH = backend
ingest:
	uv run python -m app.services.knowledge_service

mcp: export PYTHONPATH = backend
mcp:
	uv run python -m integrations.mcp.server
