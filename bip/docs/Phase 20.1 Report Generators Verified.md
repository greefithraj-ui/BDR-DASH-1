# Phase 20.1 Report Generators Verified

All ten report generators are registered in `ReportGeneratorRegistry.create_default_registry()` and were verified both offline (smoke script) and against the live API (each generator produced a real document from live database context).

## Registered Generators

| # | Report type (`ReportType` value) | Sections emitted (live) |
|---|---|---|
| 1 | Executive Summary | 7 |
| 2 | Machine Performance | 5 |
| 3 | Battery Summary | 5 |
| 4 | Battery Lifecycle | 7 |
| 5 | Quality Summary | 6 |
| 6 | Analytics Summary | 6 |
| 7 | Timeline Report | 5 |
| 8 | Operations Summary | 6 |
| 9 | System Health | 6 |
| 10 | Collector Status | 5 |

## Offline Verification (smoke script)

The offline smoke test instantiated the default registry and asserted:

- `len(registry.generators) == 10` — every `ReportType` has a registered generator, no type is left without a builder.
- Each generator returns a valid `ReportDocument` with non-empty `sections`.
- Section kinds are restricted to `summary`, `metrics`, `table`, `chart`.
- Documents round-trip through `ReportDocument.model_dump_json` / `model_validate_json` without data loss.

Result: **ALL_OK**.

## Live Verification

Each of the ten types was generated through `POST /api/v1/reports/generate?report_type=<name>` against the live uvicorn server (127.0.0.1:8100). All returned `200` with a stored document id and the section counts listed above. The generated documents contain real repository data — for example the Executive Summary reported "30 machine(s) tracked, 1000 battery ring(s), 6 metric(s) and 0 timeline event(s)", and the Top Machines table listed live machines (`aqc-*`) with health scores and firmware.

## Collector Status Generator Fix

`CollectorStatusGenerator` produced a timezone-mixing `ValueError` when it compared naive `last_seen` values to `datetime.now()`. Fixed to:

- build timestamps with `datetime.now(timezone.utc)`, and
- normalize naive `last_seen` values to aware UTC before comparing.

Verified: the Collector Status report now generates successfully (5 sections) on both offline and live runs.
