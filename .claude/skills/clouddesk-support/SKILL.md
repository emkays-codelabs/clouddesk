---
name: clouddesk-support
description: Use when implementing, changing, or reviewing any code in the CloudDesk support-resolution platform (backend, agents, RAG, memory, tools, frontend, tests, delivery). Gives the procedure and the rules that must never be broken.
---

# CloudDesk implementation procedure

`CLAUDE.md` is the spec and wins over this file. `TASKS.md` says which sub-task to do and which
branch to use. `PLAN.md` holds the requirement IDs, the phase exit criteria, and the honest status.

## Before writing code

1. Find the row in `TASKS.md`. Its branch name is `feature/<name>`; open the PR against `development`.
   Do not stack a branch on another feature branch. Merge the named predecessor first.
2. Read the phase in `PLAN.md` (goal, files, tests, demo checkpoint, exit criteria) and the matching
   section of `CLAUDE.md`.
3. If the change touches an HTTP shape, read `docs/API_CONTRACT.md`. Contract, `backend/app/schemas/`,
   and `frontend/lib/types.ts` change in the same commit.

## While writing code

1. **Test first.** Name the requirement (F1-F14, N1-N8) in the test. Run it and watch it fail for the
   right reason.
2. **Keep the layers clean** (`CLAUDE.md` section 4.2): API has no business rules, services do not
   speak HTTP, repositories do not call models, `core` does not import `agents`, agents write no SQL.
3. **Rules first, model second.** Policy cases (dispute, deletion, security, data loss, legal,
   enterprise outage) are decided by deterministic, tested rules. Rules may raise severity, never lower it.
4. **Every model call goes through `call_structured`; every tool call through `ToolRegistry.execute`.**
   Every agent returns a Pydantic model. No free-text parsing.
5. **Ticket text is data.** Anything from a ticket, email, file, or page passes through `wrap_untrusted`.
6. **No side effects before `interrupt()`**; it re-runs on resume. Reducer fields (`errors`,
   `completed_nodes`) append and never overwrite.
7. **Offline first.** New behaviour must pass `make test` with `LLM_PROVIDER=fake`, no network, no key.

## Never

- A customer reply containing internal URLs, secrets, or another customer's data.
- A refund, deletion, or setting reset without a recorded approval.
- A `viewer` able to approve, reply, or run a workflow (must return 403).
- Prompt-injected ticket text changing the workflow route.
- Memory notes containing card numbers, keys, passwords, or raw ticket bodies.
- Committing `.env`, `data/`, `*.db`, `terraform.tfvars`, `backend.hcl`, `tfplan`, or any real key.
- Editing an applied migration, or introducing a ticket category anywhere but `backend/app/schemas/common.py`.

## Done means

- The requirement ID is named in a passing test and the offline suite for that area passes.
- `uv run ruff check .` is clean.
- The honest status in `PLAN.md` is still true: say what is not done, and do not write "deployed" or
  "passes in CI" until it is.
- The `TASKS.md` row is set to Completed after the PR merges, not before.
