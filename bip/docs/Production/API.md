# Battery Intelligence Platform — API Reference (Overview)

Version 0.3.0. Interactive spec: `GET /api/openapi.json` (also served at `/docs`).

## Conventions

- Base path: `/api` (`BIP_API_PREFIX`). Versioned resources under `/api/v1`.
- Every v1 list/detail endpoint wraps responses in `{ "data": ..., "meta": ... }`.
- Query pagination uses `FilterParams` (page/page_size/sort/order/filters) via `Depends()` — invalid values return 422.
- Errors: `{ "error": { "code", "message" } }`; `ResourceNotFoundError` → 404, unknown format → 400, unknown route → 404, trailing-slash → 307 redirect.
- Health endpoints are unauthenticated and intentionally read-only; no write endpoints exist.

## Route table

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Full health contract (status/version/service/timestamp/environment) |
| GET | `/api/v1/health` | Health under the v1 prefix |
| GET | `/api/v1/metrics` | Battery metrics page |
| GET | `/api/v1/machines`, `/api/v1/machines/{id}` | Machine registry + detail |
| GET | `/api/v1/rings`, `/api/v1/rings/{id}` | Ring inventory + detail |
| GET | `/api/v1/timeline` | Timeline events |
| GET | `/api/v1/analytics/summary` | Aggregated analytics |
| GET | `/api/v1/quality/summary` | Quality aggregates |
| GET | `/api/v1/performance/summary` | Performance aggregates |
| GET | `/api/v1/administration/overview` | Admin overview panels |
| GET | `/api/v1/settings` | Platform settings summary |
| GET | `/api/v1/system/info` | System/DB status |
| GET | `/api/v1/prediction/models` | Prediction model list |
| GET | `/api/v1/reports` | Report document summaries (paginated) |
| POST | `/api/v1/reports/generate?report_type=...` | Generate a report (10 types) |
| GET | `/api/v1/reports/{report_id}` | Report document detail |
| GET | `/api/v1/reports/download/{report_id}?format=csv|xlsx|pdf` | Download bytes |

## Report types

`Executive Summary`, `Machine Performance`, `Battery Summary`, `Battery Lifecycle`, `Quality Summary`, `Analytics Summary`, `Timeline Report`, `Operations Summary`, `System Health`, `Collector Status`.

All ten generate + download successfully in the Phase 22 validation (38/38).

## Frontend contract

`apps/web/src/lib/apiClient.ts` is the single typed client (getReports, getTimelineEvents, fetchAllPages + metrics/machines/rings via useApiQueries). `shared/contracts/health.ts` mirrors the health payload and is kept in sync with `apps/api/app/models/health.py`.
