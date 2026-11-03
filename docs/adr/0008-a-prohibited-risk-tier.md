# ADR-0008: A fourth risk tier, `prohibited`

## Status

Proposed. This is decision D2 in `CLAUDE.md` section 20. It is not taken, and nothing may be built on it.

## Context

The upstream policy engine can forbid an action outright, for example closing an account from the CRM.
CloudDesk's `CLAUDE.md` section 7.4 can only require approval, using the tiers `low`, `medium` and `high`
and a per-tool approval bit. Today there is no way to express "never".

## Decision

Not taken. The question is whether to add `prohibited` as a fourth tier, so a tool can be refused even with
an approval.

## Consequences

If adopted: `ToolPolicy` and the risk model change, the Phase 6 and 7 tasks and tests grow, and the approval
screen needs a refusal state. If not adopted, "never" stays unexpressible and the nearest control is to
leave a tool unregistered.
