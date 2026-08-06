# Phase 12 Acceptance Checklist

## Administration Center — Layout Requirements

- [x] Route `/admin` renders the Administration Center page (via `getRouteElement` in `router.tsx`; `/admin` added to the route registry as the only new entry).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Top KPI row (5 `MetricCard`s).
- [x] Filter toolbar (search + status/connection + date range + Clear All).
- [x] Summary row (machine count + active filter count).
- [x] Sections: System Health, Collector Status, Machine Registry, Audit Log, Platform Information.
- [x] Machine registry row click → detail drill-down.

## Mock Data

- [x] System Health: 6 infrastructure metrics with tone-coded status.
- [x] Collector Status: 8 collectors (6 Running, 1 Stalled, 1 Stopped) with version/events/errors.
- [x] Schema Version: 5 schemas including `core.schema v42` and one Failed migration.
- [x] Machine Registry: 8 machines (AQC-01 … AQC-08).
- [x] Database Status: `bip_core`, `bip_fleet`, `bip_quality` with latency/connections/backup.
- [x] Service Status: 5 services with uptime and last restart.
- [x] Audit Logs: 20 deterministic entries, newest first.
- [x] Platform Information: name, version, environment, deploy date, build, nodes, storage, region.

## Machine Registry Records

- [x] Each machine has Machine ID, Machine Name, Status, Last Seen, Collector Version, Health Score, Firmware, and Connection Status.
- [x] AQC-04 modeled as Warning/Degraded and AQC-08 as Critical/Offline (consistent with prior phases).
- [x] Machine detail shows all 8 fields in a metric grid.

## Dashboard

- [x] Healthy Machines (4 / 8, "4 online now").
- [x] Offline Machines (1, "-1 this week").
- [x] Collector Status (6 / 8 running, "1 stalled · 1 stopped").
- [x] Schema Version (42, "1 migration pending").
- [x] Platform Health (98%, "+0.4 pts").

## Sections

- [x] System Health: infrastructure metric cards (CPU/Memory/Storage/Queue/Errors/Uptime).
- [x] Collector Status: collector table with status badges.
- [x] Machine Registry: full table with status and connection badges + View action.
- [x] Audit Log: timestamp/actor/action/entity/entity id/detail.
- [x] Platform Information: platform grid (platform, version, environment, deployed, build, nodes, storage, region).

## Filter Toolbar

- [x] Search matches machine id, name, firmware, and collector version.
- [x] Status select (exact match; derived from data).
- [x] Connection select (exact match; derived from data).
- [x] Date range (from/to) on last-seen.
- [x] Clear All resets all filters.
- [x] Empty state shown when no machines match.

## Detail Drill-Down

- [x] Detail shows hero (machine id + name, status/connection/firmware badges).
- [x] Machine Details: 8-metric grid.
- [x] Health Timeline: 14 daily points with health score and status badges.
- [x] Status Summary: connection, health score, audit entry count, timeline point count.
- [x] Audit Entries: per-machine audit entries filtered by machine id.
- [x] 2 `ChartContainer` placeholders (Health Score Trend, Uptime Distribution).
- [x] Back button returns to the list view.

## Chart Policy

- [x] No business charts — every chart surface is a `ChartContainer` placeholder.
- [x] Detail view uses `ChartContainer` only.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `administration.css`.
- [x] Desktop: 5-col KPI row, 3-col metric grid, 4-col detail metric grid, 2-col pair grids, 4-col platform grid.
- [x] Tablet (≤1180px): 2-column collapse of KPI row, panels, and detail grids.
- [x] Mobile (≤720px): fully single-column, stacked headers.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Layout, Sidebar, Header, Design System, Charts, or any previously shipped feature (Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, Analytics Hub, Product Analytics, Quality Analytics, Performance Analytics, Reports, AI Intelligence Center).
- [x] Route mapping follows the standard `getRouteElement` pattern; the only registry change is the new `/admin` entry.
- [x] No secrets, no backend calls, no API dependencies introduced.
