# Phase 17 Verification Report

## Environment

- Host: AETHER (Windows), PostgreSQL `localhost:5432/bdr_dashboard`, role `bip_reader` (read-only).
- Python: system 3.12.9 (asyncpg 0.31.0); `bip/.venv` with asyncpg 0.31.0 installed for `npm run dev:api`.
- App: `bip/apps/api`, FastAPI `create_app()` via `app.main:app`.

## 1. Compile Validation

```
python -m compileall -q apps/api/app  →  COMPILE OK
```

## 2. App Import + OpenAPI

- `from app.main import app` — imports cleanly.
- `app.openapi()` — **20 paths**; expected 20; missing: `[]`, extra: `[]`. Tags (13 domains) unchanged.

## 3. In-Process Smoke Test (httpx + lifespan)

All requests run with the lifespan (pool connected) against the live DB:

| Endpoint | Result |
|---|---|
| `/api/v1/health`, `/api/health` | 200, `status:"ok"` |
| `/api/v1/machines` (+ status/sort/date filters, page_size=5/100) | 200 — 16 machines, real firmware/last_seen |
| `/api/v1/machines/{aqc-10|nonexistent}` | 404 `not_found` ErrorModel |
| `/api/v1/rings` (+ status filter, page_size=3/100) | 200 — 741 rings (grouped by ring MAC) |
| `/api/v1/reports` (+ get by id) | 200 (list), 404 for unknown id |
| `/api/v1/metrics` | 200 — Active Rings 741, BDR Slots, etc. |
| `/api/v1/analytics/summary` | 200 — pass rate, collector health 100% |
| `/api/v1/timeline` (+ sort) | 200 — empty items (table currently empty), envelope intact |
| `/api/v1/prediction/models` (+ by id) | 200 — placeholder models |
| `/api/v1/quality/summary` | 200 — Pass Rate, Failed Slots etc. |
| `/api/v1/performance/summary` | 200 — Machines Online 100% |
| `/api/v1/administration/overview` | 200 — schema v1 row + API row |
| `/api/v1/settings` | 200 — real config values |
| `/api/v1/system/info` | 200 — hostname/python/version |

**Failures: 0** across 25 requests.

## 4. Real Server Test (uvicorn on port 8123, venv interpreter)

- Server booted with the venv (same command shape as `npm run dev:api`).
- `/api/v1/health` returned 200 within the startup window.
- 14 further endpoint checks (machines list/get, rings, reports, metrics, analytics, timeline, quality, performance, administration, settings, system, prediction, machines with sort+date-range): **all 200**.
- Server cleanly terminated.

## 5. Read-Only Guarantee

- Grep for `INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE` across `apps/api/app`: only match is the CORS `allow_methods` list in `core/middleware.py` (HTTP methods, not SQL).
- Legacy tables (`machine_logs`, `archive_entries`, `ring_status`) appear only in a docstring stating they are not used.
- All queries are SELECT-only and parameterized; the `bip_reader` role has SELECT grants only (double protection).

## 6. Configuration Validation

- `BIP_DB_*` and `BIP_FRESHNESS_WINDOW_SECONDS` added to `.env.development`, `.env.production`, `.env.example`; settings load via pydantic-settings (`BIP_` prefix) with sane defaults.
- `requirements.txt` now includes `asyncpg>=0.30.0`.

## 7. Not Verified / Out of Scope

- Frontend behavior (web is mock-based; not modified).
- Python static type checking — none configured in the repo (no mypy/pyright config); the documented gate is compile + import + runtime validation.
- Prediction models remain placeholder by design (no DB source).
