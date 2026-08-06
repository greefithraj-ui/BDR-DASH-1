# Battery Intelligence Platform — Release Process

Version 0.3.0.

## Version policy

Single semantic version drives the whole platform. It lives in exactly three places that must stay in sync:

1. `package.json` (root) — `version`
2. `apps/web/package.json` — `version`
3. `BIP_API_VERSION` in `.env.example`, `.env.development`, `.env.production` — and the default in `apps/api/app/config/settings.py`

## Release checklist

1. **Bump** all version locations above (three files + settings default) with the same number.
2. **Verify health** reports the new version: `npm run health:api` (expect `v<version>`).
3. **Run the validation suites**:
   - API: `python C:\Users\meshe\AppData\Local\Temp\opencode\api_validation.py` — expect `RESULT: ok=38 fail=0`.
   - Frontend: `npm run lint:web` (tsc --noEmit) and `npm run build:web`.
   - Backend compile: `Get-ChildItem apps/api/app -Recurse -Filter *.py | python -m py_compile` — all pass.
4. **Confirm no dead files** regressed: the tree walks in Phase 22 Final Verification (docs/Phase 22 Final Verification.md) are the baseline.
5. **Regenerate OpenAPI**: `GET /api/openapi.json` — verify no routes disappeared (route table in docs/Production/API.md).
6. **Release notes**: record the changeset in the Completion Report, marking the git status of `bip/` (see blocker note below).

## Blocking issue before external release

`bip/` is **not under version control** (no `.git`; untracked in the parent `D:\BDR` repository). Until the tree is committed, no externally verifiable release can be cut. Recommended action: `git init` inside `bip/` (or add it to the parent repo), confirm `.gitignore` is respected (`.env.*` excluded, `.env.example` kept), then commit the baseline.

## Post-release

- Restart the API so the new settings and version are live.
- Re-run `npm run health:api` against the deployed instance.
