# ADR-0006: SQLite for the demo, Postgres for the cloud

## Status

Accepted. Differs from upstream ADR-04, which uses Postgres for the checkpointer and the audit store.

## Context

Upstream wants one durable system of record. CloudDesk must run offline on one machine and in tests with no
database server, and it must also deploy against Supabase Postgres.

## Decision

The SQLAlchemy 2 models are portable: JavaScript Object Notation (JSON) rather than JSON binary (JSONB), and `String(36)` identifiers. The demo uses
SQLite, created at startup, with the workflow checkpointer in `AsyncSqliteSaver` (or `InMemorySaver` when
`CHECKPOINT_DB_PATH=:memory:`). The cloud uses Postgres, with the data definition language (DDL) in `database/schema.sql`.

## Consequences

- The same code runs on both, and the tests need no server.
- SQLite has no row-level security, so the repository tenant filter is the boundary there (see
  [ADR-0001](0001-tenant-id-on-every-table.md)).
- A restart can drop an in-memory pause, and file checkpoints survive only on a volume.
- `database/schema.sql` is the authority for the table list (written in Phase 2; 17 tables). The checkpointer is
  built (Phase 10).
- **Update, 2026-11-27.** At the owner's request the Docker stack now runs on Postgres 16 (`asyncpg`), and the schema,
  the row-level-security policies and the migration were applied to a real Postgres and tested. SQLite remains the
  engine for the offline test suite. Row-level security is still not enforced at runtime (the application programming interface (API) does not set
  `app.tenant_id`), so the repository filter remains the boundary.
