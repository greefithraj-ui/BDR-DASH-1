# Phase 22 Deployment Review

Deployment mechanics audited and validated end to end. Version 0.3.0.

## What was verified

| Item | Result |
| --- | --- |
| Env-file discovery | Fixed and verified from every supported working directory (see below) |
| Version sync | `package.json` root 0.3.0, `apps/web/package.json` 0.3.0, `BIP_API_VERSION` 0.3.0 in all `.env.*`, code default 0.3.0 |
| Documented run commands | `npm run dev:api`, `npm run dev:web`, `npm run build:web`, `npm run health:api` all execute correctly |
| Production-style boot | uvicorn with `--app-dir apps/api` boots and serves health |
| Requirements | `openpyxl>=3.1.5`, `reportlab>=4.2.0` pinned (were present at runtime, missing from the file) |
| Ports | API 8100; web dev 3100 (vite, proxies `/api` → 8100); DB 5432 |
| CORS | dev origins (`localhost:3100`, `127.0.0.1:3100`) default; production origin set per env file |
| Static bundle | `apps/web/dist` produced by `npm run build:web` |

## Env-file discovery (the fix)

**Problem**: `SettingsConfigDict(env_file=".env")` never loaded the repo's `.env.development`/`.env.production`, and the first repair iteration walked up past the project root and loaded the parent repository's `D:\BDR\.env`.

**Fix** (`apps/api/app/config/settings.py`): `_project_root()` locates the nearest ancestor of the CWD containing an `apps/` directory; `_find_env_file()` searches upward from the CWD but stops at that root; `_default_env_file()` prefers `.env`, then `.env.{BIP_ENVIRONMENT}`.

**Verified resolutions**:
- From `D:\BDR\bip\apps\api` → `D:\BDR\bip\.env.development`
- From `D:\BDR\bip` → `D:\BDR\bip\.env.development`
- With `BIP_ENVIRONMENT=production` → `D:\BDR\bip\.env.production` (health/CORS confirm the file loads: CORS becomes the single production origin, not the 2-origin default)

**Smoke test**: `python -m uvicorn app.main:app --app-dir apps/api --port 8181` → health `environment=development`, `version=0.3.0`.

## Version-control status (blocker)

`git -C D:\BDR status --porcelain bip` → `?? bip/`. The entire platform is untracked; `bip/` has no `.git`. No code review, history, diffing, or rollback is possible until the tree is committed. This is the **single deployment blocker**.

Recommended first commit contents: source trees, `.env.example` (tracked), `.gitignore` (confirmed to exclude `.env`, `.env.*`, `node_modules`, `dist`, `.venv`, `__pycache__`); the `.env.development`/`.env.production` files stay ignored.

## Deployment steps for production

1. `git init` in `D:\BDR\bip` (or add to the parent repo) and commit the audited baseline.
2. `npm ci` + `pip install -r apps/api/requirements.txt`.
3. Set `BIP_ENVIRONMENT=production` (or provide `.env`); override `BIP_DB_PASSWORD` and `BIP_CORS_ORIGINS`.
4. `npm run build:web`; serve `apps/web/dist`.
5. Run uvicorn behind a TLS reverse proxy (see Security.md).
6. `npm run health:api` → expect `v0.3.0 (production)`.

Full walkthrough in `docs/Production/Deployment.md`; variables in `docs/Production/Configuration.md`; release steps in `docs/Production/Release Process.md`.
