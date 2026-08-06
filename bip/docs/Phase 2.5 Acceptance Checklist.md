# Phase 2.5 Acceptance Checklist

## Ports

- [x] Web runs on `3100`.
- [x] API runs on `8100`.
- [x] `dev:api` script uses port `8100`.
- [x] `dev`/`preview` scripts use `3100`/`4100`.
- [x] `vite.config.ts` dev port is `3100`.
- [x] CORS origins point at `3100`.
- [x] `check_health.py` targets `8100` (overridable via `BIP_API_URL`).
- [x] No hardcoded old ports (`5174`, `8001`, `4174`) remain.

## Vite Proxy

- [x] `/api` is proxied to `http://localhost:8100`.
- [x] Proxy target reads from `VITE_BIP_API_PROXY_TARGET`.
- [x] Live check: `http://127.0.0.1:3100/api/health` returned the API payload.
- [x] Live check: Vite root `/` returned HTTP 200.

## Design Tokens

- [x] Token groups `--color-*`, `--surface-*`, `--text-*`, `--border-*`, `--shadow-*`, `--radius-*`, `--space-*` defined.
- [x] Light theme tokens in `:root`.
- [x] Dark theme tokens in `:root[data-theme="dark"]`.
- [x] Application stylesheets reference tokens instead of hardcoded colors.
- [x] Theme modes `light`, `dark`, and `auto` supported.
- [x] `auto` follows OS `prefers-color-scheme` and reacts to changes.
- [x] Selected theme persists across reloads (`localStorage` key `bip.theme`).

## ECharts Wrappers

- [x] `echarts` installed (`echarts@6.1.0`).
- [x] `ChartProvider` created and mounted in `AppProviders`.
- [x] `ChartTheme` registers `bip-light` and `bip-dark` themes.
- [x] `BaseChart` handles init, update, loading, resize, and theme switching.
- [x] `ChartContainer` is a reusable shell with placeholder rendering.
- [x] No business charts added.
- [x] Existing `ChartContainer` consumers still compile.

## Command Center

- [x] `Ctrl/Cmd+K` opens the palette.
- [x] Palette closes via `Escape`.
- [x] Palette closes via backdrop click.
- [x] Search input present.
- [x] Placeholder results shown (no real search logic).
- [x] Header `CTRL+K` button opens the palette.

## Environment

- [x] `.env.example` created.
- [x] `.env.development` created.
- [x] `.env.production` created.
- [x] Configurable URLs moved into environment variables.

## API Client

- [x] Requests go through the relative `/api` base.
- [x] No hardcoded localhost in the API client.
- [x] Env vars typed in `vite-env.d.ts`.

## Verification

- [x] TypeScript check passes.
- [x] Production build passes.
- [x] FastAPI imports and serves health.
- [x] Proxy verified end-to-end.
- [x] Theme mechanism verified.
- [x] Command palette compiled and wired.
- [x] Chart wrappers compiled and bundled.
