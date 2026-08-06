# Battery Intelligence Platform — Configuration Reference

Version 0.3.0.

All settings live in `apps/api/app/config/settings.py` (pydantic-settings, prefix `BIP_`). They are read from the discovered env file (see Deployment.md) and may be overridden by process environment variables.

## Files

| File | Purpose |
| --- | --- |
| `.env.example` | Documented template, committed. |
| `.env.development` | Development overrides (gitignored). |
| `.env.production` | Production overrides (gitignored). |
| `.env` | Optional explicit override; wins over the env-specific file (gitignored). |

Env files are ignored via `.gitignore` (`.env`, `.env.*`, with `!.env.example`).

## Variables

### Service identity

| Variable | Default | Notes |
| --- | --- | --- |
| `BIP_APP_NAME` | `Battery Intelligence Platform API` | Reported by `/api/health`. |
| `BIP_API_VERSION` | `0.3.0` | Reported by `/api/health` and `check_health.py`. |
| `BIP_ENVIRONMENT` | `development` | Selects `.env.<value>`; reported by health. |
| `BIP_API_PREFIX` | `/api` | Mount prefix for all routes, including `/api/health`. |
| `BIP_CORS_ORIGINS` | `http://localhost:3100,http://127.0.0.1:3100` | Comma-separated allowed origins; other origins get `400` on preflight. |

### Database (read-only)

| Variable | Default | Notes |
| --- | --- | --- |
| `BIP_DB_HOST` | `localhost` | |
| `BIP_DB_PORT` | `5432` | |
| `BIP_DB_NAME` | `bdr_dashboard` | |
| `BIP_DB_USER` | `bip_reader` | Must be a read-only role. |
| `BIP_DB_PASSWORD` | `reader_pass` | **Placeholder default** — always override in production. Never logged. |
| `BIP_DB_POOL_MIN` | `1` | asyncpg min pool size. |
| `BIP_DB_POOL_MAX` | `10` | asyncpg max pool size. |
| `BIP_DB_CONNECT_TIMEOUT` | `5` | seconds. |
| `BIP_DB_COMMAND_TIMEOUT` | `15` | seconds per query. |

### Live data freshness

| Variable | Default | Notes |
| --- | --- | --- |
| `BIP_FRESHNESS_WINDOW_SECONDS` | `60` | Window used by the Collector Status report; aligned with the BIC spec. |

### Reports

| Variable | Default | Notes |
| --- | --- | --- |
| `BIP_REPORT_STORAGE_DIR` | *(empty)* | Directory for the report document cache. Empty = platform temp dir (`<temp>/bip_reports`). |

### Web build-time (not read by the API)

| Variable | Default | Notes |
| --- | --- | --- |
| `VITE_BIP_API_BASE_URL` | `/api` | API base for the SPA in production; change when the API is served from another origin. |
| `VITE_BIP_API_PROXY_TARGET` | `http://localhost:8100` | Dev-server proxy target. |

## Behaviour notes

- Unknown `BIP_*` variables are ignored (`extra="ignore"`).
- Env-file discovery stops at the project root (nearest ancestor containing `apps/`) so the API never loads a parent repository's `.env`.
- DB credentials are never logged; `db/session.py` logs host/port/database only.
