# Phase 2.5 Architecture Review

## Summary

Phase 2.5 standardized the Battery Intelligence Platform foundation: fixed ports, added a dev proxy, introduced a design-token system with three theme modes, added reusable ECharts wrappers, implemented a global command palette, and moved all configurable URLs into environment variables. No feature or business logic was added.

## Component Topology After Phase 2.5

```
bip/
  apps/web (React SPA, :3100)
    src/
      theme/           tokens.css (light + dark), global.css
      app/             App, providers (Theme/Chart/Query/State/Notification), routing
      components/
        layout/        Main/Sidebar/Header/Footer shell
        design-system/ reusable primitives (re-exports ChartContainer)
        charts/        ChartProvider, ChartTheme, BaseChart, ChartContainer
        command-center/CommandCenter
      features/        executive-dashboard, battery-intelligence-dashboard, auth
      hooks/           useEffectiveTheme, useCommandCenter(Shortcut)
      state/           themeStore (light/dark/auto, persisted), layoutStore, notificationStore
      lib/             apiClient (relative /api), cn
  apps/api (FastAPI, :8100)
    app/
      api/v1/routes/health
      core/            config (env-driven), middleware (CORS), logging, exceptions
  scripts/check_health.py
  .env.example / .env.development / .env.production
```

## Data Flow

1. Browser issues `GET /api/...` against the SPA origin `:3100`.
2. Vite dev server proxies `/api` to `http://localhost:8100` (`VITE_BIP_API_PROXY_TARGET`).
3. FastAPI serves `/api/health` and future versioned routes.
4. CORS still allows `:3100` origins for non-proxied deployments.

## Design Decisions

- **Relative API base.** The client uses `VITE_BIP_API_BASE_URL` (default `/api`). The proxy resolves it in development; production can override with an absolute base if the API is served from another origin.
- **Token-driven theming.** All styling reads CSS custom properties. Dark mode swaps token values on `:root[data-theme="dark"]`; `auto` resolves the OS preference through `matchMedia`. The chart theme is derived from the same effective-theme hook, keeping charts consistent with the UI.
- **Tree-shaken ECharts.** `ChartTheme.ts` registers only used components/renderers via `echarts.use(...)`, and the theme-aware wrappers isolate ECharts behind a small reusable API.
- **Command center as a global overlay.** It is mounted once in `MainLayout` and driven by the existing `layoutStore`, keeping search/palette state out of routing.
- **Environment-owned configuration.** Proxy target, API base, CORS origins, and the health-script URL all live in env files; code defaults are only fallbacks.

## Resilience

- FastAPI settings load from `.env` and `BIP_*` environment variables; CORS origins are parsed defensively (whitespace-stripped, empties dropped).
- The command palette registers one global keydown listener with cleanup.
- BaseChart disposes ECharts instances on unmount and re-initializes on theme change, avoiding leaked instances or stale options.

## Risks

- See `Phase 2.5 Technical Debt Report.md` (bundle size, duplicated component CSS, JS palette mirroring tokens).
- Production deployments must either proxy `/api` at the web origin or set `VITE_BIP_API_BASE_URL` to an absolute API base.
