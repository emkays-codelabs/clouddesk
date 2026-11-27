---
paths:
  - "**/*.py"
---

# Python conventions

- Python 3.12. Ruff with line length 100 and rules `E F I UP B` (`[tool.ruff]` in `pyproject.toml`).
  Run `uv run python -m ruff check .` and `uv run python -m ruff format .`.
- Run everything through `uv run`, and call tools as `uv run python -m pytest` (the plain `uv run pytest`
  script trampoline fails on some Windows paths). Imports resolve from `backend` and the repository root through
  `pythonpath`, not from an installed package (`package = false`).
- Every agent returns a Pydantic model. No model call without `call_structured`; no tool call without
  `ToolRegistry`.
- Keep the layers apart (`CLAUDE.md` section 4.2): SQL only in repositories, `core/` never imports
  `agents/`, `rag/` never knows about tickets.
- New behaviour passes offline with `LLM_PROVIDER=fake`.
