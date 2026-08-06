# Phase 5 Acceptance Checklist

## Timeline — Functional Requirements

- [x] Route `/timeline` renders the Timeline page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Chronological event list rendered as grouped sections.
- [x] Date Grouping (group by event date, formatted label, chronological order).
- [x] Machine Grouping (group by machine ID).
- [x] Battery Grouping (group by battery serial number).
- [x] Group By segmented control switches between Date / Machine / Battery.
- [x] Event Cards show type badge, time, battery · machine · slot, reason, and state transition.
- [x] Search matches event type, battery serial, machine, slot, and reason (case-insensitive, partial).
- [x] Filter by Machine (select).
- [x] Filter by Battery (select).
- [x] Filter by Event Type (select).
- [x] Date Range filter (from / to) against event date.
- [x] Sort by timestamp asc/desc ("Oldest first" / "Newest first") — applies to groups and events within groups.
- [x] Pagination at 5 groups/page with Previous/Next and numbered buttons.
- [x] "Showing groups X–Y of Z" summary updates with the current page and total.
- [x] Summary row shows "N events in M groups" plus active-filter count.
- [x] Empty result set renders the design-system `EmptyState`.

## Timeline Event Types (all 10 present)

- [x] Observed
- [x] Tracking
- [x] Pending Removal
- [x] Finalized
- [x] Passed
- [x] Failed
- [x] Replacement
- [x] Machine Offline
- [x] Machine Online
- [x] Firmware Changed

## Timeline Detail — Functional Requirements

- [x] Back button returns to the timeline.
- [x] Event Information: event type, battery, machine, slot, timestamp, reason.
- [x] State Change panel: Previous State → Current State (with placeholder badge where no transition exists).
- [x] Metadata list (Ring, Collector, Severity, Source).
- [x] Charts Placeholder: Event Volume and Event Type Split via `ChartContainer`.

## Mock Data Requirements

- [x] Deterministic — same events on every render/reload.
- [x] 57 events; all 10 event types covered.
- [x] Dates spread across July/Aug 2026; realistic timestamps.
- [x] Realistic battery serial family consistent with the platform.
- [x] Mock-data and placeholder badges clearly mark non-real content.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `timeline.css`.
- [x] Desktop: 3-column filter grids, 2-column chart grid, time column on event cards.
- [x] Tablet (≤1180px): single-column filters and charts; 2-column metrics.
- [x] Mobile (≤720px): fully single-column, stacked heroes/headers, arrow rotates for vertical state change.
- [x] Event cards are keyboard accessible (Enter/Space).

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Executive Dashboard, Battery Dashboard, Battery Explorer, Machine Explorer, Charts, or Routing config (`routes.ts`).
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
