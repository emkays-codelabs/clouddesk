# Architecture decision records

An architecture decision record (ADR) says what was decided, why, and what follows from it, in one short
file. This folder holds the ones that shape CloudDesk AI. `CLAUDE.md` still wins when it disagrees with a
record, and a decision that changes the plan is made in `CLAUDE.md` first.

## How to add one

1. Copy the template below into `NNNN-short-name.md`. `NNNN` is the next unused four-digit number.
2. Fill in every section. Keep it to one page.
3. Add a row to the index below, with a link.
4. Never rewrite an accepted record to change the decision. Write a new record that supersedes it, and set
   the old one's status to `Superseded by NNNN`.

## Statuses

| Status | Meaning |
|---|---|
| Accepted | Decided, and the code or the plan follows it. |
| Proposed | A real question that has not been decided. Nothing may be built on it yet. |
| Superseded | Replaced by a later record, which the status line names. |

## Template

```markdown
# ADR-NNNN: Title

## Status

Accepted | Proposed | Superseded by NNNN

## Context

What forced a decision, and what the upstream design says.

## Decision

What CloudDesk AI does.

## Consequences

What gets easier, what gets harder, and what must now stay true.
```

## Index

The upstream numbers (ADR-01 to ADR-08) are in `03_HLD.md` section 14. D1 to D6 are in `CLAUDE.md`
sections 6 and 20.

| Record | Decision | Status | Source |
|---|---|---|---|
| [0001](0001-tenant-id-on-every-table.md) | Every data table carries `tenant_id` | Accepted | D1 |
| [0002](0002-langgraph-supervisor-with-six-specialists.md) | A LangGraph workflow coordinating six specialists | Accepted | ADR-01 |
| [0003](0003-policy-decided-by-rules-not-the-model.md) | Policy is decided by rules, judgement by the model | Accepted | ADR-07 |
| [0004](0004-tools-run-in-process-through-one-registry.md) | Tools run in process through one registry | Accepted | ADR-02, differs |
| [0005](0005-vector-store-behind-a-protocol.md) | The vector store sits behind a protocol | Accepted | ADR-03 |
| [0006](0006-sqlite-for-the-demo-postgres-for-the-cloud.md) | SQLite for the demo, Postgres for the cloud | Accepted | ADR-04, differs |
| [0007](0007-workflows-run-in-the-backend-process.md) | Workflows run in the backend process | Accepted | ADR-08, differs |
| [0008](0008-a-prohibited-risk-tier.md) | A fourth risk tier, `prohibited` | Proposed | D2 |
| [0009](0009-write-capable-mcp-servers.md) | Write-capable MCP servers | Proposed | D3 |
| [0010](0010-model-tiering-and-a-gateway.md) | Model tiering behind a gateway | Proposed | D4, ADR-05 |
| [0011](0011-kubernetes-and-helm.md) | Kubernetes and Helm as the parity target | Proposed | D5, ADR-06 |
| [0012](0012-the-harder-evaluation-bar-and-a-red-team-set.md) | The harder evaluation bar and a red-team set | Proposed | D6 |
