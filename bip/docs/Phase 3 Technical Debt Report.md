# Phase 3 Technical Debt Report

## Items Introduced in Phase 3

### 1. Mock Data Coupled to Serial Format
- `batteryExplorer.mock.ts` hardcodes the `RP-CH3-P18-WD-*` serial template. The format is derived from user sample IDs but is not validated against a real schema.
- **Impact**: If the real serial scheme differs, the generator (and any test asserting the format) must be updated.
- **Deferred**: Replace with an API-backed repository when the real data contract exists.

### 2. Date Handling Is String-Based
- Date filtering compares `lastSeen.slice(0, 10)` lexicographically against `dateFrom`/`dateTo` inputs. This works because all mock timestamps share the `YYYY-MM-DD` prefix, but it is fragile.
- **Impact**: Mixed date formats, timezone handling, or ISO-with-offset strings would silently mis-filter.
- **Deferred**: Introduce a date utility (e.g., `Intl`-based or a small parsing helper) when real data arrives.

### 3. Filtering/Sorting Logic Not Unit-Tested
- `matchesFilters`, `SORTERS`, pagination math, and `safePage` clamping live inside `useBatteryExplorer` with no test harness (the repo has no test runner configured).
- **Impact**: Regressions in filter/sort/page behavior would go uncaught.
- **Deferred**: Extract pure functions into `batteryExplorer.logic.ts` and add tests once a test framework (Vitest) is introduced.

### 4. Placeholder Detail Panels
- Decision Summary, Recent Events, and the two charts are explicit placeholders (`Badge`/labels say so). They render mock content that will be replaced.
- **Impact**: None functionally; intentional scope boundary.

### 5. Feature Stylesheet Growth
- `batteryExplorer.css` (~380 lines) is feature-scoped but unshared; toolbar/table/button styles could eventually move to design-system primitives.
- **Impact**: Some duplication with future explorer-style pages (e.g., Machine Explorer).
- **Deferred**: Refactor into reusable design-system components when a second consumer appears.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (`931.81 kB`, ~311 kB gzip) — ECharts is bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5, not addressed in Phase 3.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state (filters, sort, page).

## Recommendations

- Phase 4 should define the real battery data contract (schema + API) so the mock seam (`getMockBatteryRecords`/`getMockBatteryDetail`) can be swapped cleanly.
- Introduce Vitest + a small suite for `matchesFilters`/`SORTERS`/pagination before adding more explorer features.
- Consider `React.lazy` for the Battery Explorer route to reduce the initial bundle.
