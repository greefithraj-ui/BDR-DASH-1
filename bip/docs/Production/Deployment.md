# Battery Intelligence Platform — Deployment Guide

Version 0.3.0. Applies to the `bip` monorepo at `D:\BDR\bip`.

## Topology

- **API** — FastAPI/uvicorn, Python 3.12, bound to `127.0.0.1:8100` (dev) / a port chosen by the host (prod). Read-only data source: PostgreSQL `bdr_dashboard` via a `bip_reader` role that has no write privileges.
- **Web** — React 18 + Vite SPA. Dev server on `:3100` proxying `/api` to the API. Production build is static files served by any static host / reverse proxy.
- **Data collection** — external collector harness (BDR) writes to PostgreSQL. The bip API only ever reads.

## Prerequisites

- Python 3.12 (tested with the system interpreter at `C:\Users\meshe\AppData\Local\Programs\Python\Python312\python.exe`).
- Node 20+ (Vite 6 requires a modern runtime).
- PostgreSQL 15+ reachable at `BIP_DB_HOST:BIP_DB_PORT` (not required to boot the API; health endpoint reports the pool state).

## Build

```powershell
# From the repo root D:\BDR\bip
npm install
python -m pip install -r apps/api/requirements.txt

npm run build:web          # produces apps/web/dist (static bundle)
```

The production bundle is split into three chunks: `react-vendor`, `echarts`, and `index` (see Performance Review).

## Run

### API (development)

```powershell
npm run dev:api            # uvicorn --app-dir apps/api --host 127.0.0.1 --port 8100
```

### API (production-style)

```powershell
# From apps/api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --workers 2
```

Run behind a reverse proxy (nginx/Caddy) that terminates TLS and adds the security headers listed in Security.md.

### Web

```powershell
npm run dev:web            # dev server, proxies /api to 127.0.0.1:8100
# Production: serve apps/web/dist with any static host; configure VITE_BIP_API_BASE_URL
```

## Environment files

The API reads `BIP_*` variables from an env file discovered by walking up from the working directory, stopping at the project root (the nearest ancestor containing an `apps/` directory). Resolution order:

1. `.env` at or above the CWD within the project root — highest precedence.
2. `.env.<BIP_ENVIRONMENT>` (`development` default) — e.g. `.env.production`.
3. If neither exists, the file name is used as the pydantic-settings `env_file` target and process environment variables still apply.

See `Configuration.md` for the full variable reference.

## Verification after deploy

```powershell
npm run health:api         # python scripts/check_health.py — validates contract, exits nonzero on failure
```

Expected: `OK: Battery Intelligence Platform API v0.3.0 (<environment>) @ <ISO timestamp>`.

## Version

- Root `package.json`: `0.3.0`.
- `apps/web/package.json`: `0.3.0`.
- `BIP_API_VERSION` in all `.env.*`: `0.3.0` (code default `0.3.0`).

Keep all three in sync when bumping.
