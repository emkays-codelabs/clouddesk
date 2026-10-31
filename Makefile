.PHONY: setup backend test lint format

# `uv run` uses .venv and the pytest `pythonpath` setting, so no PYTHONPATH juggling is needed.

setup:
	uv sync
	@test -f .env || cp .env.example .env

backend:
	uv run uvicorn app.main:app --app-dir backend --reload --port 8000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .
