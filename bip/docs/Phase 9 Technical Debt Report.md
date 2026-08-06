# Phase 9 Technical Debt Report

## Items Introduced in Phase 9

### 1. Static Mock Aggregates
- Performance records (560 rows) and KPI values (Throughput 146.3/hr · Cycle Time 13.6s · Utilization 84.4% · Processing Rate 2.4/min · Efficiency 92% · Score 90/100) are generated deterministically inside `performanceAnalytics.mock.ts`, but are not reconciled with the battery/machine/timeline mock sources.
- **Impact**: The performance numbers are not reconciled with the explorer features; drift is guaranteed once real data arrives.
- **Deferred**: Build a mock analytics layer that computes performance aggregates from the shared battery/machine mock sources.

### 2. Product Performance Converges by Construction
- Every product is generated across all machines with the same machine-dependent throughput base, so product-level averages converge (all ≈146/hr, score 90), making the Product Performance panel nearly uniform.
- **Impact**: Product-level comparison rows look flat; meaningful per-product differences are not modeled.
- **Deferred**: Introduce product-specific throughput/cycle-time factors when real product data is modeled.

### 3. Status Thresholds Are Hardcoded
- Performance Score thresholds (≥85 On Target, ≥70 Watch, else Off Target) are magic numbers embedded in the mock.
- **Impact**: The thresholds are not shared or configurable.
- **Deferred**: Extract to a shared constant or configuration when machine-specific targets exist.

### 4. Detail View Is Local State, Not a Route
- The record drill-down (`PerformanceDetailPanel`) is driven by `useState` in `usePerformanceAnalytics` rather than a `/performance/:id` route.
- **Impact**: The detail view is not deep-linkable/bookmarkable, and the browser back button does not exit the drill-down.
- **Deferred**: Promote the drill-down to a parameterized route or URL-synced state when real navigation semantics are required.

### 5. No Unit Tests
- `performanceAnalytics.mock.ts` shape, the filter predicate, and the hook are not covered by tests (the repo has no test runner configured).
- **Impact**: Structural changes to the mock contract or filter logic could go uncaught.
- **Deferred**: Add contract/filter tests once a test framework (Vitest) is introduced.

### 6. Feature Stylesheet Growth
- `performanceAnalytics.css` (~540 lines) repeats section-header, button, toolbar, distribution-bar, comparison, and responsive patterns from prior features.
- **Impact**: Cross-feature duplication continues to grow.
- **Deferred**: Promote shared primitives (section header, toolbar, distribution bars) into the design system.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (~1,042 kB, ~331 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state.

## Recommendations

- Derive Performance Analytics mock values from the shared battery/machine mock generators to keep the platform's numbers consistent.
- Introduce Vitest for contract tests on mock providers, hooks, and the filter predicate.
- Consider `React.lazy` for dashboard/analytics routes to reduce the initial bundle.
- Consider URL-synced drill-down state (`/performance/:id`) for deep-linking.
