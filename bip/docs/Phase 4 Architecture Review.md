# Phase 4 Architecture Review

## Overview

Phase 4 adds the Machine Explorer as a self-contained feature under `apps/web/src/features/machine-explorer/`. It mirrors the Phase 3 Battery Explorer architecture (feature folder, types, mock provider, hooks, presentational components, token-based CSS) and introduces no changes to the platform foundation.

## Layering

```
MachineExplorerPage (composition / route target)
 ├── useMachineExplorer      (state: filters, sort, selection; derived: filtered/sorted machines)
 ├── useMachineDetail        (memoized mock detail for selected machine)
 ├── components/MachineSearchToolbar  (presentational, props-only)
 ├── components/MachineCard           (presentational card; exports StatusIndicator)
 ├── components/MachineDetail         (detail composition)
 │    ├── MachineInfoCard
 │    ├── MachineStats
 │    ├── SlotOverview
 │    ├── HealthPanel
 │    ├── TimelinePlaceholder
 │    ├── BatteryList
 │    ├── RecentEvents
 │    └── ChartsPlaceholder
machineExplorer.types.ts   (shared types)
machineExplorer.mock.ts    (deterministic mock source, single import point)
machineExplorer.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `getMockMachineRecords()` resolves once via `useMemo` (module-level constant, deterministic).
2. `useMachineExplorer` derives `options.statuses` and the filtered+sorted list via `useMemo` keyed on `[allMachines, filters, sort]`.
3. Selection stores the `MachineRecord`; `useMachineDetail` memoizes the full mock detail; the page switches to `MachineDetail` while `selected` is set.
4. Every detail panel derives from the record via `getMockMachineDetail`, so no external mock store is required.

## Component Principles

- **Container/presentational split**: only `MachineExplorerPage` (via hooks) holds state; every child is props-driven and unit-testable.
- **Single responsibility**: 12 components, each rendering one concern. `StatusIndicator` is shared between card and detail (imported from `MachineCard`).
- **Accessibility**: cards are focusable (`tabIndex={0}`) and open detail on Enter/Space, not just click.
- **Stable keys**: machines keyed by `id`; slots by slot label; batteries/events/stages by generated ids.

## State Management

- Local React state only inside `useMachineExplorer`. No global store, context, or URL sync — consistent with the platform's current approach and adequate for mock-only scope.
- `updateFilters`/`toggleSort` mutate their slice only; no pagination needed (8 machines).

## Styling

- `machineExplorer.css` uses only design tokens; the dark theme is inherited automatically via token swaps.
- Class prefixes `machine-explorer__` and `machine-explorer-detail__` prevent collisions with Battery Explorer and existing styles.
- Breakpoints: ≤1180px collapses toolbar/detail grids to single column; ≤720px goes fully single-column with stacked headers and rows.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–3. `routes.ts` already contained the `/machine-explorer` entry; no config change was needed.

## Mock Strategy

- The mock module is the single contact point for fake data; `getMockMachineDetail(record)` derives all detail panels from the record. Replacing mocks with an API later only requires changing `getMockMachineRecords`/`getMockMachineDetail` (or the two hooks), leaving components intact.
- Serial-number and state families are shared with Battery Explorer's mock so cross-feature mock data stays visually consistent.

## Dependencies Added

- None. Phase 4 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`) and the existing ECharts infrastructure.
