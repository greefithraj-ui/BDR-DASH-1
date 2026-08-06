# Phase 2.5 Technical Debt Report

## Introduced or Resurfaced in Phase 2.5

### 1. Large production chunk (ECharts in the main bundle)
- `vite build` emits a single ~913 KB JS chunk (ECharts contributes most of it), triggering the >500 KB warning.
- **Suggested fix:** lazy-load feature routes with `React.lazy`/`Suspense` and/or split `echarts` into a manual chunk (`build.rollupOptions.output.manualChunks`). Defer to a feature phase; the SPA is a shell today.

### 2. Duplicated component-level CSS
- `.ds-card`, `.ds-badge`, `.ds-button`, `.ds-metric-card`, etc. still live inside `features/executive-dashboard/executiveDashboard.css` even though they style global design-system primitives.
- **Suggested fix:** move design-system styles into a shared stylesheet (e.g. `components/design-system/design-system.css` imported by the design-system module) during the component-library phase.

### 3. Chart palette mirrors tokens in JavaScript
- `ChartTheme.ts` hardcodes chart colors that duplicate `tokens.css` values.
- **Suggested fix:** derive chart theme colors from computed CSS variables at registration time, or generate both from a single source, to prevent drift.

### 4. Command center is intentionally shallow
- Results are static route labels filtered by the query; there is no keyboard navigation, no "recent" tracking, and no real search.
- **Suggested fix:** implement the design's ranking formula, entity search, and keyboard interaction in the planned Command Center phase.

### 5. Theme persistence is single-tab
- Persistence uses `localStorage` only; a theme change in one tab is not propagated to other tabs.
- **Suggested fix:** listen for the `storage` event or use a `BroadcastChannel` when multi-tab consistency matters.

### 6. Production `/api` routing depends on deployment topology
- In production the SPA must be served behind a proxy that forwards `/api` to `:8100`, or `VITE_BIP_API_BASE_URL` must be overridden.
- **Suggested fix:** document/document-check the PM2 or reverse-proxy configuration during deployment setup.

## Pre-existing (not addressed in Phase 2.5)

### 7. Dependency audit findings
- `npm audit` reports 2 moderate-severity vulnerabilities. No fix was applied because automatic `npm audit fix` can mutate dependency versions outside this standardization scope.

### 8. No automated tests
- The BIP web app and API have no automated test suite yet (the BDR collector has its own suite). Unit/integration tests for BIP were not part of Phase 2.5.

### 9. Design-system placeholders
- Many primitives (`Dialog`, `Drawer`, `Tabs`, `Table`, `Filters`, `SearchInput`, `Avatar`) remain minimal shell components; real implementations belong to the component-library phase.

### 10. No `.env` committed for backend local use
- Backend config falls back to defaults when `.env` is absent; teams should copy `.env.example` to `.env` for local overrides.

## Standing Recommendations

- Run `npm run lint:web` and `npm run build:web` before merging any change.
- Keep all URLs in environment variables; do not reintroduce hardcoded origins.
- Keep chart usage behind the `components/charts` wrappers so theme switching stays consistent.
