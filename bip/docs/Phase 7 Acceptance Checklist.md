# Phase 7 Acceptance Checklist

## Product Analytics — Layout Requirements

- [x] Route `/production` renders the Product Analytics page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Filter toolbar (search + filters + Clear All).
- [x] Summary row (filtered product count + active filter count).
- [x] Top KPI row (4 `MetricCard`s).
- [x] Distribution panels (Firmware, Product Share, Failure, Lifecycle).
- [x] Product Health Summary + Product Comparison Cards.
- [x] Product table with row click → detail drill-down.
- [x] Placeholder chart area.

## Filter Toolbar

- [x] Search input matches product, category, and description.
- [x] Product select (exact match).
- [x] Firmware select (matches products using that firmware).
- [x] Machine select (matches products deployed on that machine).
- [x] Lifecycle State select (matches products with that stage).
- [x] Date range (from/to) on the product's last-updated date.
- [x] Clear All resets all filters.
- [x] Summary row shows filtered count and active-filter count.
- [x] Empty state shown when no products match.

## KPI Summary

- [x] Products (5, across 3 categories).
- [x] Total Batteries (1,700, +118 this month).
- [x] Avg Pass Rate (94%, +0.3 pts).
- [x] Fleet Health (79/100, +1 pt).

## Catalog Content

- [x] 5 products: LFP-280, LFP-135, NMC-121, NMC-280, LTO-45.
- [x] Product distribution with share % (sums to ~100%).
- [x] 5 failure causes with tone-coded distribution.
- [x] 5 lifecycle stages (Registered, Tracking, Review, Pending Removal, Finalized).
- [x] Fleet firmware summary (v3.0.2, v2.4.1, v2.3.8, v1.9.0).
- [x] 5 comparison cards "vs fleet average" with tone-coded metrics.
- [x] Product table: product, category, description, total/active/pending/finalized/failed, pass rate, health, status, machines, view action.

## Detail Drill-Down

- [x] Row click or View button opens the product detail panel.
- [x] Detail shows hero, status badge, 8-metric overview grid.
- [x] Firmware and lifecycle distribution per product.
- [x] Machines deployment list.
- [x] Fleet comparison card for the selected product.
- [x] Back button returns to the list view.

## Chart Policy

- [x] No business charts — every chart surface is a `ChartContainer` placeholder (Firmware Adoption Trend, Failure Trend by Cause).
- [x] List and detail views both use `ChartContainer` only.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `productAnalytics.css`.
- [x] Desktop: 4-col KPI/metric rows, 2-col panels, 2-col health/comparison grid, 2-col chart grid.
- [x] Tablet (≤1180px): single-column KPI row, panel grids, health/comparison grid, detail grids, and charts.
- [x] Mobile (≤720px): fully single-column, stacked headers, single-column metric grids.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Routing config (`routes.ts`), Charts, Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, or Analytics Hub.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
