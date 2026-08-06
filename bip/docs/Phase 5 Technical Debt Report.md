# Phase 5 Technical Debt Report

## Items Introduced in Phase 5

### 1. Group Pagination Semantics
- Pagination operates on groups (5 groups/page), not individual events. A single group can contain many events, so page sizes are uneven.
- **Impact**: Users may see large group sections; counts ("Showing groups X–Y of Z") differ from the explorer features' event/page semantics.
- **Deferred**: Acceptable for a timeline; revisit if a flat event pagination mode is requested.

### 2. Mock Event Sources Are Static
- Events derive purely from `index` in `timeline.mock.ts`; they are not generated from the battery/machine mocks, so timeline batteries/machines are visually consistent by convention, not by construction.
- **Impact**: Cross-feature mock data can drift (e.g., a timeline battery that Machine Explorer wouldn't place on that machine).
- **Deferred**: Shared mock factory that generates batteries → machines → events from one source of truth.

### 3. Filtering/Grouping Logic Not Unit-Tested
- `matchesFilters`, `groupEvents`, and pagination math live inside `useTimeline` with no test harness (the repo has no test runner configured).
- **Impact**: Regressions in search/filter/group/sort behavior would go uncaught.
- **Deferred**: Extract pure functions into `timeline.logic.ts` and add tests once a test framework (Vitest) is introduced.

### 4. State Change Panel Is a Placeholder
- The Previous/Current state transition is static mock text derived from a type map; no real transition engine exists.
- **Impact**: None functionally; intentional scope boundary (labeled Placeholder).

### 5. Feature Stylesheet Growth
- `timeline.css` (~560 lines) duplicates toolbar, button, card, table-like row, and section-header patterns already present in the explorer stylesheets.
- **Impact**: Cross-feature duplication keeps growing with each phase.
- **Deferred**: Promote shared primitives (toolbar fields, segmented control, pagination, section header) into the design system.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (`966.86 kB`, ~318 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state (filters, sort, group-by, page).

## Recommendations

- Introduce Vitest + a small suite for `matchesFilters`/`groupEvents`/pagination across all explorer/timeline features.
- Build a shared mock factory so batteries, machines, and events are generated from a single deterministic source.
- Promote repeated toolbar/pagination/section-header styles into the design system before adding more phases.
