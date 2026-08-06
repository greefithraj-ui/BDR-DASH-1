# Phase 22 Security Review

Performed 2026-08-05. Scope: the running API, source tree, and configuration. Result: no critical vulnerabilities; four accepted risks documented.

## Checks performed

### 1. CORS enforcement
Preflight (`OPTIONS /api/v1/metrics`):
- Origin `http://localhost:3100` → `200`, `access-control-allow-origin: http://localhost:3100`, `allow-credentials: true`, `max-age: 600`.
- Origin `http://evil.example.com` → **`400 Bad Request`** (rejected).

### 2. Response headers
- `server: uvicorn` banner exposed on all responses (risk R2).
- No `X-Content-Type-Options`/CSP at the app layer (recommended at the reverse proxy).

### 3. Repo-wide secrets scan
Pattern `password|secret|api[_-]?key|BEGIN (RSA|PRIVATE)|AKIA` over `*.py,*.ts,*.tsx,*.json,*.yaml,*.yml,*.toml,*.cfg,*.ini`, excluding `node_modules`, `dist`, `.venv`, `package-lock.json`:
- Only two first-party hits: `config/settings.py` (`db_password` default) and `db/session.py` (uses `db_password`). No hardcoded secrets in source.
- All `.venv` hits are third-party libraries.

### 4. Credential handling
- `db/session.py` logs only host/port/database at INFO; the password is never logged.
- Env files (`.env`, `.env.*`) are gitignored; only `.env.example` is committed.

### 5. Input validation
- FastAPI/pydantic `FilterParams`/`PageQuery`/`Annotated[..., Depends()]` provide 422 on malformed input.
- DB access via asyncpg with parameterised queries; the API is read-only (no write endpoints).

## Accepted risks (documented)

| # | Risk | Mitigation |
| --- | --- | --- |
| R1 | No authentication/authorization (read-only API, in-scope exclusion) | Bind to localhost/private network or require proxy-level auth before public exposure |
| R2 | `server: uvicorn` header leaks identity | Strip at the reverse proxy |
| R3 | Placeholder `BIP_DB_PASSWORD` default (`reader_pass`) | Mandatory override in production; `bip_reader` must be read-only |
| R4 | No rate limiting on `POST /api/v1/reports/generate` (~1 s/op) | Add limiting at the proxy before public exposure |

## Recommendations for production

- TLS + reverse proxy with `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, CSP, `Referrer-Policy`.
- Run `pip-audit` / `npm audit` as part of the release process (no known-vulnerable runtime deps flagged during this phase).
- Rotate DB credentials; keep the reader role read-only.

## Conclusion

Security posture is appropriate for an internal read-only platform with no PII and no write surface. The four risks are deliberate, documented, and containable at deployment time. Details in `docs/Production/Security.md`.
