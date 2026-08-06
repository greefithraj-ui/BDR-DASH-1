# Phase 18 Acceptance Checklist

## 1. Mock Provider Replacement

- [x] All nine in-scope features consume backend data exclusively through `useQuery` hooks backed by `apiClient`.
- [x] No feature hook imports any mock module (verified by grep across `src/features`).
- [x] The eight removed mock files are deleted from the repository.
- [x] `reports.mock.ts` contains only `formatDuration`, still required by five report components; the mock report provider is gone.
- [x] Out-of-scope features (settings, prediction, performance-analytics, ai-intelligence, administration, auth) are untouched.

## 2. API Client

- [x] `apiClient` extended with typed methods — not duplicated, no second client created.
- [x] All requests use the existing `request<T>` helper and the relative `/api` base (`VITE_BIP_API_BASE_URL ?? "/api"`).
- [x] `SuccessEnvelope` unwrapping via `requestData`; pagination contract (`items/total/page/page_size`) preserved.
- [x] Collections larger than 100 items fetched completely via `fetchAllPages`.
- [x] Health endpoint and `HealthResponse` contract unchanged.

## 3. Hooks

- [x] Each migrated hook exposes: original fields (shapes unchanged), `isLoading`, `error`, `refresh`, `isEmpty`.
- [x] Mapping from API DTOs to feature types happens inside hooks only.
- [x] No `fetch()` calls in any component (verified by grep).
- [x] Loading state surfaces the existing `LoadingSkeleton` on the two dashboard pages; no spinners introduced.
- [x] Empty datasets render the existing `EmptyState` branches; no crashes on undefined data (hooks return empty arrays while loading).
- [x] Errors surface via the pages' existing error branches (`EmptyState` on the dashboards; empty state on interactive pages).

## 4. React Query

- [x] All data fetching goes through `useQuery` — no loaders, no raw promises in components.
- [x] Query keys centralized in `src/lib/queryKeys.ts`.
- [x] `staleTime: 30_000` on all data queries; global `retry: 1`, `refetchOnWindowFocus: false` from `QueryProvider`.
- [x] Cached per feature: dashboard pages cache a single composed query; explorers cache the source collections.

## 5. Backend Integrity

- [x] Zero backend changes: no endpoints, models, SQL, repositories, services, or routers touched.
- [x] API remains read-only (no DML introduced).
- [x] All consumed endpoints return 200 with the documented envelope shape through the dev proxy (see Verification Report).

## 6. UI Integrity

- [x] No pages, components, CSS, design tokens, theme, sidebar, header, routing, app shell, or providers modified.
- [x] No new pages added.
- [x] Hook return shapes preserved so pages compile and render unchanged (`tsc --noEmit` clean).

## 7. Verification Commands

- [x] `npm run lint:web` — passes (0 errors).
- [x] `npm run build:web` — passes; production bundle builds successfully.
- [x] Live smoke: API + vite dev server started; 11 hook endpoints verified 200 through the `/api` proxy.

## 8. Deliverables

- [x] Phase 18 Completion Report
- [x] Phase 18 Architecture Review
- [x] Phase 18 Acceptance Checklist
- [x] Phase 18 Verification Report
- [x] Phase 18 Technical Debt Report
- [x] Phase 18 Backward Compatibility Report

## Not in Scope (documented constraints)

- Per-battery/slot-level data, product catalog, per-record quality rows, and report schedules/history are not exposed by the Phase 17 API; those surfaces render the existing empty states (see Technical Debt Report, item 2).
- Phase 19 not started.
