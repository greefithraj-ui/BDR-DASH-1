# Phase 17 Acceptance Checklist

## Scope
Phase 17 Backend API Completion — `bip/apps/api` switched from in-memory placeholders to read-only, asyncpg-backed live PostgreSQL data, without breaking the Phase 15/16 contracts.

## Database Access & Safety

- [x] API connects to `bdr_dashboard` via the `bip_reader` role (SELECT-only)
- [x] asyncpg connection pool created at startup, closed at shutdown (`lifespan`)
- [x] One pooled connection per request (`get_db_connection`), 503 `ErrorModel` when pool unavailable
- [x] Only approved tables read: `bic.*` + `public.live_rings_raw` / `public.live_bdr_raw`
- [x] Legacy tables (`machine_logs`, `archive_entries`, `ring_status`) never read
- [x] No INSERT/UPDATE/DELETE/DDL anywhere; all SQL parameterized; ORDER BY via fixed whitelist
- [x] `bic.machine_checkpoint` not relied upon (empty); machine health derived from live freshness
- [x] `downloaded_at::timestamptz` casting used for correct UTC freshness math

## Configuration

- [x] `BIP_DB_*` + `BIP_FRESHNESS_WINDOW_SECONDS` added to settings, `.env.development`, `.env.production`, `.env.example`
- [x] `asyncpg>=0.30.0` added to `requirements.txt` and installed in `bip/.venv` (dev server runs)

## Endpoints (all 20 paths, verified live)

- [x] `/api/v1/health` and legacy `/api/health` → 200 `HealthResponse`
- [x] `/api/v1/machines`, `/api/v1/machines/{id}` → live machines, 404 for unknown ids
- [x] `/api/v1/rings`, `/api/v1/rings/{id}` → rings grouped by ring MAC with derived status
- [x] `/api/v1/reports`, `/api/v1/reports/{id}` → per-machine live snapshot reports
- [x] `/api/v1/metrics`, `/api/v1/metrics/{id}` → fleet aggregates
- [x] `/api/v1/analytics/summary` → pass rate / collector health
- [x] `/api/v1/timeline`, `/api/v1/timeline/{id}` → `bic.ring_events`
- [x] `/api/v1/prediction/models`, `/prediction/models/{id}` → placeholder (no DB source, permitted)
- [x] `/api/v1/quality/summary`, `/api/v1/performance/summary` → derived indicators
- [x] `/api/v1/administration/overview` → schema version + runtime
- [x] `/api/v1/settings`, `/api/v1/system/info` → real config/runtime values

## Filtering / Pagination / Sorting / Validation

- [x] `search` (ILIKE), `status` (exact) on all list endpoints
- [x] `sort_by` / `sort_dir` on machines, rings, timeline, reports (+ summary collections)
- [x] `date_from` / `date_to` ISO-8601 filtering on machines, rings, timeline, reports
- [x] SQL `LIMIT/OFFSET` pagination with accurate `total` (`COUNT(*) OVER ()`)
- [x] `page ≥ 1`, `page_size 1–100`, invalid input → 422; unknown ids → 404 `ErrorModel`

## Backward Compatibility

- [x] OpenAPI: 20/20 paths identical, no missing/extra, tags unchanged
- [x] Response models, envelope, pagination contract, `ErrorModel`, `HealthResponse` untouched
- [x] `FilterParams` additions are optional (superset only)
- [x] `bip/apps/web/**` not modified
- [x] `npm run dev:api` command path unchanged and bootable (venv + asyncpg)

## Verification

- [x] `compileall` passes
- [x] In-process smoke test: 25 requests, 0 failures
- [x] Real uvicorn (port 8123, venv) boots; 15 endpoint checks all 200
- [x] Deliverables produced: Architecture Review, Completion, Backward Compatibility, Verification, Technical Debt (this checklist)

## Out of Scope / Explicitly Not Done

- [ ] No write endpoints, ORM, migrations, or schema changes (by design)
- [ ] No frontend changes (mock-based by design)
- [ ] No automated test suite (pre-existing repo condition; flagged in Technical Debt Report)
- [ ] Prediction models stay in-memory until a real source exists
