# Phase 6 Acceptance Checklist

## Analytics Hub — Layout Requirements

- [x] Route `/analytics` renders the Analytics Hub page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Top KPI row (Executive KPI Summary).
- [x] Analytics category grid (Analytics Navigation Cards).
- [x] Recent Insights panel.
- [x] Top Alerts panel.
- [x] Quick Navigation section.
- [x] Placeholder chart area.

## Executive KPI Summary

- [x] Batteries Tracked (1,284, +42 this month).
- [x] Active Machines (8, all reporting).
- [x] Open Alerts (6, 3 critical).
- [x] Fleet Health Score (91, +2 pts).
- [x] KPI deltas shown as tone-coded helpers.

## Analytics Navigation Cards (7 categories)

- [x] Machine Analytics Summary — status Nominal, route `/machine-explorer`.
- [x] Product Analytics Summary — status On Track, route `/production`.
- [x] Quality Summary — status Watch, route `/quality`.
- [x] Reliability Summary — status Nominal, route `/reliability`.
- [x] Performance Summary — status Nominal, route `/performance`.
- [x] Trend Summary — status Rising, route `/trends`.
- [x] Comparison Summary — status Stable, route `/comparison`.

## Card Anatomy (every card includes)

- [x] Title.
- [x] Description.
- [x] Key Metrics (4 per card, tone-coded where applicable).
- [x] Mini Chart Placeholder (72px `ChartContainer`).
- [x] Primary Action (navigates to the category route).
- [x] Secondary Action ("View Charts" — smooth-scrolls to the placeholder chart area).
- [x] Status Badge.

## Panels & Sections

- [x] Recent Insights: 4 items with tag badge, title, detail, timestamp.
- [x] Top Alerts: 4 items with severity badge (danger/warning/info), title, detail, timestamp.
- [x] Quick Navigation: 5 cards (Executive, Battery Intelligence, Battery Explorer, Machine Explorer, Timeline) that navigate to live pages.
- [x] Placeholder Chart Area: Fleet Health Trend + Alert Volume by Category via `ChartContainer`.

## Chart Policy

- [x] No business charts — every chart surface is a `ChartContainer` placeholder.
- [x] Mini charts and full chart area both use `ChartContainer`.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `analyticsHub.css`.
- [x] Desktop: 4-col KPI row, auto-fill category grid, 2-col insights/alerts and charts.
- [x] Tablet (≤1180px): single-column KPI row, panels, and charts.
- [x] Mobile (≤720px): fully single-column, stacked headers.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Routing config (`routes.ts`), Charts, Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, or Timeline.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
