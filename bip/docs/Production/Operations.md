# Battery Intelligence Platform — Operations Runbook

Version 0.3.0.

## Services

| Service | Location | Port | Command |
| --- | --- | --- | --- |
| bip API | `apps/api` | 8100 | `npm run dev:api` (dev) / uvicorn (prod) |
| bip web (dev) | `apps/web` | 3100 | `npm run dev:web` |
| bip web (prod) | `apps/web/dist` | static | any static host |
| PostgreSQL | external BDR stack | 5432 | external |

## Daily checks

```powershell
# 1. Health contract (status/version/service/timestamp/environment)
npm run health:api

# 2. OpenAPI is published
curl -s http://127.0.0.1:8100/api/openapi.json | findstr /C:"paths"

# 3. Collector freshness (Collector Status report)
curl -s "http://127.0.0.1:8100/api/v1/reports/generate?report_type=Collector%20Status"
```

## Restart procedure

```powershell
# Stop: find the process bound to 8100 and terminate it
$conn = Get-NetTCPConnection -LocalPort 8100 -State Listen
Stop-Process -Id $conn.OwningProcess -Force

# Start (API must run from apps/api or with --app-dir apps/api)
npm run dev:api
```

## Logs

API logs are written to the console/uvicorn log. When launched through the documented dev flow, capture stdout/stderr to a file, e.g.:

```
uvicorn app.main:app --host 127.0.0.1 --port 8100 > bip_api.log 2> bip_api.err
```

- Startup errors (missing module, bad env file) appear at import time.
- Request failures surface as HTTP 5xx plus a stack trace in the log.
- The DB pool logs connection/disconnection at INFO level; it never logs credentials.

## Failure procedures

### API won't start

1. `python -m py_compile` each module under `apps/api/app` — a syntax error aborts import.
2. Confirm the working directory or `--app-dir` points at `apps/api`.
3. Check that the env file was discovered: run `python -c "from app.config.settings import _default_env_file; print(_default_env_file())"` from the same directory. It must resolve inside `D:\BDR\bip`, never the parent repo.
4. If the DB is unreachable, the API still boots; `/api/health` reports `status=ok` while `/api/v1/system/info` may show the pool disconnected.

### 404s on previously working routes

- Verify you hit `/api/v1/...` (routes mount under `/api`).
- The OpenAPI document at `/api/openapi.json` lists every registered route — diff it against the expected route table in API.md.

### Reports fail to generate/download

- Generation is ~1 s per type; a 500 with a generator traceback is visible in the API log.
- Downloads are served from the report store (`BIP_REPORT_STORAGE_DIR` or `<temp>/bip_reports`). Unknown ids → 404, unknown format → 400.

## Scheduled maintenance

- **None required**: the API is read-only and holds no mutable application state beyond the report document cache (temp dir) and asyncpg pool.
- On version bumps: update `BIP_API_VERSION` in all `.env.*`, both `package.json` files, then restart.
