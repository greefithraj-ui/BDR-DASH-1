# Phase 18.1 Completion Report

## Summary

Phase 18.1 refines the Phase 18 API integration: detail views now fetch dedicated backend endpoints, every API page has explicit refresh, loading, error (with Retry), and empty states, mock wording was removed from the nine live features, and React Query usage was consolidated behind a shared query layer so caches are reused across features. No backend changes, no design-system changes, no CSS changes, no routing changes, no layout redesigns.

## 1. Files Modified

**Added**
- `apps/web/src/lib/errors.ts` — `describeApiError(error)` maps failures to operator-facing messages (Unable to reach API / Database unavailable / Collector unavailable / Unable to load data). No raw exceptions leak to the UI.
- `apps/web/src/lib/useApiQueries.ts` — shared, stable-key query hooks: `useMetricsQuery`, `useAnalyticsSummaryQuery`, `useQualitySummaryQuery`, `usePerformanceSummaryQuery`, `useHealthQuery`, `useMachinesQuery`, `useRingsQuery`, `useTimelineQuery`, `useReportsQuery` (all `staleTime: 30_000`).
- `apps/web/src/components/feedback/ApiErrorState.tsx` — reusable error state (message + Retry) built from existing `EmptyState` and the `ds-button` class.

**Modified**
- `apps/web/src/lib/queryKeys.ts` — added `metrics.all`, `analyticsSummary.all`, `qualitySummary.all`, `performanceSummary.all`, `health.all`.
- Hooks (all 11): `useExecutiveDashboard`, `useBatteryIntelligenceDashboard`, `useAnalyticsHub`, `useProductAnalytics`, `useQualityAnalytics`, `useBatteryExplorer`, `useMachineExplorer`, `useTimeline`, `useReports`, `useBatteryDetail`, `useMachineDetail`.
- Pages (all 9): `ExecutiveDashboardPage`, `BatteryIntelligenceDashboardPage`, `AnalyticsHubPage`, `BatteryExplorerPage`, `MachineExplorerPage`, `TimelinePage`, `ProductAnalyticsPage`, `QualityAnalyticsPage`, `ReportsPage`.
- Detail components: `BatteryDetail`, `MachineDetail`, `DetailIdentityCard`, `DetailLifecycleTimeline`, `MachineStats`, `BatteryList`.
- Detail panels (badge wording only): `TimelineDetailPanel`, `QualityDetailPanel`, `ProductDetailPanel`, `ReportDetailPanel`, `InsightsPanel`.

## 2. Detail Hooks Updated

`useBatteryDetail` and `useMachineDetail` previously derived detail data synchronously from the list row. They now run real queries:

- `useBatteryDetail(record)` → `useQuery({ queryKey: queryKeys.rings.detail(id), queryFn: () => apiClient.getRing(id), enabled: id != "" })` against `GET /api/v1/rings/{id}`.
- `useMachineDetail(record)` → `useQuery({ queryKey: queryKeys.machines.detail(id), queryFn: () => apiClient.getMachine(id), enabled: id != "" })` against `GET /api/v1/machines/{id}`.

Behavior:
- Opening a detail view always issues a fresh server request (staleTime 30s; still cached within the window).
- While fetching, the panel renders instantly from the last known state (no blank screen) and shows a "Refreshing the latest state…" badge.
- On failure, the panel keeps rendering the cached state, shows a `Cached` badge with the classified message ("Unable to reach API", "Database unavailable", …), and a Retry button.
- The fetched DTO is re-mapped to the feature domain types inside the hook (state/tone/lifecycle mapping, timestamp formatting); components receive only the mapped `BatteryDetail`/`MachineDetail`.

## 3. Mock Wording Removed

All nine live features now use neutral, accurate wording:

- Page subtitles: "…using mock data" → "…from live collector and database data" (explorers, timeline, product, quality, reports); dashboards describe live backing data.
- Hero badges: `Mock Data` → `Live Data` on all nine pages and in-scope detail panels/cards.
- KPI helpers in `useExecutiveDashboard`/`useBatteryIntelligenceDashboard`: `Mock operational snapshot` → `Live operational snapshot`, `Mock heartbeat received` → `Heartbeat received`, etc.
- Lifecycle/decision notes in detail hooks: `Mock stage reached` → `Stage reached`, `Mock · 87%` → `Estimated · 87%`.
- `BAT-MOCK-*` ids → `BAT-*`; `{n} mock batteries` → `{n} batteries registered`.
- Intentional placeholders were preserved: `ChartContainer` placeholders, chart descriptions, `Placeholder` badges on chart sections, and the executive "Coming Soon" summary card.
- Out-of-scope features (settings, prediction, performance-analytics, ai-intelligence, administration) still show `Mock Data` because they remain mock-backed.

## 4. Refresh Implementation

Every page backed by React Query now exposes an explicit Refresh button in the page hero (and in the two detail views), wired to `refetch()` — no reload of the application:

- Dashboards/hub: `refresh = () => Promise.all(queries.map(q => q.refetch()))`.
- Explorers/timeline/reports/product/quality: `refresh = refetch` directly from the shared query.
- Detail views: `Refresh` re-fetches `GET /v1/rings/{id}` / `GET /v1/machines/{id}`.
- All refresh actions reuse existing query refetch logic; nothing is duplicated.

## 5. Error-State Improvements

- New `describeApiError` classifier: network failure → "Unable to reach API"; HTTP 500 → "Database unavailable"; 502/503/504 → "Collector unavailable"; everything else → "Unable to load data". Raw exceptions are never rendered.
- New `ApiErrorState` component (EmptyState + Retry button). All nine pages render it when their query fails — previously the dashboards showed a generic "Coming Soon" and the interactive pages silently showed empty states.
- Detail views degrade gracefully: cached content + `Cached` badge + classified message + Retry.

## 6. Loading-State Improvements

- Dashboards kept `LoadingSkeleton`.
- All seven interactive pages now render `LoadingSkeleton` on first load (previously they showed the empty state during the initial fetch).
- Detail views never blank: they render cached state with a "Refreshing" badge while the detail query runs.
- Every in-scope surface now has the four states: loading (skeleton), success (content), error (message + Retry), empty (existing `EmptyState` branches).

## 7. React Query Optimizations

- **Cache reuse across features**: shared query hooks with stable keys (`metrics.all`, `machines.all`, `rings.all`, …). `/v1/metrics`, `/v1/machines`, `/v1/rings`, `/v1/analytics/summary`, `/v1/quality/summary` are fetched once per 30s window and shared by all consumers (e.g. Battery Intelligence + Battery Explorer share the rings cache; Machine Explorer + Quality + Analytics Hub share the machines cache).
- **Duplicate request removal**: executive dashboard no longer fetches `/v1/machines` (its machines-online KPI comes from MT-2), dropping one request per load.
- **Consistent freshness**: every data query uses the single `DATA_STALE_TIME = 30_000` constant; gcTime/global options unchanged.
- **Stable keys**: all keys are static-typed factories in `queryKeys.ts`; no inline key literals in features.
- **No unnecessary refetches**: shared keys + staleTime mean re-mounting a consumer within the window does not refetch.

## 8. Dead-Code Cleanup

- Removed unused imports after the migration (`apiClient`/`fetchAllPages`/`useQuery`/`queryKeys` from feature hooks, `EmptyState` from `ExecutiveDashboardPage`, `MachineStatus` from `useMachineExplorer`).
- Removed unnecessary type assertions (`as MachineStatus[]` in `useMachineExplorer`; `as TimelineEventType[]` in `useTimeline` via a generic `unique` helper).
- Added a guarded `toTimelineEventType` conversion (unknown types fall back to `Observed`).
- Verified zero `any` / `as any` / `as unknown` / `@ts-ignore` across `src` (grep).
- Kept: `reports.mock.ts` `formatDuration` (still imported by five report components — shared utility still in use); out-of-scope feature mocks; shared `format.ts` utilities.
- No remaining imports of any of the eight Phase 18 deleted mock providers (grep-verified).
