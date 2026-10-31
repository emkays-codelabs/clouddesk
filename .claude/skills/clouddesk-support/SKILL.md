---
name: clouddesk-support
description: Use when implementing, changing, or reviewing any code in the CloudDesk support-resolution platform (backend, agents, RAG, memory, tools, frontend, tests, delivery). Gives the procedure and the rules that must never be broken.
---

# CloudDesk implementation procedure

## The files, and which one to trust

| File | Holds |
|---|---|
| `CLAUDE.md` | The spec: layers, agents, tools, rules. **Wins over every other file, including this one.** |
| `TASKS.md` | The 67 tasks: what to build, files, **Needs**, **Done when**, branch, and the order. |
| `PLAN.md` | Requirement IDs (F1-F14, N1-N8) and each phase's exit criteria and demo checkpoint. |
| `MEMORY.md` | The honest status, locked decisions, open questions, and working agreements. |
| `docs/` | `API_CONTRACT.md` (routes and shapes), `ARCHITECTURE.md`, `Git_GitHub_Workflow_Guide.md`. |

## Before writing code

1. Find the task in `TASKS.md`. Check its **Needs** line: every predecessor must already be merged.
   Its branch is `feature/<name>`; the PR goes against `development`. Never stack a branch on
   another feature branch.
2. Read the task's **Build / Files / Done when**, the phase in `PLAN.md`, and the matching section of
   `CLAUDE.md`. Read `MEMORY.md` for decisions that already apply.
3. If the change touches an HTTP shape, read `docs/API_CONTRACT.md`. Contract, `backend/app/schemas/`,
   and `frontend/lib/types.ts` change in the same commit.
4. Do not start a task that is not in `TASKS.md`. If the work needs one, add the row first, with its
   **Needs** and **Done when**, and trace it to a requirement ID.

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
- Pushing to GitHub, or opening, closing, or merging a pull request, without the owner saying so.
  Commit locally by default. Never push directly to `development`, `testing`, or `main`.
- Writing "deployed", "passes in CI", or "validated" in any file before it is true.

## Done means

- The task's **Done when** is true, and the requirement ID is named in a passing test.
- `uv run ruff check .` is clean and the offline suite for that area passes.
- The diff holds no `.env`, database, or secret.
- Then, and only after the PR merges: set the `TASKS.md` row to Completed and update the Progress
  summary. When a whole phase is finished, update the Build phases table in `PLAN.md` and the Honest
  status in `MEMORY.md`, saying only what was actually run.
