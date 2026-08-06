# Phase 20.1 Technical Debt Report

## 1. Generators in a Single Module (medium)

All ten generator classes live in one large `apps/api/app/report_generators/__init__.py`. At the current scale it works, but it mixes import-time registry setup with generator implementations and grows every time a report type is added.

**Recommendation:** split into `report_generators/base.py`, `report_generators/registry.py`, and `report_generators/generators/*.py` (one file per generator). Preferable when adding the next report type.

## 2. `settings.report_storage_dir` Default (low)

The setting defaults to `""`, which maps to the OS temp directory (`<temp>/bip_reports`). Reports stored in a temp dir are wiped on OS cleanup/reboot and are machine-local.

**Recommendation:** configure a persistent path (e.g. `bip/data/reports`) in the deployment settings so generated reports survive restarts. No code change needed — the setting already exists.

## 3. DTO→Domain Casts in `useReportGeneration` (low)

The hook casts API DTOs to `ReportDocument` with explicit casts at the boundary. This is the correct seam, but the `ReportDocument` domain type and the DTO are structurally similar, so drift between API payloads and the domain type would only surface at runtime.

**Recommendation:** generate/keep the DTO types strictly aligned with the backend `ReportDocument`/`ReportSection` models (a lightweight generator or a checked fixture test on both sides of the boundary).

## 4. Frontend Duplicate Report Type Sources (low)

`ReportType` / `ExportFormat` display names exist in both the backend enum values and the frontend (`types/reportTypes.ts`). If a report type is renamed, the mismatch shows only as a 400 at runtime (already handled gracefully by the UI).

**Recommendation:** derive the frontend list from `/api/v1/reports/meta`-style endpoint in a future phase, or add a contract test asserting the frontend list equals the backend enum values.

## 5. Chart Sections Are Placeholders (informational)

Report "chart" sections carry structured data only; CSV/XLSX/PDF emit them as text placeholders, and the frontend renders placeholder badges. This is an intentional, documented limitation, not a bug — rasterized charts would require a charting backend and are out of scope for the Reports Engine phase.

## 6. Error Envelope Inconsistency (low, pre-existing)

`GET /reports/{id}` uses `detail: "Report document not found"` while download uses the structured `not_found` envelope. Both are 404s; unifying on the structured envelope would be cosmetic-only cleanup.

## 7. No Test Automation for Report Endpoints (medium)

Verification in this phase was performed via smoke/live scripts (offline and HTTP). There is no committed pytest coverage for `generate`/`list`/`get`/`download` including the error paths.

**Recommendation:** add a pytest module that exercises the reports router with a temporary store directory and mocked repositories, so the 500/422 regressions fixed here are locked in.

## 8. `exporters/options.py` Stale Module (low)

An earlier `ExportOptions` module may remain unused after `ExportOptions`/`ExportFormat` were consolidated into `exporters/__init__.py`/`models/report.py`.

**Recommendation:** verify and remove stale export helper modules to avoid import confusion.
