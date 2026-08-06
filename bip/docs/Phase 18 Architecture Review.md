# Phase 18 Architecture Review

## Summary

Phase 18 replaces the frontend mock provider layer with a thin, typed API access layer backed by React Query, leaving the component tree byte-identical. The architecture is a strict three-tier layering: **components → hooks (React Query + mapping) → apiClient (typed fetch) → backend `/api/v1`**.

## Layering

```
components / pages            (unchanged — consume the same hook return shapes)
        │
        ▼
feature hooks (useX)          (only code changed: getMockX() → useQuery(...))
        │  exposes: original fields + isLoading | error | refresh | isEmpty
        │  contains ALL mapping from API DTOs → feature domain types
        ▼
src/lib/apiClient.ts          (single API client, extended, not duplicated)
        │  typed DTOs + SuccessEnvelope/PaginatedResponse + requestData unwrap
        │  fetchAllPages for collections larger than page_size=100
        ▼
backend /api/v1               (Phase 17, unchanged — read-only PostgreSQL via asyncpg)
```

## Design Decisions

1. **Single client, no duplication.** All HTTP access stays in `apiClient.ts`. New methods reuse the existing `request<T>` helper; a new `requestData<T>` unwraps the `SuccessEnvelope` so hooks receive `PaginatedResponse<T>` directly. A new `ApiQuery` param object is serialized by `buildQuery`; empty/undefined params are omitted.
2. **Mapping lives in hooks.** API DTOs (`MachineDto`, `RingDto`, …) are deliberately flat and snake_case (matching the backend), and feature domain types (`BatteryRecord`, `TimelineEvent`, …) are built inside each hook. No DTO shape leaks into components.
3. **Query keys centralized.** `src/lib/queryKeys.ts` provides per-feature key factories (`machines.all`, `rings.detail(id)`, `executive.dashboard`, …) so cache identity is consistent and stable. No key string is duplicated across hooks.
4. **Stable return shapes.** Every hook preserves its pre-migration fields so no page needed changes. Additional lifecycle fields (`isLoading`, `error`, `refresh`, `isEmpty`) are additive. Dashboard hooks return an always-defined `data` (empty fallback) so the pages' existing `isLoading`/`error` guards keep TypeScript narrowing safe.
5. **Zero-downtime interactivity.** Interactive hooks (explorers, timeline, analytics) keep their filter/sort/pagination state in `useState`; only the source collection moves to `useQuery`. Empty arrays are used while loading so the pages' existing empty-state branches render instead of crashing.
6. **Multi-page collections.** `fetchAllPages` issues parallel page requests (page_size 100) for rings and timeline so features see the full dataset rather than a capped slice.
7. **Detail hooks derive from live records.** `useBatteryDetail`/`useMachineDetail` build detail panels from the already-live record passed in (the record itself came from the API), keeping the detail view synchronous and avoiding N+1 requests; no mock module is referenced.

## Cache & Freshness

- Single `QueryClient` (existing `QueryProvider`): `retry: 1`, `refetchOnWindowFocus: false`.
- All data queries use `staleTime: 30_000` — matches the backend freshness window concept without hammering the API.
- Parallel dependent fetches within a feature are batched with `Promise.all` (e.g. Executive Dashboard: metrics + analytics + quality + machines + health in one query).
- `refresh` exposes `refetch()` so future UI can add manual refresh without touching components.

## Data Availability Model

Features receive exactly what the API exposes:

| Backend data | Frontend usage |
|---|---|
| `bic.ring_events` (timeline) | Timeline events; batteries/slot empty until source carries them |
| Live ring snapshots (aggregated) | Rings, battery explorer rows, reports, machine health inputs |
| Summary endpoints (metrics/analytics/quality/performance) | All dashboard KPIs and hub cards |
| `bic.active_rings` counts | Pending removal / finalized metrics |
| Health | Collector/system status signals |

Absent dimensions (per-battery slots, product catalog, per-record quality, report schedules) surface as empty collections that trigger the pages' existing `EmptyState` rather than fabricated data.

## Quality Attributes

- **Maintainability**: one client module, one key module, one formatting module; each hook owns its mapping in one place.
- **Type safety**: DTOs are explicit; `tsc --noEmit` passes (see Verification Report).
- **Performance**: 3–7 parallel requests per dashboard; explorers fetch all pages once per 30s stale window; no render-time fetching.
- **Security**: same as Phase 17 — read-only GETs; no credentials in the client; relative `/api` base via `VITE_BIP_API_BASE_URL`.
