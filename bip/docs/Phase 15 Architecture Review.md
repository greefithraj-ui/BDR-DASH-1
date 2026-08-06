# Phase 15 Architecture Review

## Overview

Phase 15 extends the FastAPI scaffold into a layered backend foundation. The design favors explicit layering (router → service → repository → placeholder data), constructor injection via FastAPI `Depends`, and a single standard response/error contract — so future phases (e.g., real repository implementations) can be swapped in without touching routers or services.

## Layering

```
apps/api/app/
├── main.py                  create_app(): OpenAPI metadata, lifespan, middleware, handlers, routers
├── config/                  Settings (pydantic-settings) + cached get_settings()
├── core/
│   ├── exceptions.py        central handlers → ErrorModel (404/422/500/501)
│   ├── logging.py           logging bootstrap
│   └── middleware.py        CORS + request-logging registration
├── middleware/              RequestLoggingMiddleware
├── models/                  pydantic response models (health, domain entities)
├── schemas/                 SuccessEnvelope, ErrorModel, PageQuery/PaginatedResponse, FilterParams
├── routers/                13 placeholder-GET routers (thin, Depends-injected services)
├── services/                ReadService base + 13 domain services (filtering/pagination)
├── repositories/            InMemoryListRepository base + 13 placeholder repositories (data)
├── dependencies/            Depends providers (settings, services)
├── utils/                   time helpers (utc_now / utc_now_iso)
├── db/session.py            marker protocol only (unchanged)
└── api/                     /api prefix → /api/v1 routers + legacy /api/health alias
```

## Request Flow

1. A client calls e.g. `GET /api/v1/machines?page=1&page_size=3&status=Healthy`.
2. FastAPI parses `PageQuery` and `FilterParams` from the query string via `Depends()` on the pydantic models; the `MachinesService` is resolved by `get_machines_service()`.
3. The router forwards the parsed values to the service with zero business logic.
4. `MachinesService` reads placeholder rows from `MachinesRepository`, applies search/status filtering and pagination, and returns `SuccessEnvelope[PaginatedResponse[Machine]]`.
5. Missing single resources raise `ResourceNotFoundError`, converted by the central handler to a 404 `ErrorModel`.
6. Every request is logged by `RequestLoggingMiddleware` (method, path, status, duration).

## Key Decisions

- **Repository interfaces only**: `ReadOnlyRepository` protocol (kept) + `InMemoryListRepository[T]` which returns deterministic placeholder data and blocks writes with `NotImplementedError`. This satisfies the "interfaces only, no queries" requirement while keeping every endpoint functional.
- **Dependency injection**: services take repositories via constructor; routers receive services via `Depends`. `HealthService` additionally receives cached `Settings`. Providers live in `dependencies/services.py`.
- **Standard envelope**: lists return `SuccessEnvelope[PaginatedResponse[T]]`, singles return `SuccessEnvelope[T]`, errors return `ErrorModel`, health returns a plain `HealthResponse` (no envelope) per the mission contract.
- **No business logic in routers**: routers only wire dependencies and declare `response_model`s.
- **Config relocated**: `Settings` moved from `core/config.py` to `config/settings.py`; `config/` becomes the canonical configuration package and all importers were updated.
- **Versioning path**: `api_router` (prefix `/api`) includes `v1_router` (prefix `/v1`). The health router is included twice deliberately to preserve the pre-Phase 15 `/api/health` contract for `scripts/check_health.py` and `apps/web/src/lib/apiClient.ts`.
- **OpenAPI**: tags metadata for all 13 groups; docs at `/api/docs`, redoc at `/api/redoc`, spec at `/api/openapi.json`.

## Data Contracts

- **Success**: `{ "data": ..., "meta": { "generated_at": "…" } }`
- **Paginated**: `{ "data": { "items": [...], "total": n, "page": p, "page_size": s }, "meta": {...} }`
- **Error**: `{ "error": code, "message": "...", "status_code": n, "timestamp": "…" }`

## Determinism

Placeholder datasets are module-level frozen tuples (AQC-01…AQC-08 machines, RNG-001…RNG-006 rings, RPT-1001… reports, PRD-01…PRD-06 prediction models, etc.) consistent with the frontend mock identities established in earlier phases. The only non-deterministic field is the health `timestamp` (by design).

## Dependencies Added

- None. Phase 15 uses only `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings` already declared in `requirements.txt`.
