# Phase 18.1 Acceptance Checklist

## 1. Detail API Hooks (Task 1)

- [x] `useBatteryDetail` fetches `GET /api/v1/rings/{id}` via React Query (`queryKeys.rings.detail`), enabled only when a record is selected.
- [x] `useMachineDetail` fetches `GET /api/v1/machines/{id}` via React Query (`queryKeys.machines.detail`).
- [x] Detail pages always request the latest server state on open (fresh query, 30s stale window).
- [x] Loading: detail renders instantly from last-known state with a "Refreshing" badge — no blank screens.
- [x] Error: detail shows cached content + `Cached` badge + classified message + Retry.
- [x] Empty: detail never blanks; list-level empty states unchanged.
- [x] Mapping (state/tone/lifecycle/timestamps) stays inside the hooks; components receive mapped domain types only.

## 2. Mock Wording Removed (Task 2)

- [x] No `Mock Data` / `mock data` wording remains in the nine live features (pages, panels, cards, hook helper text, detail views) — grep-verified.
- [x] Neutral wording used: `Live Data`, "live collector and database data", "Live operational snapshot", "Heartbeat received", "Estimated · 87%", "batteries registered".
- [x] Intentional placeholders preserved: ChartContainer placeholders, chart descriptions, `Placeholder` badges, executive "Coming Soon".
- [x] Out-of-scope features keep their honest `Mock Data` badges (still mock-backed).

## 3. Manual Refresh (Task 3)

- [x] All nine pages expose a Refresh button in the hero wired to query `refetch()` — no app reload.
- [x] Both detail views expose Refresh for their detail query.
- [x] Refresh reuses existing query logic; no duplicated fetch code.

## 4. Error States (Task 4)

- [x] All API pages render an error state with a meaningful message and a Retry button on failure.
- [x] Messages classified: "Unable to reach API" (network), "Database unavailable" (500), "Collector unavailable" (502/503/504), "Unable to load data" (other).
- [x] Raw exceptions are never exposed to the UI (`describeApiError` is the only message source).
- [x] Dashboards no longer show a misleading "Coming Soon" on error.

## 5. Loading States (Task 5)

- [x] All nine pages render `LoadingSkeleton` on first load.
- [x] Every in-scope API surface has loading / success / error / empty states — no blank screens.

## 6. Query Optimization (Task 6)

- [x] Duplicate requests avoided: shared query hooks (`lib/useApiQueries.ts`) with stable keys; collections fetched once per 30s window across features.
- [x] Executive dashboard dropped its unused `/v1/machines` fetch.
- [x] Query keys are stable, typed factories in `queryKeys.ts`.
- [x] `staleTime` consistent (single `DATA_STALE_TIME = 30_000` constant); no unnecessary refetches on remount within the window.

## 7. Type Safety (Task 7)

- [x] Zero `any` / `as any` / `as unknown` / `@ts-ignore` in `src` (grep-verified).
- [x] Unnecessary casts removed (`as MachineStatus[]`, `as TimelineEventType[]`).
- [x] Unknown timeline types guarded via `toTimelineEventType` (fallback `Observed`).
- [x] All API responses strongly typed via shared DTOs; `tsc --noEmit` clean.

## 8. Cleanup (Task 8)

- [x] Unused imports removed (hooks, pages) after the migration.
- [x] No references to the eight Phase 18 deleted mock providers.
- [x] Shared utilities kept: `reports.mock.ts` `formatDuration` (5 consumers), `lib/format.ts`.
- [x] Out-of-scope feature mocks untouched.

## 9. Verification Commands

- [x] `npm run lint:web` — PASS (0 errors).
- [x] `npm run build:web` — PASS (production build emitted).
- [x] Live smoke: API + vite proxy — 12/12 endpoints 200, including both detail endpoints (`/v1/machines/aqc-04`, `/v1/rings/C0:11:B8:E1:2E:E5`).

## 10. Deliverables

- [x] Phase 18.1 Completion Report (files modified, detail hooks, wording, refresh, error/loading, query optimization, cleanup)
- [x] Phase 18.1 Verification Report
- [x] Phase 18.1 Backward Compatibility Report
- [x] Phase 18.1 Technical Debt Report
- [x] Phase 18.1 Acceptance Checklist

## Not in Scope (documented constraints)

- No backend changes; no design-system, CSS, theme, token, routing, or layout changes.
- Slot-level, product-catalog, per-record quality, and report-history data remain absent from the API (see Technical Debt Report).
- Phase 19 not started — stopped for review.
