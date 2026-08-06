# Phase 8 Technical Debt Report

## Items Introduced in Phase 8

### 1. Static Mock Aggregates
- Quality records (560 rows) and KPI values (Pass Rate 94.5% · Fail Rate 5.5% · Yield 96.9% · Retest Rate 3.4% · Quality Score 95/100) are generated deterministically inside `qualityAnalytics.mock.ts`, but are not reconciled with the battery/machine/timeline mock sources.
- **Impact**: The quality numbers are not reconciled with the explorer features; drift is guaranteed once real data arrives.
- **Deferred**: Build a mock analytics layer that computes quality aggregates from the shared battery/machine mock sources.

### 2. Defect Assignment Is Uniform by Construction
- Per-record defect categories are assigned by rotating seed indices, so the fleet-level defect distribution is near-uniform (~16–17% per category) rather than reflecting realistic skew.
- **Impact**: Panels look flat; does not exercise meaningful differences between categories.
- **Deferred**: Introduce weighted severity-based defect generation when real defect data is modeled.

### 3. Detail View Is Local State, Not a Route
- The record drill-down (`QualityDetailPanel`) is driven by `useState` in `useQualityAnalytics` rather than a `/quality/:id` route.
- **Impact**: The detail view is not deep-linkable/bookmarkable, and the browser back button does not exit the drill-down.
- **Deferred**: Promote the drill-down to a parameterized route or URL-synced state when real navigation semantics are required.

### 4. Pass/Fail Threshold Is Hardcoded
- A record is `Pass` when `passRate >= 95`, matching the pass-rate KPI only by convention.
- **Impact**: The threshold is a magic number inside the mock and is not shared or configurable.
- **Deferred**: Extract to a shared constant or configuration when product-specific thresholds exist.

### 5. No Unit Tests
- `qualityAnalytics.mock.ts` shape, the filter predicate, and the hook are not covered by tests (the repo has no test runner configured).
- **Impact**: Structural changes to the mock contract or filter logic could go uncaught.
- **Deferred**: Add contract/filter tests once a test framework (Vitest) is introduced.

### 6. Feature Stylesheet Growth
- `qualityAnalytics.css` (~540 lines) repeats section-header, button, toolbar, distribution-bar, comparison, and responsive patterns from prior features.
- **Impact**: Cross-feature duplication continues to grow.
- **Deferred**: Promote shared primitives (section header, toolbar, distribution bars) into the design system.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (~1,022 kB, ~328 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state.

## Recommendations

- Derive Quality Analytics mock values from the shared battery/machine mock generators to keep the platform's numbers consistent.
- Introduce Vitest for contract tests on mock providers, hooks, and the filter predicate.
- Consider `React.lazy` for dashboard/analytics routes to reduce the initial bundle.
- Consider URL-synced drill-down state (`/quality/:id`) for deep-linking.
