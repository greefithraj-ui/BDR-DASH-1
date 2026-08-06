# Phase 8 Architecture Review

## Overview

Phase 8 adds the Quality Analytics page as a self-contained feature under `apps/web/src/features/quality-analytics/`. It follows the established feature-folder pattern (types, mock provider, hook, presentational components, token-based CSS) and introduces no changes to the platform foundation.

## Layering

```
QualityAnalyticsPage (composition / route target)
 ├── useQualityAnalytics            (mock data + filter state + drill-down state)
 ├── components/QualityToolbar      (search + product/machine/firmware/result/date filters)
 ├── components/QualityKpiRow       (KPI summary via MetricCard)
 ├── components/DefectDistributionPanel
 ├── components/FailureCategoriesPanel
 ├── components/QualityTrendPlaceholder  (3 ChartContainer placeholders + recent-points table)
 ├── components/QualityComparison × 2    (Product / Machine quality comparisons)
 ├── components/QualityTable        (record table, row click → detail)
 └── components/QualityDetailPanel  (drill-down view, replaces page body)
qualityAnalytics.types.ts   (shared types)
qualityAnalytics.mock.ts    (deterministic mock source)
qualityAnalytics.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `useQualityAnalytics` memoizes `getMockQualityAnalytics()` once. Records flow into a memoized filter pipeline: `matchesFilters` checks search + exact product/machine/firmware/result matches and date-field bounds; `deriveOptions` builds select options from records.
2. Aggregates (kpis, defectDistribution, failureCategories, trend, productComparisons, machineComparisons, charts) are computed once from all records in the mock and flow as props to presentational components.
3. Drill-down is local UI state: `openDetail(record)` sets `selected`; the page renders `QualityDetailPanel` instead of the list view; `closeDetail` returns.

## Component Principles

- **Container/presentational split**: only `QualityAnalyticsPage` and `useQualityAnalytics` hold state/composition; every child is props-driven and re-usable.
- **Single responsibility**: 8 components, each rendering one dashboard region.
- **Stable keys**: KPIs, records, defect rows, failure rows, trend points, comparisons, and charts all keyed by id.
- **Tone system**: result, status, severity, defect, and comparison tones map onto the design-system Badge/MetricCard tone contracts.

## State Management

- `useState` only: filter object and the selected record for drill-down. No global store, context, or URL sync. Filtering is computed on every render via memoized `filteredRecords`.

## Styling

- `qualityAnalytics.css` uses only design tokens; dark theme inherited automatically via token swaps.
- Class prefix `quality-analytics__` / `quality-analytics-detail__` prevents collisions with other features.
- Breakpoints: ≤1180px collapses KPI row, panel grids, chart grid, comparison grids, and detail metric grid to 2 columns; ≤720px goes fully single-column with stacked headers.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–7. `routes.ts` already contained the `/quality` entry; no config change was needed.
- `/quality` previously fell through to `PlaceholderPage`; it now renders `QualityAnalyticsPage`.

## Mock Strategy

- The mock module is the single contact point for fake data. 560 records are generated deterministically from product/machine/date seeds; KPI, defect, trend, and comparison aggregates are derived from those records and labeled Mock Data in the UI. Replacing with an API later only requires changing `getMockQualityAnalytics` (or the hook), leaving components intact.

## Dependencies Added

- None. Phase 8 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`) and `react` hooks.
