# Phase 3 Architecture Review

## Overview

Phase 3 adds the Battery Explorer as a self-contained feature under `apps/web/src/features/battery-explorer/`. It follows the same feature-folder convention used by the Executive and Battery Intelligence dashboards and introduces no changes to the platform foundation.

## Layering

```
BatteryExplorerPage (composition / route target)
 ├── useBatteryExplorer        (state: filters, sort, page, selection; derived: options, filtered, paged)
 ├── useBatteryDetail          (memoized mock detail for selected record)
 ├── components/ExplorerToolbar      (presentational, props-only)
 ├── components/ActiveFilterChips    (presentational, props-only)
 ├── components/BatteryExplorerTable (presentational, props-only)
 ├── components/ExplorerPagination   (presentational, props-only)
 └── components/BatteryDetail        (detail composition)
      ├── DetailIdentityCard
      ├── DetailCurrentContext
      ├── DetailLifecycleTimeline
      ├── DetailRecentEvents
      └── DetailPlaceholderCharts
batteryExplorer.types.ts   (shared types)
batteryExplorer.mock.ts    (deterministic mock source, single import point)
batteryExplorer.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `getMockBatteryRecords()` is resolved once via `useMemo` (deterministic module-level constant).
2. `useBatteryExplorer` derives `options` (unique products/machines/slots/states/firmwares) and the filtered+sorted list via `useMemo` keyed on `[allRecords, filters, sort]`.
3. Pagination slices the filtered list (`PAGE_SIZE = 10`); `safePage` clamps to the computed page count so filters that shrink results never land on an empty page.
4. Row selection stores the `BatteryRecord`; `useBatteryDetail` memoizes the full mock detail; the page switches to `BatteryDetail` while `selected` is set.

## Component Principles

- **Container/presentational split**: only `BatteryExplorerPage` (via hooks) holds state; every child component receives props and emits callbacks. This keeps each component unit-testable and re-usable.
- **Single responsibility**: 12 subcomponents each render one concern; the toolbar's internal `TextField`/`SelectField` helpers keep markup DRY.
- **Stable keys**: records keyed by `id`; columns keyed by column name; stages/events keyed by generated ids.

## State Management

- All state is local React state (`useState`) inside `useBatteryExplorer`. No global store, context, or URL sync was added — consistent with the platform's current approach and adequate for a mock-only page.
- `updateFilters`/`toggleSort`/`removeFilter` always reset to page 1; `changePage` clamps.

## Styling

- `batteryExplorer.css` uses only design tokens; the dark theme is inherited automatically via `:root[data-theme="dark"]` token swaps.
- Class prefix `battery-explorer__` (feature) and `battery-explorer-detail__` (detail) prevent collisions with existing styles.
- Breakpoints: desktop (5-col filters / 2-col detail), ≤1180px (2-col filters / 1-col detail), ≤720px (1-col everywhere, stacked hero).

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–2. `routes.ts` already contained the `/battery-explorer` entry; no config change was needed.

## Mock Strategy

- The mock module is the single point of contact for fake data. `getMockBatteryDetail(record)` derives all detail panels from the record, so no external mock store is required. Replacing mocks with an API later only requires changing `getMockBatteryRecords`/`getMockBatteryDetail` (or the two hooks), leaving the components intact.

## Dependencies Added

- None. Phase 3 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`) and the existing ECharts infrastructure.
