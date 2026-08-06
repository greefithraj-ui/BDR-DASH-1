# Phase 17 Backward Compatibility Report

## Objective

Confirm that Phase 17's database-backed rewrite does not break any contract established in Phase 15/16, for the frontend (`bip/apps/web`, mock-based, untouched) and for external scripts (e.g. `check_health.py`, `apiClient.ts`).

## Compatibility Verified

### 1. OpenAPI surface — identical
- All 19 `/api/v1` paths plus the legacy `/api/health` alias are present (20 paths total, exact match; no missing, no extra paths).
- Paths and HTTP methods verified against the Phase 15 route list (`app.api.v1.router` + legacy health router).
- OpenAPI tags (13 domain tags) unchanged.

### 2. Response models — unchanged
- Frozen Pydantic domain models in `app/models/domain.py` and `app/models/health.py` were **not modified**.
- `SuccessEnvelope[T]` (data + `meta.generated_at`), `PaginatedResponse[T]` (items, total, page, page_size), `ErrorModel`, `HealthResponse` all untouched.
- `HealthResponse.status` remains `Literal["ok"]`; the legacy `/api/health` payload shape is byte-for-byte the same shape as before.

### 3. Query parameters — superset only
- `search`, `status`, `page`, `page_size` behave as before (exact-match / case-insensitive filters).
- `sort_by`, `sort_dir`, `date_from`, `date_to` are **optional additions** — requests that omit them get the previous semantics.

### 4. Status codes — preserved
- 200 for all success paths; 404 with `ErrorModel` (`not_found`) for unknown ids (e.g. `GET /api/v1/machines/nonexistent`).
- 422 for invalid pagination/sort/date inputs; 503 `ErrorModel` when the database pool is unavailable (new, documented behavior).
- The `NotImplementedError` → 501 handler remains registered (still used by `InMemoryListRepository.write`).

### 5. Frontend contract
- `apiClient.ts` only calls `GET /health` and expects `{status, service, …}` — verified live, returns `{"status":"ok","service":"Battery Intelligence Platform API",…}`.
- No web files were touched; the frontend continues to consume mock data.

### 6. Runtime compatibility
- `npm run dev:api` (uvicorn, `--app-dir apps/api`, port 8100) works with the venv after installing `asyncpg>=0.30.0` (added to `requirements.txt`).
- Config: all new settings have defaults; existing `BIP_*` variables keep their meaning.

## Behavioral Differences (intentional, documented)

| Aspect | Phase 15/16 (placeholder) | Phase 17 (live) |
|---|---|---|
| Data source | hardcoded rows | live PostgreSQL tables |
| Machine ids | `AQC-01…AQC-08` | `aqc-04, aqc-10, …` (live `machine_name`) |
| Timeline/report contents | fabricated rows | `bic.ring_events` / live snapshots (empty when no data) |
| Metrics values | static | computed from live aggregates |
| DB unavailable | N/A (no DB) | 503 `ErrorModel` on DB-backed endpoints |

These are data-content changes driven by the new (real) data source; the envelope, pagination, filtering and error-shape contracts are unchanged.

## Verification Evidence

- Smoke test: 25 requests, **0 failures** (all DB-backed endpoints 200, unknown ids 404, placeholder prediction 200).
- OpenAPI check: 20/20 paths, missing: `[]`, extra: `[]`.
- Live uvicorn boot + HTTP checks on 14 endpoints: all 200.
