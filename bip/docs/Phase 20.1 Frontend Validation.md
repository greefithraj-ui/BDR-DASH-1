# Phase 20.1 Frontend Validation

## Scope

The frontend report feature was made type-safe against the real Phase 20 API contracts and cleaned of imports that did not exist or were misused. Changes are confined to `apps/web/src/features/reports/` and `apps/web/src/lib/apiClient.ts`.

## Files Changed

- `lib/apiClient.ts` — added `ReportSectionDto`, `ReportDocumentDto`, `postJson`, `downloadBlob`, `generateReport`, `downloadReport`.
- `features/reports/types/reportTypes.ts` — snake_case API-aligned types (`report_type`, `generated_at`, `time_range`, `ReportFilters`, `ReportDocument`).
- `features/reports/types/reportFilters.ts` / `reportErrors.ts` — re-export from `reportTypes.ts`.
- `features/reports/hooks/useReportGeneration.ts` — uses `apiClient`; `ReportType` imported as a value (enum usable at runtime); DTO→domain conversions at the hook boundary.
- `features/reports/components/ReportGeneration.tsx` — native controls, correct imports, `onClose` prop, preview + download buttons.
- `features/reports/components/ReportHistory.tsx` — `apiClient.getReports` + shared `formatDateTime`.
- `features/reports/components/ReportDownload.tsx` — native buttons + `apiClient.downloadReport`; formats from `ExportFormat`.
- `features/reports/ReportsPage.tsx` — restored to the working Phase 10 imports; error render uses `reports.error.message`.

## Removed / Avoided

- `lucide-react` icon imports (not a project dependency).
- `date-fns` (not a dependency) — replaced with the shared `lib/format` helper.
- Design-system `Input` / `Select` / `DatePicker` components that do not exist.
- `ReportGeneration.css` import — the file does not exist; the feature uses `reports.css`.
- Unnecessary `ReportType` type-only imports (imported as a value where the enum is used at runtime).

## Static Checks

- `npm run lint:web` (tsc --noEmit): **0 errors**.
- `npm run build:web` (tsc --noEmit && vite build): **PASS** — 875 modules transformed, `dist/` emitted.
- No `any` / `as any` / `as unknown` / `@ts-ignore` introduced; DTO→domain casts are confined to `useReportGeneration.ts` at the API boundary.

## Runtime Contract Match

The API methods now target the exact endpoints verified live:

- `generateReport(reportType, options)` → `POST /v1/reports/generate?report_type=…`
- `getReports()` → `GET /v1/reports`
- `downloadReport(id, format)` → `GET /v1/reports/download/{id}?format=…`

DTO field names match the live payloads (e.g. `report_type`, `generated_at`, `time_range`, `sections[]` with `{ title, kind, ... }`), so the feature renders real server data without transformation mismatches.

## Conclusion

The report frontend compiles cleanly and is aligned with the verified API contract. **PASS.**
