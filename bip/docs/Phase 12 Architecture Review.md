# Phase 12 Architecture Review

## Overview

Phase 12 adds the Administration Center as a self-contained feature under `apps/web/src/features/administration/`. It follows the established feature-folder pattern (types, mock provider, hook, presentational components, token-based CSS) and introduces no changes to the platform foundation.

## Layering

```
AdministrationPage (composition / route target)
 ├── useAdministration                 (mock data + filter state + drill-down state)
 ├── components/AdministrationToolbar  (search + status/connection/date filters)
 ├── (inline) KPI row × 5 MetricCard   (Healthy Machines, Offline Machines, Collector Status, Schema Version, Platform Health)
 ├── components/SystemHealthPanel      (infrastructure metric cards)
 ├── components/ServiceStatusPanel     (service table)
 ├── components/DatabaseStatusPanel    (database table)
 ├── components/CollectorStatusPanel   (collector table)
 ├── components/SchemaVersionPanel     (schema registry table)
 ├── components/MachineRegistryPanel   (registry header + AdministrationTable)
 ├──   └── AdministrationTable         (machine table, row click → detail)
 ├── components/AuditLogPanel          (audit table, reused in detail)
 ├── (inline) Platform Information section
 └── components/AdministrationDetailPanel (drill-down view, replaces page body)
     ├── HealthMetricsPanel            (14-day health timeline)
     └── AuditLogPanel                 (per-machine audit entries, reused)
administration.types.ts   (shared types)
administration.mock.ts    (deterministic mock source)
administration.css        (feature-scoped, token-based styles)
```

## Data Flow

1. `useAdministration` memoizes `getMockAdministration()` once. Machines flow into a memoized filter pipeline: `matchesFilters` checks search + exact status/connection matches and last-seen date bounds; `deriveOptions` builds select options from the machine set.
2. Aggregates (kpis, healthMetrics, collectors, schemas, services, databases, auditEntries, platform) are derived once in the mock and flow as props to presentational components.
3. Drill-down is local UI state: `openDetail(machine)` sets `selected`; the page renders `AdministrationDetailPanel`. Per-machine `machineTimeline` (14 points via `getHealthTimeline`) and `machineAuditEntries` (audit filtered by `entityId === machineId`) are memoized on selection.

## Component Principles

- **Container/presentational split**: only `AdministrationPage` and `useAdministration` hold state/composition; every child is props-driven and re-usable.
- **Single responsibility**: 12 components, each rendering one region. `AdministrationTable`, `AuditLogPanel`, and tone helpers are reused across list and detail views.
- **Stable keys**: KPIs, machines, collectors, schemas, services, databases, audit entries, and timeline points all keyed by id.
- **Tone system**: machine status, connection, collector, schema, service, and database statuses map onto the design-system Badge/MetricCard tone contracts via shared helper functions in the mock.

## State Management

- `useState` only: the filter object and the selected machine for drill-down. No global store, context, or URL sync. Filtering is computed on every render via memoized `filteredMachines`.

## Styling

- `administration.css` uses only design tokens; dark theme inherited automatically via token swaps.
- Class prefix `administration__` / `administration-detail__` prevents collisions with other features.
- Breakpoints: ≤1180px collapses the KPI row, metric grids, pair grids, detail grids, and platform grid to 2 columns; ≤720px goes fully single-column with stacked headers.

## Routing

- Wired through the existing `getRouteElement` switch in `router.tsx` — the same pattern used for Phases 1–11.
- `/admin` was not present in `routes.ts`, so a single additive entry `{ path: "/admin", label: "Administration Center" }` was inserted (same precedent as `/ai` in Phase 11). The pre-existing `/administration` entry and all other route entries were left untouched.

## Mock Strategy

- The mock module is the single contact point for fake data. Machine records are shared with the platform's machine identity (AQC-01 … AQC-08) so the registry, collectors, audit log, and timelines stay internally consistent (e.g., AQC-04 stalled/degraded, AQC-08 offline/critical). Timeline points and statuses are derived deterministically from each machine's health score. Replacing with an API later only requires changing `getMockAdministration`, leaving components intact.

## Dependencies Added

- None. Phase 12 consumes only existing design-system primitives (`Badge`, `Card`, `MetricCard`, `EmptyState`, `ChartContainer`) and `react` hooks.
