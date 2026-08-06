# Phase 22 Backward Compatibility Report

Phase 22 made no functional changes to any public surface. The API, web client, and data contracts are backward compatible with Phase 20.1.

## API surface

- **Routes**: unchanged — all 13 route groups and every path in `/api/openapi.json` remain (OpenAPI route-table check: `missing=[]`).
- **Response shapes**: unchanged — success envelopes `{data, meta}`, error model `{error: {code, message}}`, health contract `{status, version, service, timestamp, environment}` identical to the Phase 20.1 model.
- **Query params**: `FilterParams`/`PageQuery` via `Annotated[..., Depends()]` idiom unchanged; same 422 semantics.
- **Report endpoints**: list/generate/get/download unchanged; same 10 report types; same csv/xlsx/pdf formats; same 404/400 behaviour.
- **Status codes**: 200/400/404/422/307 semantics identical.

## Frontend

- `apiClient.ts` removed four helpers (`generateReport`, `downloadReport`, `postJson`, `downloadBlob`) plus two DTO types that were only used by deleted dead files. Live consumers (`useReports`, `ReportsPage`, `useTimeline`, shared query hooks) use the remaining surface and compile unchanged.
- `queryKeys.ts` removed keys not referenced by any live hook.
- Reports error-state rendering switched to the shared `ApiErrorState`/`describeApiError` pattern already used by other pages — a rendering path change, not an API change.

## Configuration

- `BIP_API_PREFIX` still defaults to `/api`; all URLs are unchanged.
- `api_v1_prefix` was removed but was never read anywhere (grep-verified), so no consumer is affected.
- Env-file discovery changed *where values come from* (`.env.development`/`.env.production` now actually load) but the variable names and defaults are unchanged. Before the fix the env files were never loaded; after the fix they load — this is a correction, and default-only deployments see identical values.

## Database / data

- No schema changes, no migrations, read-only access preserved.
- Report document store layout unchanged (`<temp>/bip_reports` or `BIP_REPORT_STORAGE_DIR`); previously generated documents remain readable.

## Removed code that had zero consumers

`grep` verification before deletion confirmed no live references to any removed module, component, hook, type, helper, or query key. The legacy `services/reports.py`/`repositories/reports.py` chain was never wired into any router.

## Conclusion

Backward compatible. All functional behavior, URLs, payloads, and data formats are unchanged; the only differences are the removal of unreferenced code and corrected config loading.
