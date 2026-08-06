# Phase 9 Acceptance Checklist

## Performance Analytics — Layout Requirements

- [x] Route `/performance` renders the Performance Analytics page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Filter toolbar (search + filters + Clear All).
- [x] Summary row (record count + active filter count).
- [x] Top KPI row (6 `MetricCard`s).
- [x] Cycle Distribution + Utilization Distribution panels.
- [x] Performance Trend section (chart placeholders + recent points).
- [x] Machine Comparison + Product Performance comparison grids.
- [x] Performance table with row click → detail drill-down.

## Filter Toolbar

- [x] Search input matches machine, product, category, and firmware.
- [x] Machine select (exact match).
- [x] Product select (exact match).
- [x] Firmware select (exact match).
- [x] Date range (from/to) on the record date.
- [x] Clear All resets all filters.
- [x] Summary row shows record count and active-filter count.
- [x] Empty state shown when no records match.

## KPI Summary

- [x] Throughput (146.3/hr, +6/hr).
- [x] Cycle Time (13.6s, −0.3s).
- [x] Machine Utilization (84.4%, +1.2 pts).
- [x] Battery Processing Rate (2.4/min, +0.1/min).
- [x] Machine Efficiency (92%, +0.8 pts).
- [x] Performance Score (90/100, +3 pts).

## Distributions

- [x] Cycle Distribution: 3 buckets (10-12s ×17, 12-14s ×331, 14-16s ×212), tone-coded bars with count + share %.
- [x] Utilization Distribution: 3 buckets (70-80% ×70, 80-90% ×435, ≥90% ×55), tone-coded bars with count + share %.
- [x] Lower cycle time and higher utilization buckets are tone-coded as more favorable.

## Performance Trends

- [x] 3 `ChartContainer` placeholders: Throughput Trend, Utilization Trend, Cycle Time Trend.
- [x] Recent Points table (last 7 days) with date, throughput, utilization, cycle time, efficiency.
- [x] 14 daily trend points computed from record averages.

## Comparisons

- [x] Machine Comparison: 8 cards (AQC-01 … AQC-08), each vs fleet average.
- [x] Product Performance: 5 cards (LFP-280, LFP-135, NMC-121, NMC-280, LTO-45), each vs fleet average.
- [x] Metrics per card: Throughput, Cycle Time, Utilization, Efficiency, Performance Score, tone-coded vs fleet.
- [x] Kind badge distinguishes Machine vs Product.

## Performance Table

- [x] Columns: machine, product, firmware, date, produced, throughput, cycle time, utilization, processing rate, efficiency, performance score, status badge, view action.
- [x] Row click and View button both open the detail panel.
- [x] 560 records (8 machines × 5 products × 14 days).

## Detail Drill-Down

- [x] Detail shows hero (machine · product, category/firmware/date), status badge.
- [x] 8-metric grid: Throughput, Cycle Time, Utilization, Processing Rate, Efficiency, Performance Score, Produced, Target Throughput.
- [x] Throughput vs Target bar with % of target badge.
- [x] `ChartContainer` placeholder.
- [x] Back button returns to the list view.

## Chart Policy

- [x] No business charts — every chart surface is a `ChartContainer` placeholder.
- [x] List and detail views both use `ChartContainer` only.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `performanceAnalytics.css`.
- [x] Desktop: 6-col KPI row, 4-col detail metric grid, 2-col distribution/comparison grids, 3-col chart grid.
- [x] Tablet (≤1180px): 2-column collapse of KPI row, panels, charts, and comparisons.
- [x] Mobile (≤720px): fully single-column, stacked headers.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Routing config (`routes.ts`), Charts, Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, Analytics Hub, Product Analytics, or Quality Analytics.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
