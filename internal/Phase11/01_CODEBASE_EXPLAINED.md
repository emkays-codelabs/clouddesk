# Phase 11 explained: approval and escalation

> **Status:** implemented and tested offline. Approval timeouts (FR-24) are NOT built. Nothing is deployed.

## A. Executive summary

Phase 11 makes the workflow safe to run on money. A plan with a refund or a setting reset pauses for a person; approving runs the action exactly once; rejecting escalates. Policy cases hand off to a named team. `scripts/demo.py` shows the refund path in a terminal.

## B. Business problem and solution

Support teams cannot let software move money unattended. The platform proposes, a human decides, and every decision is recorded. Sensitive cases (disputes, deletion, security, data loss, enterprise outage) never wait for model judgement.

## C. Architecture in simple language

The graph's `human_approval` node calls `interrupt()`. The service layer then creates an `approval_requests` row and sets the ticket to `waiting_on_approval`. An agent approves or rejects through the application programming interface (API); the service resumes the same run. Escalations are rows in `escalations`, created by the escalation node through the `create_escalation` tool.

## D. File-by-file

| File | Purpose |
|---|---|
| `agents/nodes/human_approval.py` | The pause. |
| `agents/nodes/escalation.py` | Escalation and the post-rejection path. |
| `agents/specialists/escalation.py` | `decide`, `record`, `run`: rules first, model for grey areas. |
| `backend/app/services/approval_service.py` | Creates, decides and resumes approvals. |
| `backend/app/api/approvals.py` | List, approve and reject approvals, and list and update escalations (`/escalations`). Agent role required for every write. |
| `backend/app/schemas/approval.py` | Approval and escalation schemas. |
| `backend/app/tools/policy.py` | Which tools need approval. |
| `backend/app/tools/idempotency.py` | One refund per key, even after a retry or resume. |
| `scripts/demo.py` | `make demo`: the CD-1002 refund end to end on the fake model. |
| `tests/workflow/test_demo_script.py` | The demo's behaviour. |

## E. Execution flow

Run the refund ticket; the plan contains `create_refund_request`; risk is high; the run pauses. `GET /approvals?status=pending` lists it; `POST /approvals/{id}/approve` resumes; the action runs through `ToolRegistry.execute(..., approved=True)` and its result is read back; the ticket resolves.

## F. Concepts

Approval is a property of the tool, not of the run. The idempotency key `ticket_id:tool:hash(args)` means a resume never refunds twice.

## G. Decisions

Rejection escalates instead of ending the run, so a refused refund still reaches a human team. A fourth `prohibited` tier (D2) is not built.

## H. Failure handling

A second run on a waiting ticket is 409. Resuming a run that is not paused is 409. A viewer is 403 on every write.

## I. Testing

`tests/workflow/test_graph_run.py` covers pause, approve-once, reject, policy escalation, injection containment and role-based access control (RBAC). Not tested: an approval nobody decides (no timeout exists).

## J. Interview-ready explanation

"Approval is a tool property. The graph pauses with `interrupt()`, the API records the decision, and an idempotency key guarantees one execution."

## K. Next phase

Phases 12 and 13 put the console in front of these routes.
