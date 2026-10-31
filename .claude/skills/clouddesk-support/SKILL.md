---
name: clouddesk-support
description: >-
  Implements the CloudDesk autonomous customer-support platform in this
  repository. Use when adding or changing tickets, agents, the LangGraph
  workflow, RAG, tools, memory, guardrails, the Next.js console, API routes,
  tests, or deployment, and when the user mentions CloudDesk, CLAUDE.md,
  TASKS.md, requirements F1-F14 or N1-N8, approvals, escalations, or DEMO_MODE.
---

# CloudDesk support platform

## The files, and which one to trust

| File | Holds |
|---|---|
| `CLAUDE.md` | The spec: layers, agents, tools, rules. **Wins over every other file, including this one.** |
| `TASKS.md` | Every task: what to build, files, **Needs**, **Done when**, branch, and the order. |
| `PLAN.md` | Requirement IDs (F1-F14, N1-N8) and each phase's exit criteria and demo checkpoint. |
| `MEMORY.md` | The honest status, locked decisions, open questions, and working agreements. |
| `docs/ARCHITECTURE.md` | Component and infrastructure diagrams. |
| `docs/API_CONTRACT.md` | Every route and payload type. |
| `docs/Git_GitHub_Workflow_Guide.md` | Branches, pull requests, promotion. |

If a change would contradict `CLAUDE.md`, update `CLAUDE.md` first, then the plan, then the code.

## Before coding

1. Find the task in `TASKS.md`. Check its **Needs** line: every predecessor must already be merged.
   Copy the branch name from its row. One task is one `feature/<name>` branch, opened against
   `development`. Never stack a branch on another feature branch.
2. If the user names work that has no row, add the row first, with its **Needs**, **Done when**, and a
   requirement ID. Do not build untracked work.
3. Read the task's **Build / Files / Done when**, the phase in `PLAN.md`, the matching section of
   `CLAUDE.md`, and `MEMORY.md` for decisions that already apply.
4. Name the requirement (F1-F14 or N1-N8) and the test that will prove it.
5. A route or payload change updates `docs/API_CONTRACT.md`, `backend/app/schemas/`, and
   `frontend/lib/types.ts` in the same change.
6. Stay inside one layer (`CLAUDE.md` section 4.2):
   - `backend/app/api/` handles HTTP, validation, auth, RBAC, and background tasks. No business rules.
   - `backend/app/services/` orchestrates repositories and the graph. It does not speak HTTP.
   - `backend/app/repositories/` owns all SQL. It never calls a model.
   - `backend/app/core/` owns config, security, logging, Redis, guardrails, and the database. It does
     not import `agents/` or `integrations/`.
   - `backend/app/tools/` exposes tools only through `ToolRegistry`.
   - `agents/` owns state, graph, nodes, specialists, rules, and prompts. It reads and writes data
     through repositories, never raw SQL.
   - `rag/` chunks and retrieves. It does not know about tickets.
   - `memory/` stores short-term and long-term notes and never stores secrets.
   - `frontend/` calls the backend only through `frontend/lib/api.ts`.

## Implementation rules

- **Test first.** Run the test and watch it fail for the right reason before writing the code.
- **Policy is code.** Escalation, the severity floor, refunds, deletions, disputes, security, and data
  loss are decided in `agents/rules.py` and `backend/app/tools/policy.py`. The model only judges grey
  areas, and only through `call_structured`. Severity rules may raise the model's severity, never lower it.
- Every agent returns a Pydantic model defined in `backend/app/schemas/workflow.py`. Prompts live in
  `agents/prompts.py` and share `SECURITY_PREAMBLE`. No free-text parsing.
- **Ticket text is data.** Text from a ticket, email, file, or web page goes through `wrap_untrusted`.
  Ticket `CD-1013` must remain data and must not export customer records.
- Tools are async `@tool` functions. All execution goes through `ToolRegistry.execute`. A failure becomes
  `ToolResult(ok=False)` and must not crash the graph. Planned actions come from
  `ResolutionAgent.plan_actions`, never from the model.
- A node returns a partial state dict. Reducers append `errors` and `completed_nodes` and sum
  `token_usage` with `merge_usage`; they never overwrite.
- Code that runs before `interrupt()` stays small and idempotent, because it re-runs on resume.
- Refunds, setting resets, deletions, and disputes need a recorded approval.
  `MAX_REFUND_WITHOUT_APPROVAL` defaults to `0`.
- `assess_risk()` returns `high` when the plan needs approval, a policy escalation fired, severity is
  critical, injection was detected, or output validation failed.
- Memory writes go through `scrub()`; skip exact-duplicate notes. Customer replies pass
  `validate_customer_output` before they can be shown or sent.
- New ticket categories are added in `backend/app/schemas/common.py` before they appear anywhere else.
- New behaviour passes offline with `DEMO_MODE=true`, `LLM_PROVIDER=fake`, `VECTOR_STORE=memory`, and
  `USE_FAKE_REDIS=true`.
- Migrations are additive files `database/migrations/000N_<name>.sql`. Update the SQLAlchemy model and
  `database/schema.sql` with them. Never edit an applied migration.

## Checkpoints

On Windows, prefer `uv run`. Otherwise use `.venv/Scripts/python.exe`, put `backend` on `PYTHONPATH`
with `;`, and set `PYTHONIOENCODING=utf-8`.

- `make test` and `make lint` after every task.
- `make demo` once the workflow exists. `TICKET=CD-1002` must pause for approval; `TICKET=CD-1005`
  must escalate by policy.
- A UI change is verified in the browser: run the ticket flow, confirm role-disabled actions, and
  confirm Approve and Reject appear only when `approval_status` is `pending`.

## Done when

- The task's **Done when** is true, the requirement maps to a test, and the offline suite passes.
- A `viewer` receives 403 on run, reply, and approve.
- The active phase's demo checkpoint still runs.
- The diff holds no `.env`, `data/`, `*.db`, `terraform.tfvars`, `backend.hcl`, `tfplan`, or secret.
- After the PR merges, and not before: set the `TASKS.md` row to `Completed ✅` and update the
  Progress summary. When a whole phase is finished, update the Build phases table in `PLAN.md` and
  the Honest status in `MEMORY.md`, saying only what was actually run.

## Hard stops

- A customer reply containing internal URLs, secrets, or another customer's data.
- A refund, deletion, or setting reset running without a recorded approval.
- A `viewer` able to approve, reply, or run a workflow.
- Ticket text changing the workflow route.
- Memory notes containing card numbers, keys, passwords, or raw ticket bodies.
- Deploying production from the dev var-file, or applying an unreviewed plan.
- Writing "deployed", "passes in CI", or "validated" before it is true.
- Pushing to GitHub, or opening, closing, or merging a pull request, without the owner saying so.
  Commit locally by default. Never push directly to `development`, `testing`, or `main`.
