# Phase 10 explained: the workflow graph and trace

> **Status:** implemented and tested offline (`tests/workflow/`). The graph was also run end to end in Docker against the real Euron model. Nothing is deployed.

## A. Executive summary

Phase 10 joins the six agents into one LangGraph workflow. A ticket runs through twelve steps, every step is recorded, state is saved after each node, and the run can pause and resume. The API exposes it as run, workflow and events routes.

## B. Business problem and solution

Without a graph the agents are parts on a bench. The workflow gives support agents one button, "Run AI workflow", and an inspectable record of what the platform did and why, including time, tokens and tool calls.

## C. Architecture in simple language

`agents/graph.py` defines the nodes and the routing. `agents/state.py` defines the state every node updates by returning a partial dictionary. `agents/checkpointer.py` saves state (in memory for tests, SQLite otherwise) so a paused run can resume under the same `thread_id`. `backend/app/core/observability.py` is the tracer that writes `workflow_events`. `backend/app/services/workflow_service.py` creates the run, starts it in the background and saves state after each node.

## D. File-by-file

| File | Purpose |
|---|---|
| `agents/state.py` | `SupportState` and its reducers: `errors`, `completed_nodes` and `route_history` append, `step_count` sums, `token_usage` merges. |
| `agents/graph.py` | Builds the graph, routing functions and `GRAPH_NODES` / `GRAPH_EDGES`. |
| `agents/nodes/supervisor.py` | Understand, classify and the final summary. |
| `agents/nodes/investigate.py` | Customer context, knowledge retrieval, troubleshooting. |
| `agents/nodes/decision.py` | Resolution planning, risk check and execution. |
| `agents/nodes/human_approval.py` | Pauses with `interrupt()`. |
| `agents/nodes/escalation.py` | Escalation and the memory update. |
| `agents/nodes/common.py` | Shared node plumbing: tracer, tool-call recording, failure handling. |
| `backend/app/core/observability.py` | `WorkflowTracer` (never raises). |
| `backend/app/services/workflow_service.py` | Run lifecycle, resume, state persistence. |
| `backend/app/services/agent_service.py` | Agent list and run statistics for `/agents`. |
| `backend/app/api/workflow.py` | `POST /tickets/{id}/run`, `GET /workflow`, `GET /events`. |
| `backend/app/api/agents.py` | `GET /agents`. |

## E. Execution flow

understand, classify, customer context, retrieval, troubleshooting, resolution planning, risk check. Then one of three routes: escalation (policy, injection, low confidence or a spent budget), `human_approval` (pending approval-required actions) or execute. After that: summary, memory update, end. A failed node sets `failed` and escalates rather than crashing.

## F. Concepts

- **Reducers** let many nodes add to a list without overwriting each other.
- **Interrupt** stops a run inside a node; code before `interrupt()` runs again on resume, so it must be tiny and free of side effects.
- **Budgets**: at most 12 graph steps and a confidence floor of 0.6.

## G. Decisions

Background tasks run in the API process (ADR 0007) rather than a worker: simpler, but a restart loses in-flight runs, which is why state is saved after every node.

## H. Failure handling

Tool failures become results, not exceptions. A node failure is recorded, the status becomes `failed` and the escalation path runs. The tracer swallows its own errors so telemetry cannot break a run.

## I. Testing

`tests/workflow/test_state_and_graph.py` checks graph shape and routing; `test_graph_run.py` runs the real app through its API: a low-risk ticket completes and remembers, a refund pauses and runs once, a viewer gets 403, a second run on a waiting ticket is 409. Not tested: a process restart during a run, concurrent runs of one ticket.

## J. Interview-ready explanation

"The workflow is a state machine with reducers, an interrupt for human approval, a checkpointer for resume and a tracer that records every node, tool call and model call without ever failing a run."

## K. Next phase

Phase 11 adds the approval, escalation and demo pieces that sit on top of the pause.
