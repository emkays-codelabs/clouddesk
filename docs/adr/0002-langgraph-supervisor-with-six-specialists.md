# ADR-0002: A LangGraph workflow coordinating six specialists

## Status

Accepted. Matches upstream ADR-01.

## Context

A ticket needs several different kinds of work: understanding, customer lookup, retrieval, troubleshooting,
planning and escalation. One large prompt would be hard to test, and a free-running agent loop would be hard
to bound. The upstream design chose an explicit supervisor graph for its control flow, checkpoints and
human-in-the-loop interrupts.

## Decision

The business logic is one LangGraph workflow (`agents/graph.py`) over six specialists: Support Supervisor,
Customer, Knowledge, Troubleshooting, Resolution and Escalation. Each returns a Pydantic model through
`call_structured`. A `human_approval` node calls `interrupt()`, and the checkpointer stores state under a
`thread_id`.

## Consequences

- Control flow is data, so the graph shape, routing and risk levels can be tested without a model.
- A run is bounded: at most 12 graph steps, 2 investigation cycles and 2 clarifying questions, and it
  escalates below 0.6 confidence.
- Code before `interrupt()` re-runs on resume, so it must stay small and idempotent.
- Nothing of this exists yet. It is built in Phases 9 to 11.
