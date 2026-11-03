# ADR-0003: Policy is decided by rules, judgement by the model

## Status

Accepted. Matches upstream ADR-07.

## Context

Some cases must never depend on a model's probabilities: payment disputes, account deletion, security
incidents, data loss, legal matters and enterprise outages. A prompt can be argued out of a rule, and a
model can be talked into an export by text inside a ticket.

## Decision

Policy cases are decided by deterministic, tested rules (`agents/rules.py`, `ToolPolicy`). The model adds
judgement only in grey areas, and a rule always wins. Severity rules may raise the model's severity and
never lower it. Planned actions come from `ResolutionAgent.plan_actions`, not from the model.

## Consequences

- Every policy decision is auditable and covered by a unit test that needs no model.
- Money and account changes (refunds, setting resets, deletions, disputes) always wait for a recorded human
  approval.
- A vague model escalation is distrusted: it is kept only when severity is high and confidence is not low.
- Adding a policy case means adding a rule and a test, not editing a prompt.
