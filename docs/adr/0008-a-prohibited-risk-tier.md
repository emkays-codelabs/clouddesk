# ADR-0008: A fourth risk tier, `prohibited`

## Status

Accepted on 2026-11-27 (owner approval in chat). This is decision D2 in `CLAUDE.md` section 20. The decision is taken; the code is not built yet, and building it needs a `TASKS.md` row.

## Context

The upstream policy engine can forbid an action outright, for example closing an account from the CRM.
CloudDesk's `CLAUDE.md` section 7.4 can only require approval, using the tiers `low`, `medium` and `high`
and a per-tool approval bit. Today there is no way to express "never".

## Decision

Add `prohibited` as a fourth risk tier. A tool marked `prohibited` is refused by `ToolRegistry.execute` even when `approved=True`, returns a distinct error, and is shown as refused (not as awaiting approval) on the approval screen. A tool missing from the policy table still fails closed as requiring approval.

## Consequences

If adopted: `ToolPolicy` and the risk model change, the Phase 6 and 7 tasks and tests grow, and the approval
screen needs a refusal state. If not adopted, "never" stays unexpressible and the nearest control is to
leave a tool unregistered.
