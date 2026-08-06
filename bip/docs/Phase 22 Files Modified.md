# Phase 22 Files Modified

Phase 22 is the production-readiness and final-validation phase. Changes are limited to dead-code removal, configuration/version/contract drift fixes, build hygiene, and documentation. No runtime behaviour of the 13 API route groups was changed.

## Backend — Deleted

- `apps/api/app/exporters/options.py` — broken, unused exporter-options module.
- `apps/api/app/ui/report_generation.py` — broken, unused (unported JS/TS state class); the whole `apps/api/app/ui/` directory was removed.
- `apps/api/app/dependencies/settings.py` — `provide_settings` was never used by any router.
- `apps/api/app/services/reports.py` + `apps/api/app/repositories/reports.py` — legacy DB-backed `ReportsService`/`ReportsRepository` chain never referenced by any router (superseded by `services/report.py` + `storage/report_store.py` in Phase 20.1).
- `shared/contracts/openapi-placeholder.json` — stale placeholder for a spec now served live at `/api/openapi.json`.

## Backend — Modified

- `apps/api/app/config/settings.py`:
  - Rewrote env-file discovery. `_project_root()` finds the nearest ancestor of the CWD containing an `apps/` directory; `_find_env_file()` walks up from the CWD but **stops at the project root**, so the API never loads a parent repository's `.env` (previously it loaded `D:\BDR\.env`).
  - `_default_env_file()` resolves `.env` first, then `.env.{BIP_ENVIRONMENT}`; falls back to the file name.
  - Removed unused `api_v1_prefix`; kept `api_prefix` (used by `repositories/settings.py` SET-4).
- `requirements.txt` — added `openpyxl>=3.1.5` and `reportlab>=4.2.0` (both already installed: openpyxl 3.1.5, reportlab 5.0.0).
- `apps/api/app/dependencies/services.py` — removed `get_reports_service` and the `ReportsService`/`ReportsRepository` imports.
- `apps/api/app/services/__init__.py` — removed `ReportsService` export.
- `apps/api/app/repositories/__init__.py` — removed `ReportsRepository` and `ReadOnlyRepository` exports (kept `InMemoryListRepository`).
- `apps/api/app/schemas/common.py` — removed unused `utc_now` import and the dead `ErrorDetail` class.
- `apps/api/app/schemas/__init__.py` — exports `ErrorModel`, `SuccessEnvelope`, `FilterParams`, `PageQuery`, `PaginatedResponse`.
- `apps/api/app/report_generators/__init__.py` — removed unused `Optional` and `ReportFilters` imports.
- `apps/api/app/repositories/settings.py` — removed dead `SETTINGS_ROWS = ()`.
- `apps/api/app/main.py` — description updated from the Phase-0 placeholder text to the live services description.

## Frontend — Deleted

- `apps/web/src/features/auth/` (auth.client.ts, auth.types.ts) — auth was never implemented.
- `apps/web/src/features/reports/components/ReportGeneration.tsx`, `ReportDownload.tsx`, `ReportHistory.tsx` — superseded by the Phase 20.1 `ReportCard`/`ReportsGrid`/`ReportTable`/`ReportHistoryPanel` set.
- `apps/web/src/features/reports/hooks/useReportGeneration.ts` — replaced by `useReports.ts`.
- `apps/web/src/features/reports/types/reportTypes.ts`, `reportErrors.ts`, `reportFilters.ts` — replaced by `reports.types.ts`.
- `apps/web/src/types/app.ts` — unused global types file.
- `apps/web/src/docs/Phase20_*.md` — stray scratch docs in source.
- `apps/web/src/assets/README.md` — placeholder.

## Frontend — Modified

- `apps/web/src/lib/apiClient.ts` — removed dead `ReportSectionDto`/`ReportDocumentDto` types and `postJson`/`downloadBlob`/`generateReport`/`downloadReport` (only used by the deleted files). Kept `getReports`, `getTimelineEvents`, `fetchAllPages`.
- `apps/web/src/lib/queryKeys.ts` — removed dead keys: `executive`, `batteryIntelligence`, `analyticsHub`, `productAnalytics`, `qualityAnalytics`.
- `apps/web/src/features/administration/components/AdministrationTable.tsx` — removed unused `Card` import.
- `apps/web/src/features/machine-explorer/components/MachineInfoCard.tsx` — removed unused `Badge` import.
- `apps/web/src/features/ai-intelligence/useAiChat.ts` — removed unused `AiConversation` import.
- `apps/web/src/features/prediction/usePrediction.ts` — removed unused `PredictionModel` import.
- `apps/web/src/features/reports/ReportsPage.tsx` — error state now uses the shared `ApiErrorState` + `describeApiError` + retry via `reports.refresh()`.
- `vite.config.ts` — added `build.chunkSizeWarningLimit: 800` and `manualChunks` splitting `echarts` and `react-vendor` (main index chunk 1.15 MB → 262 kB).
- `package.json` (root) — version `0.3.0`, description updated.
- `apps/web/package.json` — version `0.3.0`.

## Contracts / Scripts / Config — Modified

- `shared/contracts/health.ts` — rewritten to the real 5-field payload (`status`, `version`, `service`, `timestamp`, `environment`).
- `scripts/check_health.py` — rewritten: validates HTTP 200, `status=="ok"`, service name, version; JSON errors and contract mismatches exit nonzero.
- `.env.example`, `.env.development`, `.env.production` — `BIP_API_VERSION` 0.2.5 → 0.3.0.

## Documentation — Added

- `docs/Production/` — Deployment.md, Configuration.md, Operations.md, Security.md, Troubleshooting.md, API.md, Release Process.md, Performance.md.
- 15 `docs/Phase 22 *.md` deliverables.

## Not Changed

- No database schema changes, no migrations.
- No routing/layout/theme changes; the 13 route groups behave identically.
- No new dependencies in `package.json` (openpyxl/reportlab were already installed at runtime and are now pinned).
