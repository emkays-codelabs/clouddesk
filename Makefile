.PHONY: setup backend test lint format seed ingest mcp demo terraform-validate smoke

# `uv run` uses .venv and the pytest `pythonpath` setting, so no PYTHONPATH juggling is needed.
# `demo` runs scripts/demo.py on the offline fake model; `make demo TICKET=CD-1005` picks another ticket.
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

demo:
	uv run python scripts/demo.py

# Offline check of the three Terraform roots: no cloud account, nothing is planned or applied.
terraform-validate:
	terraform -chdir=deployment/aws init -backend=false -input=false
	terraform -chdir=deployment/aws validate
	terraform -chdir=deployment/azure init -backend=false -input=false
	terraform -chdir=deployment/azure validate
	terraform -chdir=deployment/gcp init -backend=false -input=false
	terraform -chdir=deployment/gcp validate

# Needs a bash on PATH (Git Bash on Windows) and a running stack: BASE_URL=http://localhost:18000 make smoke
smoke:
	bash deployment/scripts/smoke_test.sh
