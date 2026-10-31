.PHONY: setup backend test lint format

# `uv run` uses .venv and the pytest `pythonpath` setting, so no PYTHONPATH juggling is needed.
# Later tasks add: seed, ingest, demo, mcp, smoke, terraform-validate.

# Recipes only call `uv`, so they work in cmd.exe, PowerShell and sh alike (no `test`/`cp`/`&&`).
setup:
	uv sync
	@uv run python -c "import pathlib, shutil; p = pathlib.Path('.env'); p.exists() or shutil.copyfile('.env.example', p)"

backend:
	uv run uvicorn app.main:app --app-dir backend --reload --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .
