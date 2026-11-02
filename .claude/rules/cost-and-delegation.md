# Cost and delegation

- Finish one task before starting another. Keep one session per topic and `/clear` between tasks.
- Pick the model at the top of a session. Each model has its own cache, so `/model` mid-task makes the next
  request uncached. Default is Sonnet. Opus runs only inside `planner` and `opus-consultant`.
- `CLAUDE.md`, rules and agent files load at session start. An edit applies after `/clear`, `/compact` or a
  restart, so make those edits between tasks. Do not connect or remove an MCP server, or deny a whole tool,
  mid-session: both rebuild the cache.
- Delegate instead of reading long output yourself:

  | Need | Use |
  |---|---|
  | Find where something lives | `Explore` (Haiku) |
  | Digest a long test or lint log | `log-triage` (Haiku) |
  | Plan a task | `/plan` |
  | Execute an approved plan | `/implement` |
  | Tests | `/test` |
  | Review a diff or a pull request | `/review`, `/pr-review` |
  | One narrow design question | `/consult-opus` |
  | Document a finished phase | `/phase-docs N` |

- Run agents in parallel only for independent file scopes: at most 3, one worktree each. Anything touching
  the same file, migration, lock file or schema runs in sequence. `TASKS.md`, `PLAN.md` and `MEMORY.md` are
  shared files, so edits to them are always sequential.
- Batch questions into one message.
- Commit locally only after review and green tests. Never push, and never open, close or merge a pull
  request, unless the owner says so.
