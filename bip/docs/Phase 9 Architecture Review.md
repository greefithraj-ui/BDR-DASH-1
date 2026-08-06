# Phase 9 Architecture Review

## Overview

Phase 9 adds the Performance Analytics page as a self-contained feature under `apps/web/src/features/performance-analytics/`. It follows the established feature-folder pattern (types, mock provider, hook, presentational components, token-based CSS) and introduces no changes to the platform foundation.

## Layering

```
PerformanceAnalyticsPage (composition / route target)
 ├── usePerformanceAnalytics          (mock data + filter state + drill-down state)
 ├── components/PerformanceToolbar    (search + machine/product/firmware/date filters)
 ├── components/PerformanceKpiRow     (KPI summary via MetricCard)
 ├── components/DistributionPanel × 2 (Cycle / Utilization distributions)
 ├── components/PerformanceTrendPlaceholder  (3 ChartContainer placeholders + recent-points table)
 ├── components/PerformanceComparison × 2    (Machine Comparison / Product Performance)
 ├── components/PerformanceTable      (record table, row click → detail)
 └── components/PerformanceDetailPanel (drill-down view, replaces page body)
performanceAnalytics.types.ts   (shared types)
performanceAnalytics.mock.ts    (deterministic mock source)
performanceAnalytics.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `usePerformanceAnalytics` memoizes `getMockPerformanceAnalytics()` once. Records flow into a memoized filter pipeline: `matchesFilters` checks search + exact machine/product/firmware matches and date-field bounds; `deriveOptions` builds select options from records.
2. Aggregates (kpis, cycleDistribution, utilizationDistribution, trend, machineComparisons, productComparisons, charts) are computed once from all records in the mock and flow as props to presentational components.
3. Drill-down is local UI state: `openDetail(record)` sets `selected`; the page renders `PerformanceDetailPanel` instead of the list view; `closeDetail` returns.

## Component Principles

- **Container/presentational split**: only `PerformanceAnalyticsPage` and `usePerformanceAnalytics` hold state/composition; every child is props-driven and re-usable.
- **Single responsibility**: 7 components, each rendering one dashboard region. `DistributionPanel` and `PerformanceComparison` are generic and reused for two datasets each.
- **Stable keys**: KPIs, records, distribution rows, trend points, and comparisons all keyed by id.
- **Tone system**: status, distribution, and comparison tones map onto the design-system Badge/MetricCard tone contracts.

## State Management

- `useState` only: filter object and the selected record for drill-down. No global store, context, or URL sync. Filtering is computed on every render via memoized `filteredRecords`.

## Styling

- `performanceAnalytics.css` uses only design tokens; dark theme inherited automatically via token swaps.
- Class prefix `performance-analytics__` / `performance-analytics-detail__` prevents collisions with other features.
- Breakpoints: ≤1180px collapses KPI row, panel grids, chart grid, comparison grids, and detail metric grid to 2 columns; ≤720px goes fully single-column with stacked headers.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–8. `routes.ts` already contained the `/performance` entry; no config change was needed.
- `/performance` previously fell through to `PlaceholderPage`; it now renders `PerformanceAnalyticsPage`.

## Mock Strategy

- The mock module is the single contact point for fake data. 560 records are generated deterministically from machine/product/date seeds; throughput is scaled by a machine base so machine-level comparisons are meaningful. KPI, distribution, trend, and comparison aggregates are derived from those records and labeled Mock Data in the UI. Replacing with an API later only requires changing `getMockPerformanceAnalytics` (or the hook), leaving components intact.

## Dependencies Added

- None. Phase 9 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`) and `react` hooks.
