# Phase 18 Completion Report

## Scope Completed

Phase 18 connected the frontend to the Phase 17 database-backed backend: the nine mock-powered feature providers in `bip/apps/web` were replaced with **React Query hooks that consume the real `/api/v1` endpoints through the existing `apiClient`**. No UI, component, page, router, CSS, or backend code was modified. All mock data modules for the nine in-scope features were removed; shared mock utilities still used elsewhere were retained.

## Data Source Mapping

| Feature | Hook(s) | API endpoints consumed | Mock provider removed |
|---|---|---|---|
| Executive Dashboard | `useExecutiveDashboard` | `/v1/metrics`, `/v1/analytics/summary`, `/v1/quality/summary`, `/v1/machines`, `/health` | `executiveDashboard.mock.ts` |
| Battery Intelligence Dashboard | `useBatteryIntelligenceDashboard` | `/v1/metrics`, `/v1/analytics/summary`, `/v1/quality/summary`, `/v1/machines`, `/v1/rings`, `/v1/timeline`, `/health` | `batteryIntelligence.mock.ts` |
| Battery Explorer | `useBatteryExplorer`, `useBatteryDetail` | `/v1/rings` (all pages) | `batteryExplorer.mock.ts` |
| Machine Explorer | `useMachineExplorer`, `useMachineDetail` | `/v1/machines` | `machineExplorer.mock.ts` |
| Timeline | `useTimeline` | `/v1/timeline` (all pages) | `timeline.mock.ts` |
| Analytics Hub | `useAnalyticsHub` | `/v1/metrics`, `/v1/analytics/summary`, `/v1/quality/summary`, `/v1/performance/summary`, `/v1/machines`, `/v1/rings` | `analyticsHub.mock.ts` |
| Product Analytics | `useProductAnalytics` | `/v1/quality/summary`, `/v1/analytics/summary`, `/v1/machines` | `productAnalytics.mock.ts` |
| Quality Analytics | `useQualityAnalytics` | `/v1/quality/summary`, `/v1/machines` | `qualityAnalytics.mock.ts` |
| Reports | `useReports` | `/v1/reports` (all pages) | `reports.mock.ts` (reduced to `formatDuration`) |

## Files Modified

### New
- `bip/apps/web/src/lib/queryKeys.ts` — typed React Query key factories per feature.
- `bip/apps/web/src/lib/format.ts` — `formatDateTime`, `formatDate`, `formatTime`, `toDisplayCount`.

### Extended
- `bip/apps/web/src/lib/apiClient.ts` — added `SuccessEnvelope`, `PaginatedResponse`, `ApiQuery`, typed DTOs (Machine, Ring, ReportSummary, TimelineEvent, Metric, Analytics/Quality/Performance summary), `buildQuery`, `requestData` (envelope unwrap), `fetchAllPages` (multi-page fetch for >100-item collections), and typed methods: `getMachines`, `getMachine`, `getRings`, `getRing`, `getReports`, `getTimelineEvents`, `getMetrics`, `getAnalyticsSummary`, `getQualitySummary`, `getPerformanceSummary`. Existing `health()` unchanged.

### Rewritten (mock provider → API hook, return shapes preserved)
- `bip/apps/web/src/features/executive-dashboard/useExecutiveDashboard.ts`
- `bip/apps/web/src/features/battery-intelligence-dashboard/useBatteryIntelligenceDashboard.ts`
- `bip/apps/web/src/features/battery-explorer/useBatteryExplorer.ts`, `useBatteryDetail.ts`
- `bip/apps/web/src/features/machine-explorer/useMachineExplorer.ts`, `useMachineDetail.ts`
- `bip/apps/web/src/features/timeline/useTimeline.ts`
- `bip/apps/web/src/features/analytics-hub/useAnalyticsHub.ts`
- `bip/apps/web/src/features/product-analytics/useProductAnalytics.ts`
- `bip/apps/web/src/features/quality-analytics/useQualityAnalytics.ts`
- `bip/apps/web/src/features/reports/useReports.ts`

### Deleted
- 8 feature mock modules (listed above). `bip/apps/web/src/features/reports/reports.mock.ts` retained with only `formatDuration` (still imported by five report components).

## Hook Contract

Every migrated hook now exposes, alongside its original fields: `isLoading` (first-load, via `isPending && isFetching`), `error: Error | null`, `refresh` (React Query `refetch`), and `isEmpty`. All queries run through `useQuery` with a `staleTime` of 30s, `retry: 1` and `refetchOnWindowFocus: false` inherited from the existing `QueryProvider`. No `fetch()` appears in any component; all mapping is performed inside the hooks.

## Data Fidelity Constraints (Documented)

The Phase 17 backend exposes aggregates, not slot-level or product-level records. The hooks therefore surface live aggregates and map them to the existing feature types:
- **Battery Explorer** rows are ring aggregates (ring MAC as identifier, slot/product/machine/firmware columns empty until a slot-level endpoint exists).
- **Machine Explorer** rows carry live health score, firmware, status, and last-seen; slot-count fields are 0 (not exposed by `/v1/machines`).
- **Product Analytics** has no product dimension in the API; the page shows the existing empty state with fleet-level KPIs and a real firmware distribution from `/v1/machines`.
- **Quality Analytics** KPIs come from `/v1/quality/summary`; the per-record table shows the existing empty state; machine comparisons are derived from live machine health.
- **Timeline** is live from `bic.ring_events` (currently empty until collectors emit events); battery/slot fields are empty until the event source carries them.
- **Reports** lists the live per-machine "Ring Snapshot" reports from `/v1/reports`; schedules/history/previews are not exposed by the API and render empty.

See the **Verification Report** and **Technical Debt Report** for the full constraint list.

## Explicitly Not Implemented

- No backend changes (endpoints, models, SQL, repositories, services, routers).
- No UI changes (pages, components, CSS, tokens, theme, sidebar, header, routing, providers, charts).
- No new pages or new API client — `apiClient` was extended, not duplicated.
- Out-of-scope features (settings, prediction, performance-analytics, ai-intelligence, administration, auth) remain mock-backed and untouched.
- No Phase 19 work was started.
