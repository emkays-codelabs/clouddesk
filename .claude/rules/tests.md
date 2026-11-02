---
paths:
  - "tests/**"
---

# Test conventions

- Tests run fully offline: no API key, no network. `tests/conftest.py` sets the environment before the
  app imports and blocks non-loopback sockets. Do not weaken it.
- `asyncio_mode = "auto"` with one session-scoped loop is set in `pyproject.toml`. Async tests need no
  marker; never add `@pytest.mark.asyncio` with a different scope.
- Write the test first and watch it fail for the right reason. A test must be able to fail: break the code
  once, confirm it goes red, then restore the original bytes.
- Every requirement in `PLAN.md` (F1-F14, N1-N8) maps to at least one test.
- Evaluation thresholds in `CLAUDE.md` section 13 fail the build. Do not lower one to make a run pass.
- Tests live in the folder that matches what they prove: `unit/`, `api/`, `rag/`, `agents/`, `workflow/`,
  `evaluation/`, `deployment/`.
