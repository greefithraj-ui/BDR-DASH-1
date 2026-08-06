# Phase 20.1 Missing Generators Added

## Status

No additional generator implementations were required in Phase 20.1. The registry already covered all ten `ReportType` enum members at the start of the phase, so no type was left without a builder.

## Coverage Audit

`ReportGeneratorRegistry.create_default_registry()` was audited against `ReportType` (defined in `apps/api/app/models/report.py`):

| `ReportType` enum member | Value | Generator present |
|---|---|---|
| `EXECUTIVE_SUMMARY` | Executive Summary | Yes |
| `MACHINE_PERFORMANCE` | Machine Performance | Yes |
| `BATTERY_SUMMARY` | Battery Summary | Yes |
| `BATTERY_LIFECYCLE` | Battery Lifecycle | Yes |
| `QUALITY_SUMMARY` | Quality Summary | Yes |
| `ANALYTICS_SUMMARY` | Analytics Summary | Yes |
| `TIMELINE_REPORT` | Timeline Report | Yes |
| `OPERATIONS_SUMMARY` | Operations Summary | Yes |
| `SYSTEM_HEALTH` | System Health | Yes |
| `COLLECTOR_STATUS` | Collector Status | Yes |

The offline smoke test asserted `len(registry.generators) == 10`, guarding the 1:1 mapping. If a future `ReportType` member is added without a generator, this invariant fails loudly at startup / smoke time.

## What Was "Added" Instead

The gap found in Phase 20.1 was not a missing generator but correctness bugs in existing ones. Two were fixed:

1. **Collector Status generator** — timezone handling fixed (`datetime.now(timezone.utc)` + naive `last_seen` normalization). Previously the generator could raise a `ValueError` comparing naive and aware datetimes.
2. **Report context builder** — `_build_context` in `ReportService` crashed while preparing the shared context used by generators (mis-handled `(rows, total)` tuples from the rings/timeline repositories). Fixed in `apps/api/app/services/report.py`; this was the cause of the `500` on `POST /generate` before the fix.

## Registry Contract

`create_default_registry()` maps each `ReportType` to a generator instance at import time. Generators receive the built `ReportGenerationContext` plus a `ReportFilters` and emit a `ReportDocument`; they are pure functions of the context and never touch the database or the store directly.
