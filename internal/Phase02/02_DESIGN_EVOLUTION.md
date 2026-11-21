# Phase 2: system design evolution (in progress)

> **Status:** Phase 2 is not finished. This document covers tasks P2-1 and P2-3. The schema and RLS (P2-2) and seeding (P2-4) are planned and do not exist yet.

---

## P2-1: the portable data model

**Added.** `backend/app/schemas/common.py` holds the domain vocabulary as `StrEnum`s: 10 categories, 7 ticket statuses, 4 severities and 4 channels, plus the smaller enums the tables need. `backend/app/models/entities.py` holds the SQLAlchemy 2 models for `tenants` and the 16 data tables. `backend/app/core/database.py` holds the async engine, session factory and `create_tables()`.

**Portability.** The models use JSON (not JSONB) and `String(36)` UUID keys, so the same code runs on SQLite (demo) and Postgres (cloud). Enum columns are stored as VARCHAR with a CHECK constraint (`native_enum=False`), so no Postgres `CREATE TYPE` is needed. The vocabulary is defined once in `common.py` and the models import it, with a test that compares it to `docs/design/06_API_CONTRACT.md`.

**D1 in the model.** Every data table has a not-null, indexed `tenant_id` with a foreign key to `tenants.id`, and it is the first column of every composite index and unique constraint. `DEMO_TENANT_ID` is a fixed, valid UUID, because the planned RLS policies cast with `::uuid`. A test loops over `Base.metadata.tables`, so a table added later cannot omit the column.

**SQLite behaviour.** `backend/app/core/database.py` creates the database file's parent directory and turns on `PRAGMA foreign_keys=ON`, so a row with a missing tenant is rejected as Postgres would reject it.

**Planned, not built.** The Postgres DDL, RLS policies and migrations (P2-2); the seeded tenant row, sample data and the startup hook (P2-4). `asyncpg` is not installed yet.

---

## P2-3: the repository layer

**Added.** `backend/app/repositories/` is the single place SQL is written and the single place the tenant filter lives (D1). `backend/app/repositories/base.py` defines `ScopedRepository`, built with an `AsyncSession` and a tenant id (default `DEMO_TENANT_ID`). Every read goes through `_select()`, which adds the tenant filter, and every insert is stamped with the tenant; an object carrying another tenant raises `ValueError`. `backend/app/repositories/tenants.py` holds `TenantRepository`, the one unscoped repository, because it manages the `tenants` table itself.

**Flush, never commit.** Repositories flush and leave the commit to the caller (the Phase 4 services and the P2-4 bootstrap), so one request is one transaction. A caller that forgets to commit loses its writes.

**Guards.** `tests/unit/repositories/test_repositories_layering.py` statically checks that no repository imports an agent or model client, that none bypasses the filter with `session.get` or raw SQL, and that no file under the API, services, tools, agents, memory, rag or integrations folders contains the token `tenant_id`. `tests/unit/repositories/test_repositories_tenant_isolation.py` seeds two tenants with the same natural keys, proves each read returns nothing of the other's, and fails if a public method is not classified as a read, write or create.

**Timestamps.** SQLite's `CURRENT_TIMESTAMP` has whole-second resolution and the Windows clock ticks about every 15 ms, so `_add` sets a strictly increasing microsecond `created_at` to keep insertion order.

**Planned, not built.** `SET LOCAL app.tenant_id` on Postgres (who issues it is open, see CLAUDE.md section 6) and any Postgres run of these repositories.
