# Phase 2: system design evolution (in progress)

> **Status:** Phase 2 is not finished. This document covers tasks P2-1, P2-2 and P2-3. Seeding of sample data (P2-4) is planned and does not exist yet.

---

## P2-1: the portable data model

**Added.** `backend/app/schemas/common.py` holds the domain vocabulary as `StrEnum`s: 10 categories, 7 ticket statuses, 4 severities and 4 channels, plus the smaller enums the tables need. `backend/app/models/entities.py` holds the SQLAlchemy 2 models for `tenants` and the 16 data tables. `backend/app/core/database.py` holds the async engine, session factory and `create_tables()`.

**Portability.** The models use JSON (not JSONB) and `String(36)` UUID keys, so the same code runs on SQLite (demo) and Postgres (cloud). Enum columns are stored as VARCHAR with a CHECK constraint (`native_enum=False`), so no Postgres `CREATE TYPE` is needed. The vocabulary is defined once in `common.py` and the models import it, with a test that compares it to `docs/design/06_API_CONTRACT.md`.

**D1 in the model.** Every data table has a not-null, indexed `tenant_id` with a foreign key to `tenants.id`, and it is the first column of every composite index and unique constraint. `DEMO_TENANT_ID` is a fixed, valid UUID, because the planned RLS policies cast with `::uuid`. A test loops over `Base.metadata.tables`, so a table added later cannot omit the column.

**SQLite behaviour.** `backend/app/core/database.py` creates the database file's parent directory and turns on `PRAGMA foreign_keys=ON`, so a row with a missing tenant is rejected as Postgres would reject it.

**Planned, not built.** Sample data and the startup hook (P2-4). `asyncpg` is not installed yet. The Postgres DDL, RLS policies and migrations are in the P2-2 section below.

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
