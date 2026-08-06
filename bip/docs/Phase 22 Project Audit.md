# Phase 22 Project Audit

Full-project audit executed with three parallel sweeps (frontend, backend, config/docs/contracts), then every finding was verified against source and, where confirmed, fixed. This document lists the findings, disposition, and the verified post-audit state.

## Audit findings and disposition

### Critical

| # | Finding | Disposition |
| --- | --- | --- |
| C1 | `D:\BDR\bip` is not under version control (no `.git`; `?? bip/` untracked in the parent `D:\BDR` repo) | Cannot be fixed inside scope (would require a commit). Documented as the release blocker in the Production Readiness Review, Deployment Review, and Release Process.md |

### High

| # | Finding | Disposition |
| --- | --- | --- |
| H1 | Env-file discovery (`SettingsConfigDict(env_file=".env")`) never found the repo's `.env.development`/`.env.production`; additionally the fix's first iteration escaped the project root and loaded the parent repo's `D:\BDR\.env` | Rewrote discovery in `config/settings.py`; verified from `D:\BDR\bip`, `D:\BDR\bip\apps\api`, and via `--app-dir apps/api`; health reports `environment=development`, CORS matches `.env.*` exactly |
| H2 | Dead broken code shipped: `exporters/options.py`, `ui/report_generation.py`, legacy DB report chain (`services/reports.py` + `repositories/reports.py`), unused `dependencies/settings.py` | Deleted all; DI wiring cleaned; every remaining module compiles |

### Medium

| # | Finding | Disposition |
| --- | --- | --- |
| M1 | Env version drift: `.env.*` = 0.2.5, code default = 0.3.0 | Synced to 0.3.0 |
| M2 | Frontend auth module (`features/auth/`) for a never-implemented feature | Deleted |
| M3 | Dead report artifacts from the Phase 20.1 refactor (3 components, 1 hook, 3 type files) | Deleted |
| M4 | `openapi-placeholder.json` stale | Deleted (live spec at `/api/openapi.json`) |
| M5 | Health contract drift: `contracts/health.ts` had 3 fields, `HealthResponse` model has 5 | `health.ts` rewritten; `check_health.py` validates the full contract |
| M6 | requirements.txt missing `openpyxl` + `reportlab` (both installed at runtime) | Added with version floors |
| M7 | Dead `api_v1_prefix` setting; dead `SETTINGS_ROWS` constant | Removed |
| M8 | README/package.json version 0.0.0, Phase-0 description | Version 0.3.0, live description |

### Low

| # | Finding | Disposition |
| --- | --- | --- |
| L1 | Unused imports: `ReportFilters`, `Optional` (report_generators); `utc_now` (schemas/common); `ErrorDetail`; `Card` (AdministrationTable); `Badge` (MachineInfoCard); `AiConversation` (useAiChat); `PredictionModel` (usePrediction) | Removed |
| L2 | Dead query keys: `executive`, `batteryIntelligence`, `analyticsHub`, `productAnalytics`, `qualityAnalytics` | Removed |
| L3 | Dead `apiClient.ts` helpers (`postJson`, `downloadBlob`, `generateReport`, `downloadReport`) + `ReportSectionDto`/`ReportDocumentDto` | Removed |
| L4 | `check_health.py` printed raw body without validation | Rewritten with contract validation + exit codes |
| L5 | Single 1.15 MB production bundle | Split via `manualChunks` |
| L6 | Root `package.json` had no `apps/web` version alignment | Both now 0.3.0 |

## Verified post-audit state

- **Backend**: 56 modules under `apps/api/app` (13 routers, 15 repositories, 13 services, schemas, models, config, storage); all compile.
- **Frontend**: `apps/web/src` contains only live feature code; `tsc --noEmit` clean; production build clean.
- **Contracts**: `shared/contracts/health.ts` matches `HealthResponse`; no placeholder specs remain.
- **Scripts**: `check_health.py` exits 0 on valid contract, nonzero on failure.
- **Env**: discovery bound to the project root; all three `.env.*` files at version 0.3.0.
