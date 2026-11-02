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

_Last updated: 2026-11-02 20:33 +0530_

## The files, and which one to trust

| File | Holds |
|---|---|
| `CLAUDE.md` | The spec: layers, agents, tools, rules. **Wins over every other file, including this one.** |
| `TASKS.md` | Every task: what to build, files, **Needs**, **Done when**, branch, and the order. |
| `PLAN.md` | Requirement IDs (F1-F14, N1-N8) and each phase's exit criteria and demo checkpoint. |
| `MEMORY.md` | The honest status, locked decisions, open questions, and working agreements. |
| `docs/05_ARCHITECTURE.md` | Component and infrastructure diagrams. |
| `docs/06_API_CONTRACT.md` | Every route and payload type. |
| `docs/07_GIT_WORKFLOW.md` | Branches, pull requests, promotion. |
| `docs/01_BRD.md`, `02_PRD.md`, `03_HLD.md`, `04_LLD.md` | The upstream design of **ACSRP**, the full product this repo is a v1 of. Read for intent. |

If a change would contradict `CLAUDE.md`, update `CLAUDE.md` first, then the plan, then the code.

### Do not “fix” CloudDesk to match the upstream documents

The documents in `docs/01`–`04` specify the full multi-tenant product. This repo is a deliberately
scoped single-tenant v1, and `CLAUDE.md` §1.1 tables every difference. CloudDesk's own vocabulary is
built and under test: severity is `low`/`medium`/`high`/`critical` (not `P1`–`P4`), statuses are
`waiting_on_*` (not `awaiting_*`), the channels are email/chat/web/api, and environment variables
carry no `ACSRP_` prefix. Renaming any of these to match a document breaks the schema, the API
contract and the tests at once. Change `CLAUDE.md` §5 or §10.1 first if it is genuinely wanted.

Of the six larger differences, **D1 (multi-tenancy) is settled**: every data table carries a not-null,
indexed `tenant_id`, the RLS policies are keyed on it from P2-1, one tenant is seeded, and no tenant
features are built. Repositories are the only place the filter lives, so SQLite's lack of RLS still
leaves one enforcement point. See `CLAUDE.md` §6.

**D2–D6 in `CLAUDE.md` §20 are still open**: a `prohibited` risk tier, write-capable MCP servers, model
tiering, Kubernetes, and the harder eval bar. Do not build any of them and do not assume one.

## Before coding

1. Find the task in `TASKS.md`. Check its **Needs** line: every predecessor must already be merged.
   Copy the branch name from its row. One task is one `feature/<name>` branch, opened against
   `development`. Never stack a branch on another feature branch.
2. If the user names work that has no row, add the row first, with its **Needs**, **Done when**, and a
   requirement ID. Do not build untracked work.
3. Read the task's **Build / Files / Done when**, the phase in `PLAN.md`, the matching section of
   `CLAUDE.md`, and `MEMORY.md` for decisions that already apply.
4. Name the requirement (F1-F14 or N1-N8) and the test that will prove it.
5. A route or payload change updates `docs/06_API_CONTRACT.md`, `backend/app/schemas/`, and
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
- **Every action is idempotent and verified.** It carries the key `ticket_id:tool:stable_hash(args)`;
  a key that already succeeded returns its stored result instead of acting again, and a write is
  read back afterwards. This is what stops a second refund on a retried or resumed run.
- **Tool arguments need provenance.** An id or an amount comes from customer context or an earlier
  tool result, never from ticket text. A failure rejects the argument and revises the plan.
- **Runs are bounded**: 12 graph steps, 2 investigation cycles, 2 clarifying questions, and escalate
  below 0.6 confidence. A run that exhausts a budget escalates; it never loops.
- **Retrieved chunks are untrusted too**: scan each one for instructions and drop it if it fails. A
  reply scoring below 0.8 groundedness is revised once, then escalated.
- A memory fact is kept only at confidence ≥ 0.7, and erasure removes rows and vectors together.
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
- Update `TASKS.md` in the same pull request as the task: set the row to `Completed ✅` and update
  the Progress summary (phase count and total). A task is not done until its PR includes this.
  Add a line to the Honest status in `MEMORY.md`, saying only what was actually run, and when a
  whole phase is finished also update the Build phases table in `PLAN.md`.

## Hard stops

- A customer reply containing internal URLs, secrets, or another customer's data.
- A refund, deletion, or setting reset running without a recorded approval.
- A `viewer` able to approve, reply, or run a workflow.
- Ticket text changing the workflow route.
- Memory notes containing card numbers, keys, passwords, or raw ticket bodies.
- Deploying production from the dev var-file, or applying an unreviewed plan.
- Writing "deployed", "passes in CI", or "validated" before it is true.
- Building any of decisions D2–D6, or renaming a status, severity, channel or environment variable to
  match an upstream document, without that decision being taken in `CLAUDE.md` first. (D1 is settled
  and P2-1 onward **does** build it.)
- Pushing to GitHub, or opening, closing, or merging a pull request, without the owner saying so.
  Commit locally by default. Never push directly to `development`, `testing`, or `main`.
