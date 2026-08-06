# Phase 20.1 Download API Validation

## Endpoint

`GET /api/v1/reports/download/{report_id}?format=csv|xlsx|pdf`

Defined in `apps/api/app/routers/reports.py`. Behavior:

- Looks the report up in the `ReportStore`; unknown id → `ResourceNotFoundError` → `404`.
- Validates `format` against `ExportFormat`; unknown format → `400 Invalid export format: <fmt>`.
- Returns `StreamingResponse` with the exporter bytes, correct media type, and `Content-Disposition: attachment; filename=report_<id>.<ext>`.

## Test Matrix (live, uvicorn 127.0.0.1:8100)

| Case | Request | Expected | Result |
|---|---|---|---|
| Download CSV | `/download/{id}?format=csv` | 200, text/csv, UTF-8 | **PASS** |
| Download XLSX | `/download/{id}?format=xlsx` | 200, `PK\x03\x04` magic | **PASS** |
| Download PDF | `/download/{id}?format=pdf` | 200, `%PDF-` magic | **PASS** |
| Unknown report | `/download/does-not-exist-123?format=csv` | 404 `not_found` | **PASS** |
| Unknown format | `/download/{id}?format=docx` | 400 `Invalid export format` | **PASS** |
| Default format | `/download/{id}` | 200, CSV (default `format=csv`) | **PASS** (default param verified in code) |

Observed 404 body: `{"error":"not_found","message":"report 'does-not-exist-123' was not found","status_code":404,...}` — the platform's standard error envelope.

Observed 400 body: `{"error":"http_error","message":"Invalid export format: docx","status_code":400,...}`.

## Route Note

The canonical path is `/reports/download/{report_id}` (the literal `download` segment precedes the id). The frontend `apiClient.downloadReport` already calls this exact URL:

```ts
downloadBlob(`/v1/reports/download/${encodeURIComponent(reportId)}?format=${encodeURIComponent(format)}`)
```

An early manual test used `/reports/{id}/download` (id before `download`), which correctly returned the framework 404 — the route was never wrong; the test URL was. Confirmed against the OpenAPI schema: `GET /api/v1/reports/download/{report_id}` is the registered path.

## Content Verification

- CSV body contained the full report content (metadata + all sections).
- XLSX and PDF files passed magic-byte checks and had realistic byte sizes (23.7 KB / 52.3 KB), indicating well-formed documents rather than empty stubs.

## Conclusion

The download API is correct end-to-end: valid downloads succeed with proper headers, and both error paths (missing report, invalid format) return the documented status codes and envelopes. **PASS.**
