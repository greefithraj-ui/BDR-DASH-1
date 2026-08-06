# Phase 20.1 Files Modified

Phase 20.1 hardens the Phase 20 Reports Engine: it replaces the mock/static report context with live repository-backed data, persists generated documents to a filesystem store, fixes the report service and DI wiring so all report endpoints run against the live database, corrects exporter bugs, and makes the frontend report feature type-safe against the real API contracts. No changes outside the Reports Engine scope.

## Backend — Added

- `apps/api/app/storage/__init__.py` — exports the new store module.
- `apps/api/app/storage/report_store.py` — `ReportStore`, a filesystem JSON cache for generated report documents:
  - `save` writes `<report_id>.json` atomically (temp file + rename), so a crash never leaves a half-written document.
  - `get` / `list_documents` / `list_summaries` / `get_summary` read documents back; summaries support `date_from`/`date_to` narrowing.
  - Default directory is `<temp>/bip_reports`; the store is safe to construct per request because it only resolves the same on-disk location.

## Backend — Modified

- `apps/api/app/models/report.py` — added `ReportFilters.from_filter_params(filters)` so the router can convert the generic query `FilterParams`/machine/ring/quality/timeline filter lists into a `ReportFilters` model without leaking schema imports into the domain model.
- `apps/api/app/services/report.py` — `ReportService` rewritten to build a real `ReportGenerationContext` from the live repositories:
  - Injects `MetricsRepository`, `MachinesRepository`, `RingsRepository`, `TimelineRepository`, `QualityRepository`, `AnalyticsRepository`, `PerformanceRepository`, `HealthRepository`, `Settings`, `ReportStore`, generator registry, and exporter registry.
  - `generate_report` runs the registered generator and persists the document through the store.
  - `get_report_document` / `get_report` / `list_reports` read from the store; `download_report` exports bytes and raises `ResourceNotFoundError` for unknown ids.
  - **Bug fixed**: `_build_context` unpacked `(rows, total)` tuples returned by `list_rings`/`list_events` as if the two values were interchangeable; it now indexes the tuple explicitly, which previously caused a runtime crash when generating reports (the 500 on `POST /generate`).
- `apps/api/app/dependencies/services.py` — added `get_report_service`, wiring all repositories, `ReportStore(settings.report_storage_dir)`, `ReportGeneratorRegistry.create_default_registry()`, and `ExporterRegistry.create_default_registry()`. The legacy `get_reports_service` is retained for the database-backed `ReportSummary` listing.
- `apps/api/app/routers/reports.py` — rewritten:
  - List endpoint now declares `filters: Annotated[FilterParams, Depends()]` and `page: Annotated[PageQuery, Depends()]` matching the idiom used by every other router (the prior `Optional[X] = Depends()` form produced a 422 on `GET /api/v1/reports`).
  - `POST /generate` validates the report type against the enum and ISO-8601 dates, returning 400 for invalid input.
  - `GET /download/{report_id}` exports the stored document as CSV/XLSX/PDF (`StreamingResponse` with `Content-Disposition`), 400 on an unknown format, 404 via `ResourceNotFoundError`.
  - `GET /{report_id}` returns 404 when the document is missing.
- `apps/api/app/exporters/__init__.py` — exporters rewritten:
  - `CsvExporter` writes through `StringIO` and encodes UTF-8 (previously produced invalid UTF-8 in some cases).
  - `ExcelExporter` fixed the bold header row index (applies styles to row 0) and handles all section types.
  - `PdfExporter` uses reportlab platypus with a page header/footer via `decorate` and `repeatRows` tables; handles summary/metrics/table/chart sections.
  - `ExporterRegistry.create_default_registry()` registers all three formats.
- `apps/api/app/report_generators/__init__.py` — `CollectorStatusGenerator` timezone fix: last-seen normalization now uses `datetime.now(timezone.utc)` and treats naive `last_seen` values as UTC instead of mixing naive/aware datetimes.

## Frontend — Modified

- `apps/web/src/lib/apiClient.ts` — added `ReportSectionDto` and `ReportDocumentDto` types plus `postJson`, `downloadBlob`, `generateReport`, and `downloadReport` methods mirroring the real API contracts (`/v1/reports/generate`, `/v1/reports/download/{id}`).
- `apps/web/src/features/reports/types/reportTypes.ts` — types aligned to the snake_case API payloads (`report_type`, `generated_at`, `time_range`, `ReportFilters`, `ReportDocument`).
- `apps/web/src/features/reports/types/reportFilters.ts` and `types/reportErrors.ts` — now re-export their types from `reportTypes.ts` (single source of truth).
- `apps/web/src/features/reports/hooks/useReportGeneration.ts` — rewritten to use `apiClient`; `ReportType` imported as a value; DTO → `ReportDocument` conversions are confined to the hook boundary with explicit casts.
- `apps/web/src/features/reports/components/ReportGeneration.tsx` — rewritten with native controls and correct imports; `onClose` prop; renders the generated report preview with download buttons.
- `apps/web/src/features/reports/components/ReportHistory.tsx` — rewritten to use `apiClient.getReports` and the shared `formatDateTime` helper (removes the `date-fns` dependency).
- `apps/web/src/features/reports/components/ReportDownload.tsx` — rewritten with native buttons and `apiClient.downloadReport`; formats derived from `ExportFormat`.
- `apps/web/src/features/reports/ReportsPage.tsx` — restored to the working Phase 10 imports (`./useReports`, `./components/...`, `./reports.css`); error state renders `reports.error.message`.

## Not Changed

- No database schema changes, no migrations, no theme/design-system changes, no routing changes, no layout redesigns.
- `apps/api/app/services/reports.py` and the DB-backed `ReportSummary` listing remain untouched and backward compatible.
