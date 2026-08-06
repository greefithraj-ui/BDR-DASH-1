# Phase 6 Architecture Review

## Overview

Phase 6 adds the Analytics Hub as a self-contained feature under `apps/web/src/features/analytics-hub/`. It follows the established feature-folder pattern (types, mock provider, hook, presentational components, token-based CSS) and introduces no changes to the platform foundation.

## Layering

```
AnalyticsHubPage (composition / route target)
 ├── useAnalyticsHub             (memoized mock datasets)
 ├── components/KpiRow           (Executive KPI summary via MetricCard)
 ├── components/AnalyticsCardGrid (category grid)
 │    └── AnalyticsCard          (title, description, status, metrics, mini chart, actions)
 ├── components/InsightsPanel    (Recent Insights)
 ├── components/AlertsPanel      (Top Alerts)
 ├── components/QuickNavSection  (Quick Navigation)
 └── components/ChartsArea       (placeholder chart area, scroll target)
analyticsHub.types.ts   (shared types)
analyticsHub.mock.ts    (deterministic mock source)
analyticsHub.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `useAnalyticsHub` memoizes `getMockAnalyticsHub()` once; all six datasets flow as props to presentational components.
2. Navigation is delegated to the page: `useNavigate` is called once in `AnalyticsHubPage` and passed down as `onPrimaryAction`/`onNavigate` callbacks, keeping components free of router coupling.
3. The secondary action ("View Charts") is wired to a `useRef` on the charts area and smooth-scrolls to it.

## Component Principles

- **Container/presentational split**: only `AnalyticsHubPage` holds routing/scroll logic; every child is props-driven and re-usable.
- **Single responsibility**: 7 components, each rendering one dashboard region.
- **Stable keys**: KPIs, cards, insights, alerts, nav items, and charts all keyed by id.
- **Tone system**: metric/status/severity/delta tones map onto the design-system Badge/MetricCard tone contracts.

## State Management

- No component state beyond the memoized mock data and the charts scroll ref — appropriate for a read-only summary dashboard. No global store, context, or URL sync.

## Styling

- `analyticsHub.css` uses only design tokens; dark theme inherited automatically via token swaps.
- Class prefix `analytics-hub__` prevents collisions with other features.
- Breakpoints: ≤1180px collapses KPI row, panel grid, and chart grid to single column; ≤720px goes fully single-column with stacked headers.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–5. `routes.ts` already contained the `/analytics` entry; no config change was needed.
- Primary actions navigate to category routes (`/quality`, `/reliability`, etc.) that remain `PlaceholderPage` until later phases; `/machine-explorer` navigation targets the live Machine Explorer.

## Mock Strategy

- The mock module is the single contact point for fake data. KPI/card/insight/alert values are intentionally static and labeled Mock Data. Replacing with an API later only requires changing `getMockAnalyticsHub` (or the hook), leaving components intact.

## Dependencies Added

- None. Phase 6 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `ChartContainer`), the existing ECharts infrastructure, and `react-router-dom` (already a project dependency).
