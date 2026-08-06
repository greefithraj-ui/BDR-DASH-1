# Phase 20.1 Export Validation

## Exporters

`apps/api/app/exporters/__init__.py` provides three exporters registered through `ExporterRegistry.create_default_registry()`:

| Format | Exporter | Output |
|---|---|---|
| CSV | `CsvExporter` | UTF-8 text via `StringIO` |
| XLSX | `ExcelExporter` | zip container (openpyxl) |
| PDF | `PdfExporter` | reportlab platypus `SimpleDocTemplate` |

All exporters consume the same `ReportDocument` structure (sections of kind `summary`, `metrics`, `table`, `chart`) so every report type is exportable in every format.

## Fixes Applied This Phase

1. **CSV UTF-8 encoding** — CSV output now passes through `StringIO` and is explicitly UTF-8 encoded. Earlier output could be written with a default encoding that broke non-ASCII content.
2. **Excel header row** — the bold header style is now applied to row 0 (the data header) instead of row 1, so exported workbooks have a correctly formatted header.
3. **PDF layout** — platypus flowables for all section kinds; tables use `repeatRows` for multi-page continuation; page header/footer rendered via `SimpleDocTemplate.decorate`.

## Validation

### Offline (smoke script)

- CSV decodes as UTF-8 without errors and begins with report metadata.
- XLSX output starts with the `PK` zip magic bytes and opens with openpyxl (readable workbook).
- PDF output starts with `%PDF-`.
- All three exporters ran successfully over a document containing summary, metrics, table, and chart sections.

### Live

Downloaded a generated Executive Summary document in all three formats via `GET /api/v1/reports/download/{id}?format={csv|xlsx|pdf}`:

| Format | HTTP | Size | Magic bytes | Content-Disposition |
|---|---|---|---|---|
| CSV | 200 | ~20.8 KB | `Repor` (metadata header) | `attachment; filename=report_<id>.csv` |
| XLSX | 200 | ~23.7 KB | `PK\x03\x04` | `attachment; filename=report_<id>.xlsx` |
| PDF | 200 | ~52.3 KB | `%PDF-` | `attachment; filename=report_<id>.pdf` |

The CSV body contained the real report content (Report Metadata, Sections, Top Machines by Health Score with live machine rows, Ring Summary by Name, Health Score Trend placeholder, Report Footer).

## Edge Cases

| Case | Behavior | Verified |
|---|---|---|
| Unknown format | 400 `Invalid export format: <fmt>` | Yes |
| Empty sections | Exporters produce a minimal valid file | Code review |
| Multi-page PDF tables | `repeatRows` repeats the header on each page | Code review |

## Conclusion

All three exporters produce structurally valid files (verified magic bytes) with correct content, media types, and download headers. **PASS.**
