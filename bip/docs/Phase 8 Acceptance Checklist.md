# Phase 8 Acceptance Checklist

## Quality Analytics — Layout Requirements

- [x] Route `/quality` renders the Quality Analytics page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Filter toolbar (search + filters + Clear All).
- [x] Summary row (record count + active filter count).
- [x] Top KPI row (5 `MetricCard`s).
- [x] Defect Distribution panel + Failure Categories panel.
- [x] Quality Trend section (chart placeholders + recent points).
- [x] Product Quality Comparison + Machine Quality Comparison.
- [x] Quality table with row click → detail drill-down.

## Filter Toolbar

- [x] Search input matches product, category, machine, and firmware.
- [x] Product select (exact match).
- [x] Machine select (exact match).
- [x] Firmware select (exact match).
- [x] Pass/Fail select (Pass / Fail record result).
- [x] Date range (from/to) on the record date.
- [x] Clear All resets all filters.
- [x] Summary row shows record count and active-filter count.
- [x] Empty state shown when no records match.

## KPI Summary

- [x] Pass Rate (94.5%, +0.4 pts).
- [x] Fail Rate (5.5%, −0.2 pts).
- [x] Yield (96.9%, +0.3 pts).
- [x] Retest Rate (3.4%, −1.1 pts).
- [x] Quality Score (95/100, +2 pts).

## Defect & Failure Data

- [x] Defect Distribution: 6 categories with tone-coded bars, count, and share % (total 3,150 defects).
- [x] Failure Categories: 6 rows with severity badge (Critical/High/Medium/Low), description, count, share.
- [x] Category severities map to tones (Critical→danger, High→warning, Medium→info, Low→neutral).

## Quality Trends

- [x] 3 `ChartContainer` placeholders: Pass Rate Trend, Yield Trend, Defect Volume by Category.
- [x] Recent Points table (last 7 days) with date, pass rate, yield, failed.
- [x] 14 daily trend points computed from record aggregates.

## Comparisons

- [x] Product Quality Comparison: 5 cards (LFP-280, LFP-135, NMC-121, NMC-280, LTO-45), each vs fleet average.
- [x] Machine Quality Comparison: 8 cards (AQC-01 … AQC-08), each vs fleet average.
- [x] Metrics per card: Pass Rate, Yield, Retest Rate, Quality Score, tone-coded vs fleet.
- [x] Kind badge distinguishes Product vs Machine.

## Quality Table

- [x] Columns: product, machine, firmware, date, produced, passed, failed, retested, pass rate, yield, retest rate, result badge, view action.
- [x] Row click and View button both open the detail panel.
- [x] 560 records (5 products × 8 machines × 14 days).

## Detail Drill-Down

- [x] Detail shows hero (product · machine, category/firmware/date), result badge.
- [x] 9-metric grid: Produced, Passed, Failed, Retested, Pass Rate, Fail Rate, Yield, Retest Rate, Quality Score.
- [x] Per-record defect distribution.
- [x] Status badge (Compliant / Action Required).
- [x] `ChartContainer` placeholder.
- [x] Back button returns to the list view.

## Chart Policy

- [x] No business charts — every chart surface is a `ChartContainer` placeholder.
- [x] List and detail views both use `ChartContainer` only.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `qualityAnalytics.css`.
- [x] Desktop: 5-col KPI/metric rows, 2-col defect/failure, comparison, and 3-col chart grids.
- [x] Tablet (≤1180px): 2-column collapse of KPI row, panels, charts, and comparisons.
- [x] Mobile (≤720px): fully single-column, stacked headers.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Routing config (`routes.ts`), Charts, Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, Analytics Hub, or Product Analytics.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
