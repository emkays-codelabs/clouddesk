# Phase 2: system design evolution

> **Status:** All four Phase 2 tasks (P2-1 to P2-4) are built. This document has not yet been consolidated by `/phase-docs 2`, and the phase status tables are still to be updated by the owner.

---

## P2-1: the portable data model

**Added.** `backend/app/schemas/common.py` holds the domain vocabulary as `StrEnum`s: 10 categories, 7 ticket statuses, 4 severities and 4 channels, plus the smaller enums the tables need. `backend/app/models/entities.py` holds the SQLAlchemy 2 models for `tenants` and the 16 data tables. `backend/app/core/database.py` holds the async engine, session factory and `create_tables()`.

**Portability.** The models use JSON (not JSONB) and `String(36)` UUID keys, so the same code runs on SQLite (demo) and Postgres (cloud). Enum columns are stored as VARCHAR with a CHECK constraint (`native_enum=False`), so no Postgres `CREATE TYPE` is needed. The vocabulary is defined once in `common.py` and the models import it, with a test that compares it to `docs/design/06_API_CONTRACT.md`.

**D1 in the model.** Every data table has a not-null, indexed `tenant_id` with a foreign key to `tenants.id`, and it is the first column of every composite index and unique constraint. `DEMO_TENANT_ID` is a fixed, valid UUID, because the planned RLS policies cast with `::uuid`. A test loops over `Base.metadata.tables`, so a table added later cannot omit the column.

**SQLite behaviour.** `backend/app/core/database.py` creates the database file's parent directory and turns on `PRAGMA foreign_keys=ON`, so a row with a missing tenant is rejected as Postgres would reject it.

**Planned, not built.** `asyncpg` is not installed yet. The Postgres DDL, RLS policies and migrations are in the P2-2 section below.

---

## P2-3: the repository layer

**Added.** `backend/app/repositories/` is the single place SQL is written and the single place the tenant filter lives (D1). `backend/app/repositories/base.py` defines `ScopedRepository`, built with an `AsyncSession` and a tenant id (default `DEMO_TENANT_ID`). Every read goes through `_select()`, which adds the tenant filter, and every insert is stamped with the tenant; an object carrying another tenant raises `ValueError`. `backend/app/repositories/tenants.py` holds `TenantRepository`, the one unscoped repository, because it manages the `tenants` table itself.

**Flush, never commit.** Repositories flush and leave the commit to the caller (the Phase 4 services and the P2-4 bootstrap), so one request is one transaction. A caller that forgets to commit loses its writes.

**Guards.** `tests/unit/repositories/test_repositories_layering.py` statically checks that no repository imports an agent or model client, that none bypasses the filter with `session.get` or raw SQL, and that no file under the API, services, tools, agents, memory, rag or integrations folders contains the token `tenant_id`. `tests/unit/repositories/test_repositories_tenant_isolation.py` seeds two tenants with the same natural keys, proves each read returns nothing of the other's, and fails if a public method is not classified as a read, write or create.

**Timestamps.** SQLite's `CURRENT_TIMESTAMP` has whole-second resolution and the Windows clock ticks about every 15 ms, so `_add` sets a strictly increasing microsecond `created_at` to keep insertion order.

**Planned, not built.** `SET LOCAL app.tenant_id` on Postgres (who issues it is open, see CLAUDE.md section 6) and any Postgres run of these repositories.

---

## P2-2: the Postgres schema, RLS and migrations

**Added.** `database/schema.sql` creates the 17 tables in foreign-key order, their indexes, `set_updated_at()` and one `BEFORE UPDATE` trigger per table. It is the authority for the table count: 16 data tables plus `tenants`. `database/rls_policies.sql` enables and forces row-level security on every table with one `tenant_isolation` policy: `tenant_id = current_setting('app.tenant_id')::uuid` on the data tables and `id = ...` on `tenants`. `FORCE` binds the table owner too. The file is re-runnable (`DROP POLICY IF EXISTS` first). `database/seed.sql` inserts the demo tenant row only, in one transaction with `SET LOCAL app.tenant_id`. `database/migrations/0001_initial.sql` is the schema followed by the policies, and it already contains `tenant_id`, so no migration adds it (D1).

**Type mapping.** The models use `String(36)` and the SQL uses `uuid` for every id and `tenant_id` (owner decision O1), because Postgres has no `varchar = uuid` operator and the policy text needs a uuid column. Other mappings: `String(n)` to `varchar(n)`, enums to `varchar(32)` plus a `CHECK` listing the enum values, `JSON` to `jsonb`, `DateTime(timezone=True)` to `timestamptz`, `Float` to `double precision`. Once a real `asyncpg` connection exists, uuid columns return `UUID` objects, so the first task that connects must add a type decorator in `entities.py`.

**Tests, not a database.** `tests/unit/sql_ddl.py` is a small parser for the constrained format and raises on any statement it does not recognise. Tests compare `schema.sql` with the models (tables, columns, types, nullability, defaults, enum values, foreign keys, tenant-first indexes), check RLS on every data table found in `schema.sql`, and check that the migrations in order equal `schema.sql` plus the policies. `test_applied_migrations_are_unchanged` pins the SHA-256 of `0001_initial.sql` (rule 12).

**Limits.** Nothing was applied to a Postgres instance, so syntax and policy behaviour are unproven. Supabase's `service_role` has `BYPASSRLS`, so on Supabase the policies do not constrain a backend using that key; the repository filter stays the boundary. `SET LOCAL app.tenant_id` at runtime and `asyncpg` are planned, not built.

---

## P2-4: sample data and the startup bootstrap

**Added.** `sample_data/` holds seven fictional JSON files: 8 customers (all four plans), one subscription and one workspace per customer, 13 tickets (`CD-1001` to `CD-1013`), 2 incidents (one `investigating` for SSO, one `resolved`), 5 products and 6 previous resolutions. `backend/app/services/seed_service.py` loads them through the repositories. `backend/app/main.py` gains a lifespan, and `make seed` runs the same loader by hand.

**Startup order.** The lifespan runs `create_tables()`, then `bootstrap_demo_data()`, then yields, and `dispose_engine()` on shutdown. A database error at startup is logged as the exception class and a redacted URL, with no traceback, and swallowed, so `/health/ready` can still report `degraded` instead of the process failing to start.

**Gates.** `bootstrap_demo_data()` does nothing unless `DEMO_MODE` is true, and does nothing when the database already has a customer or a ticket. The files are parsed and cross-checked before the first write, so a bad record raises `ValueError` naming it and the database stays empty. If two workers pass the emptiness check together, the unique keys make the second commit fail and that is reported as "not empty".

**One transaction, deterministic ids.** Every row is written through the repositories and committed once. Ids are `uuid5` of the record key under a fixed namespace, so `CD-1002` has the same valid UUID on every machine. Each ticket gets its first customer message, timestamped as the ticket. The loader never names the tenant column; the repositories stamp the demo tenant.

**Not in the database.** `previous_resolutions.json` is validated and left on disk for the Knowledge Agent (Phase 9), because no table holds it and loading it as tickets would break the count of 13. Knowledge articles, demo login profiles and customer memory are other tasks. `make seed` refuses to run when `DEMO_MODE` is false.

**Tested on SQLite only.** No Postgres run exists. See `tests/api/test_startup_seed.py`, `tests/unit/test_seed_service.py` and `tests/unit/test_sample_data.py`.

