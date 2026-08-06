# Phase 10 Acceptance Checklist

## Reports — Layout Requirements

- [x] Route `/reports` renders the Reports page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Filter toolbar (search + category/status/owner/frequency + date range + Clear All).
- [x] Dashboard KPI row (5 `MetricCard`s).
- [x] Recent Reports section (3 most recent first).
- [x] Scheduled Reports section.
- [x] Execution History section (45 runs, newest first).
- [x] Report Library table.
- [x] Report Preview section with per-report preview tables.
- [x] Card click and table row click → detail drill-down.

## Filter Toolbar

- [x] Search input matches title, description, category, and owner.
- [x] Category select (exact match; 8 categories).
- [x] Status select (exact match; derived from data).
- [x] Owner select (exact match; derived from data).
- [x] Frequency select (exact match; 5 frequencies).
- [x] Date range (from/to) on the last-run date.
- [x] Clear All resets all filters.
- [x] Summary row shows report count and active-filter count.
- [x] Empty state shown when no reports match.

## KPI Summary

- [x] Total Reports (9, "Across 8 categories").
- [x] Scheduled Reports (6, "2 this week").
- [x] Successful Runs (36, "+8 this month").
- [x] Failed Runs (9, "-2 this month").
- [x] Average Duration (derived from run history, ≈5m 44s).

## Report Cards

- [x] 9 deterministic reports with id, title, description, category, owner, created date, last run, next scheduled run, status/tone, frequency, estimated duration, pages.
- [x] Card shows category/status badges, frequency, description, owner, next run, duration, pages, and a View button.
- [x] Dates live in the future: created 2026-02/06, runs 2026-07/08, next runs 2026-08-03+.
- [x] Status→tone mapping: Scheduled=info, Ready=success, Draft=neutral, Failed=danger, Paused=warning.

## Sections

- [x] Recent Reports: top 3 by last-run date (Daily Production, Shift Performance, Quality Summary).
- [x] Scheduled Reports: the 6 Scheduled-status reports (Daily Production, Weekly Executive, Machine Performance, Battery Lifecycle, Monthly Intelligence, Shift Performance).
- [x] Execution History: 45 entries, newest first, tone-coded status badges.
- [x] Report Library: full table with status badges and View action.
- [x] Report Preview: renders each report's preview tables.

## Detail Drill-Down

- [x] Detail shows hero (back button, title, description, category/status/frequency badges).
- [x] Metadata grid: Owner, Created, Last Run, Next Run, Pages, Duration.
- [x] Report Schedule panel (frequency, run time, days, next run, duration, recipient chips).
- [x] Execution History panel for the selected report (5 runs).
- [x] Report Preview with the report's preview tables.
- [x] 2 `ChartContainer` placeholders (Report Content Trend, Report Volume by Category).
- [x] Back button returns to the list view.

## Chart Policy

- [x] No business charts — every chart surface is a `ChartContainer` placeholder.
- [x] List and detail views both use `ChartContainer` only.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `reports.css`.
- [x] Desktop: 5-col KPI row, 3-col card grid, 2-col detail/schedule/history/chart grids.
- [x] Tablet (≤1180px): 2-column collapse of toolbar, KPI row, cards, and detail grids.
- [x] Mobile (≤720px): fully single-column, stacked headers.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Routing config (`routes.ts`), Charts, Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, Analytics Hub, Product Analytics, Quality Analytics, or Performance Analytics.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
