# Phase 4 Technical Debt Report

## Items Introduced in Phase 4

### 1. Mock Data Duplication Across Features
- `machineExplorer.mock.ts` duplicates the serial format, state list, and state→tone mapping already present in `batteryExplorer.mock.ts`. This keeps features independent (no cross-feature imports), but the two generators can drift.
- **Impact**: Inconsistent mock data if one file is updated without the other.
- **Deferred**: Extract shared mock constants (serials, states, tone map, firmware/product lists) into a shared `features/mocks/` module when a third feature needs them.

### 2. Slot Layout Is a Simplistic Linear Grid
- `buildSlotOverview` marks the first N slots occupied in linear order (S01…S0N) — a placeholder, not a real rack layout.
- **Impact**: Does not reflect real machine slot geometry; clearly labeled Placeholder.
- **Deferred**: Real slot layout data/model when the actual machine topology is known.

### 3. Filtering/Sorting Logic Not Unit-Tested
- `matchesFilters` and `SORTERS` live inside `useMachineExplorer` with no test harness (the repo has no test runner configured).
- **Impact**: Regressions in search/filter/sort behavior would go uncaught.
- **Deferred**: Extract pure functions and add tests once a test framework (Vitest) is introduced.

### 4. Health Panel and Timeline Are Placeholders
- Health factors, timeline stages, and charts are explicit placeholder content (labels say so).
- **Impact**: None functionally; intentional scope boundary.

### 5. Feature Stylesheet Growth
- `machineExplorer.css` (~490 lines) duplicates toolbar, button, card, table, and detail patterns from Battery Explorer's stylesheet.
- **Impact**: Some duplication; both features will keep diverging as they grow.
- **Deferred**: Promote shared primitives (status pill, health bar, section header, toolbar fields) into the design system when a second consumer needs them.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (`951.37 kB`, ~315 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state (filters, sort).

## Recommendations

- Introduce Vitest + a small suite for `matchesFilters`/`SORTERS` in both explorer features before adding more explorer functionality.
- Share mock constants and UI primitives once a third explorer-style feature (e.g., Timeline) is planned.
- Consider `React.lazy` for explorer routes to reduce the initial bundle.
