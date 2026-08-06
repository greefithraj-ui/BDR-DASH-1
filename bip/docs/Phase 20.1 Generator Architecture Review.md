# Phase 20.1 Generator Architecture Review

## Layout

```
apps/api/app/report_generators/__init__.py
```

- `BaseReportGenerator` — abstract generator: `generate(report_type, context, filters) -> ReportDocument`.
- One concrete generator class per report type (e.g. `ExecutiveSummaryGenerator`, `MachinePerformanceGenerator`, … `CollectorStatusGenerator`).
- `ReportGeneratorRegistry` — maps `ReportType` → generator instance; `create_default_registry()` registers all ten.

Generators never call repositories or the store. They receive a fully-built `ReportGenerationContext` from `ReportService._build_context` and return a `ReportDocument` composed of `ReportSection` items (kind `summary` | `metrics` | `table` | `chart`).

## Context Assembly

`ReportService._build_context(filters)` now builds the context from live repositories (the Phase 20.1 change):

- `MetricSummary` list from `MetricsRepository.list_metrics`.
- Machines with fleet-stats mapping (health score, connection, firmware, last seen) from `MachinesRepository`.
- `Ring` rows from `RingsRepository.list_rings` — **indexed as `(rows, total)[0]`** after the tuple-unpacking fix.
- Timeline events from `TimelineRepository.list_events` — **indexed as `(rows, total)[0]`** after the tuple-unpacking fix.
- Quality, analytics, and performance summaries from their repositories.
- `HealthResponse` via `_build_health` (aggregates live health data).
- Existing stored summaries from the `ReportStore` (so generators can reference prior documents).

## What Was Reviewed and Fixed

1. **Tuple unpacking bug (critical).** `_build_context` did:
   ```python
   for row, _ in await self._rings.list_rings(...)
   ```
   but `list_rings` returns `(rows, total)`. The loop unpacked `(rows, total)` into `row, _`, i.e. `row = rows` (a list) and `_ = total`, then tried to build a `Ring` from a list — the resulting crash surfaced as the `500` on `POST /generate`. Fixed to iterate `(await self._rings.list_rings(...))[0]`.
2. **Timezone mismatch.** `CollectorStatusGenerator` compared naive `last_seen` values with `datetime.now()`. Normalization now happens with `datetime.now(timezone.utc)`.
3. **DI syntax.** The router used `Optional[FilterParams] = Depends()`, which FastAPI did not resolve correctly (422). Switched to `Annotated[FilterParams, Depends()]` — the same idiom used across `machines`, `rings`, `timeline`, etc.

## Registry Benefits

- Single lookup by type; no type-to-generator `if/elif` chains.
- Missing generators fail loudly (`len(registry.generators) == 10` invariant checked in smoke tests).
- New report types require one new `ReportType` member, one generator class, and one registry line — no changes to the service or router.

## Residual Notes

- Generators produce "chart" sections as structured data only; chart rasterization is a presentation-layer concern (the frontend renders them as placeholders — intentional, unchanged).
- A future phase could move generator classes into individual modules (`report_generators/generators/*.py`); today they live in a single `__init__.py`, which is acceptable at the current scale but is the main maintainability debt (see Technical Debt Report).
