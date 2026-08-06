# Phase 20.1 Backward Compatibility Report

## Summary

Phase 20.1 changes are additive and self-contained within the Reports Engine. No existing public endpoint contract, database table, or route path changed. Existing consumers keep working unchanged.

## API Contract Compatibility

| Endpoint | Phase 20 behavior | Phase 20.1 behavior | Compatible |
|---|---|---|---|
| `GET /api/v1/reports` | List report summaries | Same envelope; now served from the `ReportStore` summaries with the same `PaginatedResponse` shape | Yes |
| `GET /api/v1/reports/{report_id}` | Get report document | Same envelope and document shape | Yes |
| `POST /api/v1/reports/generate` | Generate report | Same query parameters (`report_type`, `date_from`, `date_to`, machine/ring/product/quality/timeline filters), same `ReportDocument` response; now actually succeeds (was 500) | Yes |
| `GET /api/v1/reports/download/{report_id}` | Download export | Same route, query param `format=csv|xlsx|pdf`, same media types and `Content-Disposition` | Yes |

- **No endpoint paths changed** and **no response field names changed** — the API is additive.
- The DB-backed `ReportSummary` service (`services/reports.py`, `ReportsRepository`) and its consumers are untouched.
- The reports router previously could not serve `GET /reports` (422) or `POST /generate` (500) at runtime; Phase 20.1 makes them work — strictly an improvement, no regression risk.

## Frontend Compatibility

- The report feature files were rewritten to match the real API, but the component public surfaces (`ReportsPage`, `ReportGeneration`, `ReportHistory`, `ReportDownload`, `useReportGeneration`) keep the same props and responsibilities as Phase 10/18.1 consumers expect.
- `reportFilters.ts` and `reportErrors.ts` still export the same symbol names (`ReportFilters`, `ReportGenerationError`) — now re-exported from `reportTypes.ts`.
- `lib/apiClient.ts` only gains new methods; existing methods unchanged.

## Dependency & Storage Compatibility

- The `ReportStore` default directory is the platform temp directory; no existing data directory is touched unless `settings.report_storage_dir` is explicitly configured.
- No new runtime dependencies were added on the backend (reportlab/openpyxl already present) or the frontend (removed `date-fns`/`lucide-react` usage, added none).
- No migrations, no schema changes, no settings schema changes.

## Verified Regression Surface

- Frontend `npm run lint:web` 0 errors and `npm run build:web` pass over the whole web workspace (not just the report feature), confirming no cross-feature breakage.
- Live API health, list, generate, get, and download endpoints all return documented envelopes.

## Conclusion

Phase 20.1 is backward compatible. It fixes runtime failures and adds a storage layer without altering any contract, dependency, or database surface.
