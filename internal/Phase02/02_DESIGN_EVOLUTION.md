# Phase 2: system design evolution (in progress)

> **Status:** Phase 2 is not finished. This document covers task P2-1 only. The schema, RLS, repositories and seeding are planned (P2-2 to P2-4) and do not exist yet.

---

## P2-1: the portable data model

**Added.** `backend/app/schemas/common.py` holds the domain vocabulary as `StrEnum`s: 10 categories, 7 ticket statuses, 4 severities and 4 channels, plus the smaller enums the tables need. `backend/app/models/entities.py` holds the SQLAlchemy 2 models for `tenants` and the 16 data tables. `backend/app/core/database.py` holds the async engine, session factory and `create_tables()`.

**Portability.** The models use JSON (not JSONB) and `String(36)` UUID keys, so the same code runs on SQLite (demo) and Postgres (cloud). Enum columns are stored as VARCHAR with a CHECK constraint (`native_enum=False`), so no Postgres `CREATE TYPE` is needed. The vocabulary is defined once in `common.py` and the models import it, with a test that compares it to `docs/design/06_API_CONTRACT.md`.

**D1 in the model.** Every data table has a not-null, indexed `tenant_id` with a foreign key to `tenants.id`, and it is the first column of every composite index and unique constraint. `DEMO_TENANT_ID` is a fixed, valid UUID, because the planned RLS policies cast with `::uuid`. A test loops over `Base.metadata.tables`, so a table added later cannot omit the column.

**SQLite behaviour.** `backend/app/core/database.py` creates the database file's parent directory and turns on `PRAGMA foreign_keys=ON`, so a row with a missing tenant is rejected as Postgres would reject it.

**Planned, not built.** The Postgres DDL, RLS policies and migrations (P2-2); the repositories that hold the tenant filter (P2-3); the seeded tenant row, sample data and the startup hook (P2-4). `asyncpg` is not installed yet.
