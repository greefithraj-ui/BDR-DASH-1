# Battery Intelligence Platform — Security Notes

Version 0.3.0.

## Security posture summary

| Area | Status | Evidence |
| --- | --- | --- |
| CORS | Enforced; disallowed origins rejected with 400 | Preflight test: allowed `http://localhost:3100`, rejected `http://evil.example.com` |
| Credentials | Never logged | `db/session.py` logs host/port/database only |
| Secrets at rest | Env files gitignored (`.env`, `.env.*`, keep `.env.example`) | `.gitignore` |
| Injection | FastAPI/pydantic validation on all inputs; parameterised DB access via asyncpg | 422 on malformed params, parameterised queries |
| Server banner | `server: uvicorn` header present | Recommend hiding behind reverse proxy |
| AuthN/AuthZ | **Not implemented** — read-only, in-scope exclusion for Phase 22 | See below |
| TLS | Terminated by reverse proxy in production | No TLS in the API itself |

## Known limits (accepted)

1. **No authentication/authorization.** The API serves read-only data and intentionally has no auth (explicitly out of scope for this phase). In production it must be bound to localhost / a private network, or sit behind a reverse proxy that enforces access control.
2. **`server: uvicorn` banner** leaks the server identity. Terminate at a reverse proxy and strip the header.
3. **Placeholder DB password** `reader_pass` is the code default. Production must override `BIP_DB_PASSWORD`; a `bip_reader` role with no write privileges is mandatory.
4. **No rate limiting** on report generation (`POST /api/v1/reports/generate`, ~1 s each). Protect at the proxy or add limiting before public exposure.

## Recommendations for production

- Put the API behind TLS + reverse proxy; set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy`, and a strict `Content-Type` header.
- Bind the API to `127.0.0.1` and proxy externally; never expose it raw on a public interface without auth.
- Rotate `BIP_DB_PASSWORD`; keep the `bip_reader` role read-only.
- Run the frontend as static files with `VITE_BIP_API_BASE_URL` pointing at the proxied API origin.
- Keep the dependency tree current (`pip-audit` / `npm audit`). During Phase 22 no known-vulnerable runtime deps were flagged by build tooling.

## Audit trail of the security review

Performed during Phase 22: response-header inspection (health + CORS preflight), cross-origin rejection test, repo-wide secrets scan (`password|secret|api[_-]?key|BEGIN (RSA|PRIVATE)|AKIA`), gitignore review, and DB credential logging check. No hardcoded secrets were found in source outside the documented `.env.*` files (which are gitignored).
