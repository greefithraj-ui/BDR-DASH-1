# Phase 2.5 Backward Compatibility Report

## Goal

Confirm that the standardization pass does not break existing Phases 0–2 behavior.

## Unchanged

- All 25 routes and their labels in `app/routing/routes.ts` are unchanged.
- `MainLayout`, `SidebarLayout`, `HeaderLayout`, and `FooterLayout` structure is unchanged except for wiring (see below).
- All provider exports and their composition order are unchanged; `ChartProvider` was added inside `ThemeProvider` without altering the others.
- `ExecutiveDashboardPage` and `BatteryIntelligenceDashboardPage` source and mock data are unchanged.
- API contract `GET /api/health` response shape is unchanged.
- Zustand stores: `layoutStore` and `notificationStore` unchanged; `themeStore` extended.
- Auth abstraction unchanged.

## Compatible Changes (no consumer edits required)

- **`ChartContainer`** is still exported from `components/design-system` (now re-exported from `components/charts/ChartContainer`). Both existing call sites pass `children`/`className` and continue to compile and render.
  - Minor API note: the old design-system `ChartContainer` accepted an unused `label` prop; the new wrapper does not. No consumer used `label`, so no source changes were required.
- **Theme button**: the header toggle now cycles `light → dark → auto` instead of toggling two modes. Behavior is a superset of the old toggle.
- **Theme persistence**: a selection is stored under `bip.theme`. Users who never selected a theme get `auto` on first load instead of the previous hardcoded `light`. This is intentional; their OS preference now drives first render and any manual choice persists.

## Breaking Changes (intentional, design-aligned)

- **Dev ports changed**: web `5174 → 3100`, API `8001 → 8100`, preview `4174 → 4100`. Local bookmarks and any scripts pointing at the old ports must be updated. These changes align the platform with the approved design (`:3100` web, `:8100` API) and make the design-specified dashboard button URL (`http://localhost:3100`) valid.
- **API client base changed** from a hardcoded `http://127.0.0.1:8001` to the relative `/api`. Requests now rely on the Vite proxy in development. Direct API calls from the browser at `:8001` no longer occur.
- **CORS origins** updated from `:5174` to `:3100`.
- **API version** default bumped from `0.0.0` to `0.2.5` (no contract change).

## Migration Notes

- Dev workflows: use `npm run dev:web` (now on `3100`) and `npm run dev:api` (now on `8100`).
- Health checks: use `npm run health:api` or `curl http://127.0.0.1:8100/api/health`; through the proxy, `curl http://127.0.0.1:3100/api/health`.
- If a local override is needed, copy `.env.example` to `.env` before starting the API.
