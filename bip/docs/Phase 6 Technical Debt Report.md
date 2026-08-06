# Phase 6 Technical Debt Report

## Items Introduced in Phase 6

### 1. Static Mock Aggregates
- KPI values, card metrics, insights, and alerts are hardcoded strings in `analyticsHub.mock.ts`, not derived from the battery/machine/timeline mocks.
- **Impact**: The hub's numbers (1,284 batteries, 91 health score, etc.) are not reconciled with the explorer features; drift is guaranteed once real data arrives.
- **Deferred**: Build a mock analytics layer that computes KPIs from the shared battery/machine mock sources.

### 2. Secondary Action Semantics
- "View Charts" scrolls to the placeholder chart area; it is a UX affordance rather than a real analytics drill-down.
- **Impact**: None functionally; labeled behavior may need replacement when real charts exist.
- **Deferred**: Replace with real drill-down when category pages are implemented.

### 3. Category Routes Are Still Placeholders
- Primary actions navigate to `/quality`, `/reliability`, `/performance`, `/trends`, `/comparison`, `/production` — all still render `PlaceholderPage`.
- **Impact**: Navigation works but lands on placeholder content (expected until later phases).
- **Deferred**: Implement category pages in later phases.

### 4. No Unit Tests
- `analyticsHub.mock.ts` shape and the hook are not covered by tests (the repo has no test runner configured).
- **Impact**: Structural changes to the mock contract could go uncaught.
- **Deferred**: Add contract/snapshot tests once a test framework (Vitest) is introduced.

### 5. Feature Stylesheet Growth
- `analyticsHub.css` (~360 lines) repeats section-header, button, card, and panel patterns from prior features.
- **Impact**: Cross-feature duplication continues to grow.
- **Deferred**: Promote shared primitives into the design system.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (`978.13 kB`, ~321 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state.

## Recommendations

- Derive Analytics Hub mock values from the shared battery/machine mock generators to keep the platform's numbers consistent.
- Introduce Vitest for contract tests on mock providers and hooks.
- Consider `React.lazy` for dashboard/analytics routes to reduce the initial bundle.
