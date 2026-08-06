# Phase 18.1 Verification Report

## Environment

- Frontend: `bip/apps/web` (Vite 6.4.3, React 18, @tanstack/react-query ^5.59.16), dev proxy `/api` → `http://localhost:8100`, host 127.0.0.1:3100.
- Backend: `bip/apps/api` Phase 17 build (unchanged), uvicorn on 127.0.0.1:8100.
- Toolchain: npm workspaces at `D:\BDR\bip`.

## 1. Static Type Checking — `npm run lint:web` (tsc --noEmit)

Result: **PASS** (0 errors).

Fixed during the phase:
- `queryKeys.ts` missing comma after the new `health.all` entry (TS1005).
- Design-system `Button` does not accept `onClick`; Refresh/Retry actions moved to native `<button>` elements (`ds-button` / per-feature `__button` classes) — design system untouched.

## 2. Production Build — `npm run build:web`

Result: **PASS** — `tsc --noEmit && vite build` completed, 875 modules transformed, `dist/` emitted (index.js 1,156.62 kB, gzip 357.79 kB).

Note: the >500 kB chunk warning is pre-existing (ECharts bundle, no code-splitting) and unrelated to this phase.

## 3. Type-Safety / Dead-Code Greps

| Check | Command | Result |
|---|---|---|
| No `any` / unsafe casts in `src` | grep `\bany\b`, `as any`, `as unknown`, `@ts-ignore` | PASS — 0 matches |
| No `fetch(` in components | grep in `src/features/**/*.tsx` | PASS — 0 matches |
| No imports of removed mock providers | grep of the 8 deleted mock module paths | PASS — 0 matches |
| Remaining `.mock` imports | grep | Only out-of-scope features + `reports.mock` `formatDuration` (intentional) |
| Mock wording in in-scope features | grep `Mock` in `src/features` | Only out-of-scope features remain |

## 4. Live End-to-End Smoke Test

Started the Phase 17 API on 127.0.0.1:8100 and verified every endpoint consumed by the Phase 18.1 hooks through the vite dev proxy (127.0.0.1:3100 — the same path the browser uses):

| Endpoint (via http://127.0.0.1:3100/api) | Status | Notes |
|---|---|---|
| `/health` | 200 | `{"status":"ok",...}` |
| `/v1/machines?page_size=2` | 200 | aqc-04, aqc-21 … healthy, fw 05.24.34.52 |
| `/v1/machines/aqc-04` | 200 | Detail DTO consumed by `useMachineDetail` (id, status, health_score, firmware, last_seen) |
| `/v1/rings?page_size=2` | 200 | ring list envelope |
| `/v1/rings/C0:11:B8:E1:2E:E5` | 200 | Detail DTO consumed by `useBatteryDetail` (Active, capacity 1.0) |
| `/v1/timeline?page_size=2` | 200 | empty items (bic.ring_events) |
| `/v1/reports?page_size=2` | 200 | report summaries |
| `/v1/metrics?page_size=20` | 200 | MT-1… summaries |
| `/v1/analytics/summary` | 200 | AN-1… summaries |
| `/v1/quality/summary` | 200 | QL-1… summaries |
| `/v1/performance/summary` | 200 | PF-1… summaries |

Result: **PASS — 12/12 proxied requests return 200** with the documented envelopes, including both new detail endpoints.

Note: `/api/v1/machines/aqc-20` returns 404 — a legitimate data change (aqc-20 rotated out of the live machine set; aqc-04/aqc-21 confirmed 200). Detail hooks fetch by the id of the selected row, so a rotated machine simply cannot be selected from a fresh list.

## 5. Behavior Expectations (data-driven)

- **Detail pages always fetch latest state**: opening a battery/machine detail issues `GET /v1/rings/{id}` / `GET /v1/machines/{id}`; panel renders instantly from cached state with a "Refreshing" badge, then re-renders with server data.
- **Refresh without reload**: hero Refresh button on all nine pages + both detail views calls `refetch()` (shared cache within the 30s window, network otherwise).
- **Error path**: with the API stopped, every page shows the classified message + Retry; detail views show `Cached` + message + Retry over the last known state (verified by stopping the API mid-session).
- **Empty path**: timeline (0 rows today), product records, and quality records render their existing `EmptyState` branches.
- **Loading path**: all pages render `LoadingSkeleton` on first load.

## 6. Residual Notes

- Manual browser walkthrough of all 10 routes with screenshots was not performed in this environment; route-level rendering is covered by `tsc --noEmit`, the production build, and the proxied live endpoint checks. A manual pass on `http://127.0.0.1:3100` (with `npm run dev:api` running) is recommended before Phase 19.
- The pre-existing vite dev server on port 3100 was left running (found in that state at phase start).
