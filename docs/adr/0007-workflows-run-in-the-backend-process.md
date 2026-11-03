# ADR-0007: Workflows run in the backend process

## Status

Accepted. Differs from upstream ADR-08, which queues runs on Redis for separate workers.

## Context

A separate worker needs a queue, a second deployable and its own failure modes. CloudDesk v1 is one machine,
and `POST /tickets/{id}/run` only has to return quickly and let the screen poll.

## Decision

`POST /tickets/{id}/run` writes a `workflow_runs` row, returns 202 with a `workflow_id`, and hands the graph
to FastAPI `BackgroundTasks`. State is saved after every node, and the screen polls `/workflow` every two
seconds. A separate worker is a later extension.

## Consequences

- A backend restart can interrupt a run in flight.
- A second run while a ticket is `waiting_on_approval` returns 409, as does resuming a run that is not paused.
- Moving to a worker later changes `workflow_service` and the deployment, not the graph.
- Nothing of this exists yet. It is built in Phases 10 and 11.
