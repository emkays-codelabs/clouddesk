# ADR-0001: Every data table carries `tenant_id`

## Status

Accepted. Settled 2026-11-02 as decision D1.

## Context

The upstream product (ACSRP) is multi-tenant: `tenant_id` and row-level security on every table
(`04_LLD.md` section 3.2, requirement FR-42). CloudDesk is a single-tenant v1. `CLAUDE.md` section 6
already promised row-level security on all data tables, but the table list had no column to key a policy on,
so the specification contradicted itself.

## Decision

Every data table has a not-null, indexed `tenant_id` (`String(36)`), and it is the first column of every
composite index. Row-level security is keyed on it. One tenant row is seeded, and v1 builds no tenant
features: no tenant CRUD, per-tenant routing, budgets or console switching. Repositories are the only place
the tenant filter lives.

## Consequences

- The column costs one field and one index now. Adding it later would mean migrating all 16 tables, every
  query and every test at once.
- SQLite has no row-level security, so on the demo database the repository filter is the boundary. One test
  must prove a second tenant's rows stay invisible.
- No router, service, agent or tool may write `tenant_id` into a query.
- This was settled by Claude on the owner's instruction, not by a separate review. The owner can overrule it
  in `MEMORY.md`.
