# Battery Intelligence Platform — Troubleshooting Guide

Version 0.3.0.

## Health endpoint

`GET /api/health` returns the full contract:

```json
{
  "status": "ok",
  "version": "0.3.0",
  "service": "Battery Intelligence Platform API",
  "timestamp": "2026-08-05T08:33:50.685909Z",
  "environment": "development"
}
```

Run `npm run health:api` (`scripts/check_health.py`) — it validates the contract and exits nonzero on any mismatch.

## Symptom → cause table

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `ModuleNotFoundError: No module named 'app'` | API launched from the wrong directory | Run from `apps/api` or add `--app-dir apps/api` |
| Health returns wrong environment/version | Env file not discovered | `_default_env_file()` must resolve inside `D:\BDR\bip`; remove stray parent `.env` influence (walk stops at the project root) |
| `GET /api/v1/reports` → 422 | Old query-param injection form | Use `filters`/`page` via the documented `FilterParams`/`PageQuery` idiom (already fixed) |
| `POST /api/v1/reports/generate` → 500 with generator traceback | Generator data-shape mismatch | Check API log; regenerate; the generator now indexes `(rows, total)` tuples explicitly |
| `GET /api/v1/reports/download/{id}` → 404 | Unknown report id (store is a temp-dir cache) | Re-generate the report first; downloads require a stored document |
| `GET .../download/{id}?format=docx` → 400 | Unsupported format | Use `csv`, `xlsx`, or `pdf` |
| `GET /api/v1/machines/` (trailing slash) → 307 | Starlette trailing-slash redirect | Expected; clients must follow the redirect or omit the trailing slash |
| CORS preflight → 400 | Origin not in `BIP_CORS_ORIGINS` | Add the origin; restart the API |
| DB pool shows disconnected | DB down or credentials wrong | Check `BIP_DB_*`; the API still boots — `/api/health` stays `ok` |
| Vite build > 800 kB chunk warning | N/A | Already mitigated via `manualChunks` (echarts/react-vendor split) |

## Useful commands

```powershell
# Contract health
npm run health:api

# Env file resolution
python -c "from app.config.settings import _default_env_file; print(_default_env_file())"

# Route inventory
curl -s http://127.0.0.1:8100/api/openapi.json

# Full API validation (Phase 22 suite) — see docs/Phase 22 API Validation.md
python C:\Users\meshe\AppData\Local\Temp\opencode\api_validation.py
```

## Escalation

If a symptom is not listed, capture: API log tail, `_default_env_file()` output, `BIP_ENVIRONMENT` value, and the OpenAPI route list. These four inputs isolate startup, config, and routing failures.
