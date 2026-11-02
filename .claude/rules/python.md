---
paths:
  - "**/*.py"
---

# Python conventions

- Python 3.12. Ruff with line length 100 and rules `E F I UP B` (`[tool.ruff]` in `pyproject.toml`).
  Run `uv run ruff check .` and `uv run ruff format .`.
- Run everything through `uv run`. Imports resolve from `backend` and the repository root through
  `pythonpath`, not from an installed package (`package = false`).
- Every agent returns a Pydantic model. No model call without `call_structured`; no tool call without
  `ToolRegistry`.
- Keep the layers apart (`CLAUDE.md` section 4.2): SQL only in repositories, `core/` never imports
  `agents/`, `rag/` never knows about tickets.
- New behaviour passes offline with `LLM_PROVIDER=fake`.
