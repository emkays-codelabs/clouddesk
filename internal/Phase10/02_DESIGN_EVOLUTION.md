# Phase 10: system design evolution

> **Status:** complete and validated locally. P10-1 to P10-7 are done. Nothing is deployed.

## A. Overview

Phase 10 turns six standalone agents into a resumable workflow with a trace.

## B. Initial architecture

Specialist agents callable only from tests. No state model, no graph, no events, no run route.

## C. Evolution by task

- **P10-1 state:** `agents/state.py` with reducers so parallel contributions never overwrite one another.
- **P10-2 to P10-4 nodes:** supervisor, investigation and decision nodes, each wrapped by the tracer in `agents/nodes/common.py`.
- **P10-5 graph:** `agents/graph.py` with routing, the 12-step budget and the failure path.
- **P10-6 tracer:** `backend/app/core/observability.py` writes `workflow_events`.
- **P10-7 application programming interface (API):** run, workflow, events and agents routes.

## D. Final architecture

```mermaid
flowchart LR
  A[understand] --> B[classify] --> C[customer context] --> D[retrieval] --> E[troubleshoot] --> F[plan] --> G{risk check}
  G -->|policy, injection, low confidence| X[escalation]
  G -->|approval needed| H[human approval]
  G -->|low risk| I[execute]
  H -->|approved| I
  H -->|rejected| X
  I --> J[summary] --> K[memory update]
  X --> J
```

## E. Data flow

The route creates a `workflow_runs` row and returns 202. A background task streams the graph, saving state and events after every node. The user interface (UI) polls the workflow route every two seconds.

## F. Decisions and trade-offs

In-process execution (architecture decision record (ADR) 0007) over a queue; a partial-dictionary node contract; a rule-first router so policy never depends on a model's confidence.

## G. Improvements made during the phase

An injected ticket (CD-1013) originally auto-resolved; the risk check now escalates on an injection flag. A node stored raw action dicts and produced a 500; actions are now schema-valid. A completed run no longer overwrites a resolved ticket's status.

## H. Limitations

No worker process, so a restart loses a run in flight. Only the 12-step and 0.6-confidence budgets exist; the cycle and question budgets are not built. Concurrent runs of the same ticket are blocked by status only.

## I. Completion summary

Seven tasks done; 1320 backend tests passed offline when the phase closed (1,406 by the end of the project); the graph ran end to end in Docker on the real model.


---

## QA remediation, 2026-11-27: one live run per ticket

The local audit found that `create_run` only refused a run while the ticket waited on an approval, so a second run could start while one was live and two runs could race on one ticket. `backend/app/services/workflow_service.py` now returns a conflict (409) when the latest run is still `running`, unless it started more than 15 minutes ago (`RUN_STALE_AFTER`), because a restart drops in-flight runs and must not block a ticket forever. Regression test: `tests/workflow/test_graph_run.py`.

Latency findings (measured, not changed): a real-model run takes about 165 seconds in five sequential model calls (classification, severity, diagnosis, resolution plan, escalation judgement), over 90 percent of it provider time; everything else totals under 0.3 seconds. The escalation-judgement call records a duration of 0 ms although its node takes about 30 seconds, an instrumentation gap. Candidate savings, none applied: classification and severity in parallel, a faster tier for the resolution plan, and skipping the escalation judgement when a policy rule already decides (a safety path, so it needs an owner decision).
