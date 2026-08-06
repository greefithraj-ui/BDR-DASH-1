# Phase 12 Technical Debt Report

## Items Introduced in Phase 12

### 1. Static Mock Administration Data
- Machine health scores, collector events/min, database latencies, and audit timestamps are generated deterministically inside `administration.mock.ts` but are not reconciled with the shared battery/machine mock sources.
- **Impact**: Administration numbers (e.g., AQC-04 health 71) are only loosely consistent with the explorer/analytics features; drift is guaranteed once real data arrives.
- **Deferred**: Build a shared mock admin layer that derives health/collector data from the same sources as the other features.

### 2. Health Timeline Re-derives Status from Score
- `getHealthTimeline` recomputes the status badge from the derived score using a hardcoded threshold (≥85 Healthy, ≥70 Warning, else Critical), duplicating thresholds that also live conceptually in performance/quality features.
- **Impact**: Thresholds are magic numbers embedded in the mock and not shared.
- **Deferred**: Extract status thresholds to a shared constant or configuration.

### 3. Detail View Is Local State, Not a Route
- The machine drill-down (`AdministrationDetailPanel`) is driven by `useState` in `useAdministration` rather than an `/admin/:machineId` route.
- **Impact**: The detail view is not deep-linkable/bookmarkable, and the browser back button does not exit the drill-down.
- **Deferred**: Promote the drill-down to a parameterized route or URL-synced state when real navigation semantics are required.

### 4. Audit Log Growth Is Unbounded in Mock
- `buildAuditEntries` concatenates static global entries with one generated entry per machine. The list length is fixed at 20 and sorted on every `getMockAdministration` call.
- **Impact**: Fine for a mock, but the sort-on-build approach would not scale to a real audit store.
- **Deferred**: Introduce paging/virtualization when real audit data is wired.

### 5. Duplicate Tone Maps Across Features
- Service/database/collector/schema tone maps are re-declared inside Phase 12 components (plus the shared helpers in the mock), mirroring similar status-tone maps in earlier features.
- **Impact**: Cross-feature duplication of the status→tone contract continues to grow.
- **Deferred**: Promote a shared status-tone contract into the design system.

### 6. No Unit Tests
- `administration.mock.ts` shape, the filter predicate, and the hook's drill-down flow are not covered by tests (the repo has no test runner configured).
- **Impact**: Structural changes to the mock contract or filter logic could go uncaught.
- **Deferred**: Add contract/filter tests once a test framework (Vitest) is introduced.

## Pre-Existing Debt Carried Forward (unchanged)

- **Large single JS chunk** (~1,124 kB, ~350 kB gzip) — ECharts bundled into one chunk; `vite build` emits a >500 kB warning. Introduced in Phase 2.5.
  - Suggested fix: route-level lazy loading (`React.lazy`) or `manualChunks` splitting ECharts.
- No test framework configured for the web app.
- No URL/state persistence for UI state.
- `routes.ts` requires an additive registry entry for top-level paths not already present (first seen in Phase 11).

## Recommendations

- Derive administration health/collector values from the shared machine/battery mock sources.
- Extract status thresholds and status→tone maps into shared constants/design-system primitives.
- Consider URL-synced drill-down state (`/admin/:machineId`) for deep-linking.
- Introduce Vitest for contract tests on mock providers and hooks.
- Consider `React.lazy` for admin/dashboard/analytics routes to reduce the initial bundle.
