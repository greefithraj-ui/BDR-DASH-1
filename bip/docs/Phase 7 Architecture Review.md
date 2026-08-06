# Phase 7 Architecture Review

## Overview

Phase 7 adds the Product Analytics page as a self-contained feature under `apps/web/src/features/product-analytics/`. It follows the established feature-folder pattern (types, mock provider, hook, presentational components, token-based CSS) and introduces no changes to the platform foundation.

## Layering

```
ProductAnalyticsPage (composition / route target)
 ├── useProductAnalytics            (mock data + filter state + drill-down state)
 ├── components/ProductToolbar      (search + product/firmware/machine/lifecycle/date filters)
 ├── components/ProductKpiRow       (KPI summary via MetricCard)
 ├── components/FirmwareSummaryPanel
 ├── components/ProductDistributionPanel
 ├── components/FailureDistributionPanel
 ├── components/LifecycleDistributionPanel
 ├── components/ProductHealthSummary
 ├── components/ComparisonCard × n  (Product Comparison Cards)
 ├── components/ProductTable        (catalog table, row click → detail)
 ├── components/ProductDetailPanel  (drill-down view, replaces page body)
 └── components/ChartsPlaceholder   (ChartContainer placeholders)
productAnalytics.types.ts   (shared types)
productAnalytics.mock.ts    (deterministic mock source)
productAnalytics.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `useProductAnalytics` memoizes `getMockProductAnalytics()` once. Products flow into a memoized filter pipeline: `matchesFilters` checks search + exact product/firmware/machine/lifecycle matches and date-field bounds; `deriveOptions` builds select options from products.
2. All datasets (kpis, comparisonCards, distribution, failureDistribution, fleetLifecycle, fleetFirmware, charts) flow as props to presentational components.
3. Drill-down is local UI state: `openDetail(product)` sets `selected`; the page renders `ProductDetailPanel` instead of the list view; `closeDetail` returns. The comparison card for the selected product is looked up by id and passed to the detail view.

## Component Principles

- **Container/presentational split**: only `ProductAnalyticsPage` and `useProductAnalytics` hold state/routing composition; every child is props-driven and re-usable.
- **Single responsibility**: 11 components, each rendering one dashboard region.
- **Stable keys**: KPIs, products, distribution rows, failure rows, lifecycle rows, comparison cards, and charts all keyed by id.
- **Tone system**: status, failure, lifecycle, and comparison tones map onto the design-system Badge/MetricCard tone contracts.

## State Management

- `useState` only: filter object and the selected product for drill-down. No global store, context, or URL sync. Filtering is computed on every render via memoized `filteredProducts`.

## Styling

- `productAnalytics.css` uses only design tokens; dark theme inherited automatically via token swaps.
- Class prefix `product-analytics__` / `product-analytics-detail__` prevents collisions with other features.
- Breakpoints: ≤1180px collapses KPI row, panel grids, health/comparison grid, chart grid, and detail grids to single column; ≤720px goes fully single-column with stacked headers and single-column metric grids.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–6. `routes.ts` already contained the `/production` entry; no config change was needed.
- `/production` previously fell through to `PlaceholderPage`; it now renders `ProductAnalyticsPage`.

## Mock Strategy

- The mock module is the single contact point for fake data. Product records, KPI aggregates, comparison cards, and distributions are derived deterministically from the 5-product list, and labeled Mock Data in the UI. Replacing with an API later only requires changing `getMockProductAnalytics` (or the hook), leaving components intact.

## Dependencies Added

- None. Phase 7 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`) and `react` hooks.
