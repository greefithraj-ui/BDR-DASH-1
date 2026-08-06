# Phase 5 Architecture Review

## Overview

Phase 5 adds the Timeline as a self-contained feature under `apps/web/src/features/timeline/`. It follows the same feature-folder pattern established in Phases 3–4 (types, mock provider, hook, presentational components, token-based CSS) and introduces no changes to the platform foundation.

## Layering

```
TimelinePage (composition / route target)
 ├── useTimeline             (state: filters, sort, groupBy, page, selection; derived: filtered/sorted events, groups)
 ├── components/TimelineToolbar        (search, filters, sort, group-by — presentational)
 ├── components/TimelineGroupSection   (group header + event cards; exports formatDateLabel)
 ├── components/TimelineEventCard      (presentational event card)
 ├── components/TimelinePagination     (group pagination)
 ├── components/TimelineDetailPanel    (event detail composition)
 │    ├── Event Information (MetricCard grid)
 │    ├── State Change panel
 │    ├── Metadata list
 │    └── TimelineChartsPlaceholder
timeline.types.ts   (shared types)
timeline.mock.ts    (deterministic mock source, single import point)
timeline.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `getMockTimelineEvents()` resolves once via `useMemo` (module-level constant, deterministic).
2. `useTimeline` derives `options` (machines, batteries, event types) and the filtered+sorted event list via `useMemo` keyed on `[allEvents, filters, sort]`.
3. Events are grouped (`groupEvents`) by date/machine/battery; the group key is used for ordering (direction-aware) and as the React key.
4. Pagination slices groups (`PAGE_SIZE = 5`); `safePage` clamps so filter/group changes never land on an empty page.
5. Selecting an event sets `selected`; the page swaps to `TimelineDetailPanel` (the event itself is the detail, no second lookup required).

## Component Principles

- **Container/presentational split**: only `TimelinePage` (via `useTimeline`) holds state; every child is props-driven and unit-testable.
- **Single responsibility**: 6 components, each rendering one concern; the detail panel composes simple internal sections.
- **Accessibility**: event cards are focusable and open detail on Enter/Space, not just click; group-by is a labeled `role="group"` segmented control.
- **Stable keys**: events keyed by `id`; groups by `key`.

## State Management

- Local React state only inside `useTimeline`. No global store, context, or URL sync — consistent with the platform's current approach and adequate for mock-only scope.
- All filter/group/sort changes reset to page 1; `changePage` clamps.

## Styling

- `timeline.css` uses only design tokens; dark theme inherited automatically via token swaps.
- Class prefixes `timeline__` and `timeline-detail__` prevent collisions with other features.
- Breakpoints: ≤1180px collapses filter grids and charts to single column; ≤720px goes fully single-column with stacked heroes/headers, vertical state-change arrow, and column layout for event cards.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–4. `routes.ts` already contained the `/timeline` entry; no config change was needed.

## Mock Strategy

- The mock module is the single contact point for fake events; the serial/state/machine families are consistent with the Battery and Machine Explorer mocks so the platform feels cohesive. Replacing mocks with an API later only requires changing `getMockTimelineEvents` (or the hook), leaving components intact.

## Dependencies Added

- None. Phase 5 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`) and the existing ECharts infrastructure.
