# Phase 22 Cleanup Report

Dead code, stale artifacts, and drift removed in Phase 22. All removals were verified to be unreferenced before deletion (grep across routers/deps/imports), and the tree was re-walked afterwards.

## Removed — backend

| Path | Why |
| --- | --- |
| `apps/api/app/exporters/options.py` | Broken, never imported |
| `apps/api/app/ui/report_generation.py` | Broken, unused (unported JS/TS state class); directory `app/ui/` removed entirely |
| `apps/api/app/dependencies/settings.py` | `provide_settings` unused by any router |
| `apps/api/app/services/reports.py` | Legacy DB-backed report chain, never referenced |
| `apps/api/app/repositories/reports.py` | Same chain; superseded by `storage/report_store.py` |
| `shared/contracts/openapi-placeholder.json` | Stale; live spec at `/api/openapi.json` |

Plus export/import cleanups: `dependencies/services.py` (`get_reports_service`), `services/__init__.py` (`ReportsService`), `repositories/__init__.py` (`ReportsRepository`, `ReadOnlyRepository`), `schemas/common.py` (`ErrorDetail`, `utc_now`), `report_generators/__init__.py` (`Optional`, `ReportFilters`), `repositories/settings.py` (`SETTINGS_ROWS`), `config/settings.py` (`api_v1_prefix`).

## Removed — frontend

| Path | Why |
| --- | --- |
| `features/auth/auth.client.ts`, `auth.types.ts` | Auth never implemented |
| `features/reports/components/ReportGeneration.tsx`, `ReportDownload.tsx`, `ReportHistory.tsx` | Superseded by Phase 20.1 components |
| `features/reports/hooks/useReportGeneration.ts` | Replaced by `useReports.ts` |
| `features/reports/types/reportTypes.ts`, `reportErrors.ts`, `reportFilters.ts` | Replaced by `reports.types.ts` |
| `src/types/app.ts` | Unused |
| `src/docs/Phase20_*.md` | Stray scratch docs in source |
| `assets/README.md` | Placeholder |

Plus: dead `apiClient.ts` helpers/types, dead query keys, and 7 unused imports across 4 feature files.

## Other cleanup

- `scripts/check_health.py` — rewritten from a raw-body printer to a contract validator with exit codes.
- `apps/api/app/main.py` — Phase-0 placeholder description → live description.
- Root + web `package.json` — 0.0.0 → 0.3.0, real description.
- `.env.example/.env.development/.env.production` — version 0.2.5 → 0.3.0.
- `shared/contracts/health.ts` — 3-field → 5-field contract.

## Post-cleanup verification

- Backend: all modules compile (`py_compile` sweep).
- Frontend: `tsc --noEmit` clean; production build clean.
- Live API: full 38/38 API suite re-run after cleanup.
- Tree walk (this phase) shows only live, referenced code remains in `apps/api/app` and `apps/web/src`.
- No straggler directories left empty: `app/ui/`, `features/auth/`, `src/docs/`, `src/types/` were removed with their contents.
