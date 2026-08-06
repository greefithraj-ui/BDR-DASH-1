# Phase 14 Acceptance Checklist

## Prediction Center — Layout Requirements

- [x] Route `/prediction` renders the Prediction Center page (via `getRouteElement` in `router.tsx`; `/prediction` added to the route registry).
- [x] Page title, eyebrow label, and mock-data badges displayed.
- [x] Top KPI row (5 `MetricCard`s): Models, Ready Models, Training Models, Coverage, Average Accuracy.
- [x] Toolbar (search + status + owner + Clear All).
- [x] Model Cards: each shows name, description, status badge, and View Details action.
- [x] Detail View: Back button, model name + status badge, summary grid, ChartContainer placeholders.
- [x] No modification to any previously shipped feature (Foundation, Theme, Providers, Layout, Sidebar, Header, Router, Design System, Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Timeline, Analytics Hub, Product Analytics, Quality Analytics, Performance Analytics, Reports, AI Intelligence Center, Administration Center, Settings Center).

## Mock Data

- [x] 6 models across Planned/Prototype/Training/Ready statuses.
- [x] Predict Maintenance (Ready, 94% accuracy, 85% coverage)
- [x] Remaining Useful Life (Ready, 89% accuracy, 78% coverage)
- [x] Failure Probability (Training, 0% accuracy, 92% coverage)
- [x] Machine Health Forecast (Prototype, 75% accuracy, 60% coverage)
- [x] Product Reliability (Planned, 0% accuracy)
- [x] Capacity Degradation (Ready, 91% accuracy, 88% coverage)
- [x] KPIs: 6 total models, 3 ready, 1 training, 74% coverage, 88% average accuracy.

## Models

- [x] Each model has all required fields: id, name, description, status, version, accuracy, last trained, next training, coverage, dataset size, health score, owner.

## Filters

- [x] Search matches name and description.
- [x] Status select (All + Planned, Prototype, Training, Ready).
- [x] Owner select (All + Fleet Team, Data Science, Reliability, R&D, Quality, Operations).
- [x] Clear All resets all filters.
- [x] Results shown only for matching models; empty state when no matches.

## Detail View

- [x] Model Information: description, version, owner, accuracy.
- [x] Metrics ChartContainer placeholder.
- [x] Training Timeline ChartContainer placeholder.
- [x] Datasets ChartContainer placeholder.
- [x] Configuration ChartContainer placeholder.
- [x] History ChartContainer placeholder.
- [x] Back button returns to list view (local state).

## Charts

- [x] No business charts — every chart surface is a `ChartContainer` placeholder.
- [x] Detail view uses `ChartContainer` for Metrics, Training Timeline, Datasets, Configuration, and History.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `prediction.css`.
- [x] Desktop: 5-col KPI row, 3-col model list.
- [x] Tablet (≤1180px): 2-col KPI row, 2-col model list.
- [x] Mobile (≤720px): 1-col KPI row, 1-col model list.

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to protected areas.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
