# Phase 20.1 Acceptance Checklist

| # | Criterion | Status |
|---|---|---|
| 1 | All ten report types are registered and generate a valid `ReportDocument` | **PASS** — 10/10 verified offline and live |
| 2 | No `ReportType` enum member is missing a generator | **PASS** — 1:1 audit + `len == 10` invariant |
| 3 | Report context is built from live repositories (machines, rings, metrics, timeline, quality, analytics, performance, health) | **PASS** — verified in generated documents |
| 4 | Generated reports are persisted to the filesystem store and survive separate requests | **PASS** — store round-trip + live list growth |
| 5 | Store writes are atomic (temp file + rename) | **PASS** — implemented and reviewed |
| 6 | `POST /api/v1/reports/generate` returns 200 for every valid report type | **PASS** — all ten types |
| 7 | `POST /generate` returns 400 for invalid report type and invalid dates | **PASS** |
| 8 | `GET /api/v1/reports` returns the paginated summary envelope | **PASS** — 200, correct total |
| 9 | `GET /api/v1/reports/{id}` returns the document and 404 for unknown ids | **PASS** |
| 10 | `GET /api/v1/reports/download/{id}` exports CSV, XLSX, PDF with correct magic bytes and Content-Disposition | **PASS** |
| 11 | Download returns 404 for unknown reports and 400 for invalid formats | **PASS** |
| 12 | `CollectorStatusGenerator` timezone bug fixed (no naive/aware comparison) | **PASS** |
| 13 | Report router DI uses the working `Annotated[...]` pattern (no 422) | **PASS** |
| 14 | Report service tuple-unpacking crash fixed (no 500 on generate) | **PASS** |
| 15 | Frontend report feature type-checks with `npm run lint:web` | **PASS** — 0 errors |
| 16 | Frontend production build succeeds (`npm run build:web`) | **PASS** |
| 17 | No non-existent imports (`lucide-react`, `date-fns`, `ReportGeneration.css`) remain in the report feature | **PASS** |
| 18 | Frontend API methods match verified live endpoints | **PASS** — generate / getReports / downloadReport |
| 19 | Backend changed modules compile (`py_compile`) | **PASS** |
| 20 | No database schema changes or migrations | **PASS** — none |
| 21 | No theme/design-system/routing changes outside Reports Engine scope | **PASS** |
| 22 | Existing endpoints and response shapes remain backward compatible | **PASS** |
| 23 | All 12 Phase 20.1 deliverables written to `bip/docs/` | **PASS** |

## Gate

**READY TO CLOSE PHASE 20.1.** All acceptance criteria are met; live verification passed 21/21 endpoint checks.
