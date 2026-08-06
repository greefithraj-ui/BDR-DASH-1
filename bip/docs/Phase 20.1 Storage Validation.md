# Phase 20.1 Storage Validation

## Design

`ReportStore` (`apps/api/app/storage/report_store.py`) persists generated `ReportDocument` instances as JSON files on disk. The platform database is read-only (no INSERT/UPDATE/DELETE), so reports cannot be stored in PostgreSQL; the filesystem cache is the chosen persistence layer.

- Directory: `settings.report_storage_dir` when set, otherwise `<temp>/bip_reports` (verified live at `%TEMP%\bip_reports`).
- Layout: one file per document, `<report_id>.json`.
- Atomic writes: `save` writes `.<id>.tmp` then renames over `.<id>.json` — a crash mid-write never leaves a corrupt final document.
- Ordering: `list_documents` sorts by `generated_at` descending (newest first).
- Filtering: `list_summaries(date_from=…, date_to=…)` narrows by generation timestamp.
- Tolerance: `get` returns `None` on parse failure rather than crashing a request.

## Validation Performed

### Offline (smoke script)

- Saved a `ReportDocument` with all four section kinds, then:
  - `get(id)` returned an equal document (`model_validate_json` round-trip).
  - `list_documents` contained the document.
  - `get_summary(id)` returned the expected `ReportSummary`.
- Verified the temp-file + rename path leaves exactly one final `.json` per document (no stray `.tmp` files after save).

### Live

- Generated reports through `POST /api/v1/reports/generate` are immediately retrievable via `GET /api/v1/reports/{id}` — proving `generate_report` persisted through the store and `get_report_document` read it back.
- `GET /api/v1/reports` listed 11 stored documents (10 from the offline smoke run + new live generations), sorted newest first, confirming cross-process persistence (the smoke script and the live server share the same default directory).
- After generating all ten report types live, the list total grew accordingly — documents persisted across separate HTTP requests.

## Edge Cases

| Case | Behavior | Verified |
|---|---|---|
| Unknown id | `get` → `None` → 404 | Yes (`download` and `get` endpoints) |
| Corrupt/partial JSON | `get` returns `None` (no crash) | Code review; handler degrades to 404 |
| Concurrent save | Atomic rename is last-writer-wins, no torn files | Code review |
| Empty storage dir | `list_documents` → `[]`, total 0 | Code review |

## Conclusion

The store round-trips documents correctly, persists across processes, and never writes partial files. **PASS.**
