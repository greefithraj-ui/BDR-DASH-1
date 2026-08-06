# Phase 17 Completion Report

## Scope Completed

Phase 17 replaced the Phase 15 placeholder API (`apps/api/`, in-memory repositories) with a **database-backed, read-only backend** under `bip/apps/api/`: every GET endpoint now returns live data queried from the approved PostgreSQL sources (`bic.*`, `public.live_*`) through an asyncpg connection pool. The OpenAPI surface, response models, envelope/pagination contracts, middleware and DI wiring are unchanged. The frontend (`bip/apps/web`) remains mock-based and was not modified.

## Files Modified

### New
- `bip/apps/api/app/db/session.py` — asyncpg pool manager (`Database`)
- `bip/apps/api/app/db/__init__.py`
- `bip/apps/api/app/dependencies/database.py` — `get_db_connection` (request-scoped pooled connection, 503 on unavailable pool)
- `bip/apps/api/app/repositories/live.py` — `LiveRepository` (live-table SQL)

### Rewritten
- `bip/apps/api/app/config/settings.py` — + DB settings, `freshness_window_seconds`
- `bip/apps/api/app/db/session.py` (replaced placeholder `ReadOnlyDatabaseSession` protocol)
- `bip/apps/api/app/schemas/filters.py` — + `sort_by`, `sort_dir`, `date_from`, `date_to`
- `bip/apps/api/app/repositories/base.py` — async `BaseSQLRepository` + `InMemoryListRepository`
- `bip/apps/api/app/repositories/{machines,rings,metrics,analytics,timeline,quality,performance,reports,administration,health,settings,system}.py`
- `bip/apps/api/app/services/base.py` — async `ReadService`, `_page_from_db`
- `bip/apps/api/app/services/{machines,rings,metrics,analytics,timeline,quality,performance,reports,administration,health,settings,system,prediction}.py`
- `bip/apps/api/app/dependencies/services.py` — async DB-backed providers
- `bip/apps/api/app/routers/{health,metrics,machines,rings,reports,analytics,timeline,prediction,quality,performance,administration,settings,system}.py` — `await` async services
- `bip/apps/api/app/main.py` — lifespan connects/disconnects the pool

### Configuration
- `bip/apps/api/requirements.txt` — + `asyncpg>=0.30.0`
- `bip/.env.development`, `bip/.env.production`, `bip/.env.example` — + `BIP_DB_*`, `BIP_FRESHNESS_WINDOW_SECONDS`
- `bip/.venv` — asyncpg 0.31.0 installed (runtime for `npm run dev:api`)

## Repositories / Services / Routers Implemented

| Domain | Repository | SQL source | Service | Router |
|---|---|---|---|---|
| health | `HealthRepository` | `bic.schema_version` | `HealthService` (async) | `/api/v1/health`, `/api/health` |
| machines | `MachinesRepository` | live rings+bdr union | `MachinesService` | `/api/v1/machines[/{machine_id}]` |
| rings | `RingsRepository` | live rings (grouped by ring MAC) | `RingsService` | `/api/v1/rings[/{ring_id}]` |
| metrics | `MetricsRepository` | `LiveRepository.aggregates` | `MetricsService` | `/api/v1/metrics[/{metric_id}]` |
| reports | `ReportsRepository` | live rings (snapshot reports) | `ReportsService` | `/api/v1/reports[/{report_id}]` |
| analytics | `AnalyticsRepository` | aggregates | `AnalyticsService` | `/api/v1/analytics/summary` |
| timeline | `TimelineRepository` | `bic.ring_events` | `TimelineService` | `/api/v1/timeline[/{event_id}]` |
| prediction | `PredictionRepository` | in-memory (placeholder) | `PredictionService` | `/api/v1/prediction/models[/{model_id}]` |
| quality | `QualityRepository` | aggregates | `QualityService` | `/api/v1/quality/summary` |
| performance | `PerformanceRepository` | aggregates | `PerformanceService` | `/api/v1/performance/summary` |
| administration | `AdministrationRepository` | `bic.schema_version` | `AdministrationService` | `/api/v1/administration/overview` |
| settings | `SettingsRepository` | live config | `SettingsService` | `/api/v1/settings` |
| system | `SystemRepository` | runtime | `SystemService` | `/api/v1/system/info` |

## DB Queries Added

- **Machines**: union of `live_rings_raw` + `live_bdr_raw`, `MAX(downloaded_at::timestamptz)` freshness, per-source fresh flags (fraction of `BIP_FRESHNESS_WINDOW_SECONDS`), online = either source fresh, `COUNT(*) OVER ()` total, parameterized search/status/date filters.
- **Fleet stats**: `CROSS JOIN LATERAL jsonb_each(content::jsonb)` with `MODE() WITHIN GROUP (ORDER BY firmware)` for dominant firmware and `FILTER` counts per slot state.
- **Rings**: group live slots by `COALESCE(ring_mac, ring_name, serial)` with MIN/MAX snapshot times, slot/state counts and derived status.
- **Timeline**: `bic.ring_events` → id, occurred_at, event_type, machine_name, message (`COALESCE(reason, event_type)`), parameterized type/search/date filters, whitelisted ORDER BY.
- **Reports**: per-machine snapshot reports from the live ring payloads.
- **Aggregates**: single query returning active/bdr/running/assigned/failed/passed slot counts, machine totals/fresh, finalized/pending removal (from `bic.active_rings`), event/history counts and `bic.schema_version`.
- **Health/administration**: `MAX(version) FROM bic.schema_version`.

All queries are parameterized (`$1…$n`); no identifiers are interpolated from user input (ORDER BY fragments are fixed whitelist strings).

## Filtering / Pagination / Sorting / Validation

- **Pagination**: `PageQuery` (page ≥ 1, page_size 1–100) enforced by SQL `LIMIT`/`OFFSET` for machines, rings, reports, timeline; in-memory for the small summary collections (metrics, analytics, quality, performance, settings, system, prediction).
- **Sorting**: `sort_by`/`sort_dir` on machines (machine_name, last_seen_at), rings (ring_id, ring_name, status, slot_count, last_seen_at), timeline (timestamp, type, machine_id), reports (id, generated_at); summary endpoints sort in Python over fixed key sets. Unknown keys fall back to the default ordering.
- **Search**: case-insensitive `ILIKE '%term%'` on natural key columns.
- **Status**: exact match (machine Online/Offline, ring Active/Warning/Finalized, timeline event_type, etc.).
- **Date range**: `date_from`/`date_to` (ISO-8601, validated by Pydantic `datetime`) applied to `downloaded_at::timestamptz`/`occurred_at`.
- **Validation**: unchanged FastAPI 422 behavior for invalid `sort_dir`, page/page_size, and malformed dates; 404 via `ResourceNotFoundError` for unknown ids.

## Explicitly Not Implemented

- No write endpoints, no DML — the API is read-only by design and by DB role (`bip_reader`).
- No ORM, no migrations, no schema changes.
- Prediction models remain a documented in-memory placeholder (no DB catalogue exists in the approved sources).
- No changes to `bip/apps/web/**`.

See the accompanying **Verification Report**, **Backward Compatibility Report**, **Technical Debt Report**, and **Acceptance Checklist**.
