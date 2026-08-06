# Phase 17 Architecture Review

## Purpose

Phase 17 replaced every in-memory placeholder in the Battery Intelligence Platform API (`bip/apps/api`) with real, read-only PostgreSQL access using `asyncpg`, while preserving the Phase 15/16 layered architecture, OpenAPI surface, response contracts, and dependency-injection wiring.

## Architecture Preserved

The existing layering is unchanged:

```
Router (HTTP only)
  → Service (business logic, row→model mapping)
    → Repository (SQL only)
      → Database (asyncpg pool, one connection per request)
```

No ORM was introduced. Queries are raw, parameterized `asyncpg` SQL with fixed ORDER BY fragments (no user-controlled identifiers are interpolated).

## Components Added / Changed

### 1. Configuration (`app/config/settings.py`)
- Added database settings under the existing `BIP_` prefix: `db_host`, `db_port`, `db_name`, `db_user`, `db_password`, `db_pool_min`, `db_pool_max`, `db_connect_timeout`, `db_command_timeout`.
- Added `freshness_window_seconds` (default 60), the single live-data "freshness" constant shared by machines, metrics, analytics, quality and performance.
- `cors_origin_list` helper added; all prior settings untouched.

### 2. Database layer (`app/db/session.py`)
- `Database` class owns the asyncpg connection pool; `connect()` / `disconnect()` are invoked from the app `lifespan` in `main.py`.
- The pool is created for the `bip_reader` role (SELECT-only) — the API is structurally read-only.
- `Database.ping()` (non-raising) kept for future readiness checks; `db` singleton exported.
- `app/db/__init__.py` exposes `Database` and `db`.

### 3. Request-scoped connection (`app/dependencies/database.py`)
- `get_db_connection()` is a FastAPI yield-dependency: acquires a pooled connection for the duration of one request, returning **503** `ErrorModel` when the pool is unavailable.
- All database-backed service providers depend on it; connection lifecycle is entirely framework-managed.

### 4. Query parameters (`app/schemas/filters.py`)
- `FilterParams` extended with `sort_by`, `sort_dir` (`asc`|`desc`, default `asc`), `date_from`, `date_to` (ISO-8601 datetimes) while keeping `search` and `status` unchanged — backward compatible (all new fields optional).

### 5. Repository layer (`app/repositories/`)
- `base.py`: `BaseSQLRepository` (holds the pooled connection, `fetch_all`/`fetch_one`/`fetch_val`), `ReadOnlyRepository` protocol, `InMemoryListRepository` (now async) for the prediction placeholder, and the shared `OCCUPIED_SERIAL_CONDITION` SQL fragment.
- `live.py`: `LiveRepository` — the only place that reads `public.live_rings_raw` / `public.live_bdr_raw`: machine list/get with freshness, fleet stats, and the fleet aggregate query.
- Domain repositories: `machines`, `rings`, `timeline`, `reports`, `administration`, `health` run SQL; `metrics`, `analytics`, `quality`, `performance` derive from `LiveRepository.aggregates`; `settings`/`system` build from live config/runtime; `prediction` remains in-memory (documented placeholder — no DB source exists).

### 6. Service layer (`app/services/`)
- `base.py`: `ReadService[T]` is now async with `get_by_id` (404 via `ResourceNotFoundError`), `_page` (in-memory pagination) and `_page_from_db` (SQL-paginated).
- All 13 services expose async methods; DB-backed services map raw rows → frozen domain models and encode business rules (machine health score/status derivation, ring status derivation, pass-rate/collector-health percentages).
- `settings`/`system`/`prediction` services are async wrappers over config/runtime/in-memory data.

### 7. Dependency providers (`app/dependencies/services.py`)
- DB-backed providers are `async def` with `Depends(get_db_connection)`; `prediction`, `settings`, `system` remain synchronous constructors. Service construction is per-request (cheap) — same DI pattern as before, now with a pooled connection.

### 8. Routers (`app/routers/*`)
- Unchanged signatures and response models; each route now `await`s the async service call.

### 9. App lifecycle (`app/main.py`)
- `lifespan` now calls `await db.connect()` before serving and `await db.disconnect()` on shutdown.

## Data Provenance (approved sources only)

| Domain | Source |
|---|---|
| health | `bic.schema_version` |
| machines | `public.live_rings_raw` + `public.live_bdr_raw` (union, freshness via `downloaded_at::timestamptz`) |
| rings | `public.live_rings_raw` (grouped by ring MAC) |
| metrics / analytics / quality / performance | `public.live_*` aggregates |
| timeline | `bic.ring_events` |
| reports | `public.live_rings_raw` (per-machine snapshot report) |
| administration | `bic.schema_version` + runtime/config |
| settings / system | live application config / runtime |
| prediction | **no DB source — in-memory placeholder retained** |

Legacy tables (`machine_logs`, `archive_entries`, `ring_status`) are never read. The role `bip_reader` has SELECT grants only; the codebase contains no DML.

## Design Decisions

- **One connection per request** (not per query) — consistent with the existing DI architecture and simpler than a repository-side pool.
- **Freshness window** centralised in settings so machine/aggregate definitions agree.
- **Ring capacity**: the read-only sources carry no capacity data; `capacity_mwh` surfaces the occupied slot count as a documented approximation.
- **Machine identity**: machines are identified by `machine_name` from the live tables (aqc-xx); the old AQC-01…AQC-08 placeholder identities were never in the DB.
- **Sorting safety**: ORDER BY clauses are resolved from fixed whitelist fragments keyed on `(sort_by, sort_dir)`; unknown keys fall back to the default.
