# Phase 7 Technical Debt Report

## Items Introduced in Phase 7

### 1. Static Mock Aggregates
- Product records and KPI values (Products 5 · Total Batteries 1,700 · Avg Pass Rate 94% · Fleet Health 79/100) are generated deterministically inside `productAnalytics.mock.ts`, but are not reconciled with the battery/machine/timeline mock sources.
- **Impact**: The catalog numbers are not reconciled with the explorer features; drift is guaranteed once real data arrives.
- **Deferred**: Build a mock analytics layer that computes product aggregates from the shared battery/machine mock sources.

### 2. Detail View Is Local State, Not a Route
- The product drill-down (`ProductDetailPanel`) is driven by `useState` in `useProductAnalytics` rather than a `/production/:product` route.
- **Impact**: The detail view is not deep-linkable/bookmarkable, and the browser back button does not exit the drill-down.
- **Deferred**: Promote the drill-down to a parameterized route or URL-synced state when real navigation semantics are required.

### 3. Date Filters Operate on a Label Field
- `dateFrom`/`dateTo` compare against the `lastUpdated` string field (`YYYY-MM-DD`), so they work only because mock dates are normalized ISO strings.
- **Impact**: Works for mock data; a real timestamp field must use proper date objects/ranges.
- **Deferred**: Replace with typed date handling when real data lands.

### 4. No Unit Tests
- `productAnalytics.mock.ts` shape, the filter predicate, and the hook are not covered by tests (the repo has no test runner configured).
- **Impact**: Structural changes to the mock contract or filter logic could go uncaught.
- **Deferred**: Add contract/filter tests once a test framework (Vitest) is introduced.

### 5. Feature Stylesheet Growth
- `productAnalytics.css` (~520 lines) repeats section-header, button, panel, distribution-bar, and responsive patterns from prior features.
- **Impact**: Cross-feature duplication continues to grow.
- **Deferred**: Promote shared primitives (section header, toolbar, distribution bars) into the design system.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (~1,000 kB, ~324 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state.

## Recommendations

- Derive Product Analytics mock values from the shared battery/machine mock generators to keep the platform's numbers consistent.
- Introduce Vitest for contract tests on mock providers, hooks, and the filter predicate.
- Consider `React.lazy` for dashboard/analytics routes to reduce the initial bundle.
- Consider URL-synced drill-down state (`/production/:product`) for deep-linking.
