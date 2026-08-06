# Phase 4 Acceptance Checklist

## Machine Explorer — Functional Requirements

- [x] Route `/machine-explorer` renders the Machine Explorer page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Machine Search: text query matches machine ID or machine name (case-insensitive, partial).
- [x] Machine Status filter (All / Online / Offline).
- [x] Sort by machine ID, health score, active batteries, and last seen.
- [x] Ascending/descending direction toggle.
- [x] Clear All resets search and status filter.
- [x] Result count and active-filter count shown in the summary row.
- [x] Machine Cards render in a responsive grid.
- [x] Online/Offline Indicator on every card (status pill with dot).
- [x] Health Score displayed on each card with tone-coded progress bar.
- [x] Active Batteries count on each card.
- [x] Pending Removal Count on each card.
- [x] Finalized Count on each card.
- [x] Slot Occupancy Summary on each card (occupied/total + progress bar).
- [x] Dominant Firmware and Last Seen in each card footer.
- [x] Card click (and Enter/Space on focused card) opens Machine Detail.
- [x] Empty result set renders the design-system `EmptyState`.

## Machine Detail — Functional Requirements

- [x] Back button returns to the machine grid.
- [x] Machine Information: machine ID, name, status, slot capacity, dominant firmware, last seen.
- [x] Current Statistics: active batteries, pending removal, finalized, health score, slots occupied, batteries present.
- [x] Slot Overview (placeholder badge): 12-slot grid; occupied slots show serial number + state badge.
- [x] Battery List: serial number, slot, current state (badge), firmware, last seen.
- [x] Recent Events (placeholder): timestamp, event, context.
- [x] Timeline Placeholder: Commissioned → Operational → Maintenance → Under Review → Retired with reached/current markers.
- [x] Charts Placeholder: Slot Occupancy and Battery Health Trend rendered via `ChartContainer`.
- [x] Health Panel: large health score, health factors (score, distribution, firmware coverage, data freshness), Firmware Summary, and Product Distribution.

## Mock Data Requirements

- [x] Deterministic — same machines and values on every render/reload.
- [x] 8 machines across AQC-01…08 with realistic names.
- [x] Mixed online/offline statuses (2 offline).
- [x] Realistic spread of health scores (60–99), active/pending/finalized counts.
- [x] Per-machine firmware summary and product distribution sum to the machine's battery count.
- [x] Battery serial family consistent with the platform (`RP-CH3-P18-WD-*`).
- [x] Mock-data and placeholder badges clearly mark non-real content.

## Design / Responsive

- [x] Tokens only — no hardcoded colors in `machineExplorer.css`.
- [x] Cards: `repeat(auto-fill, minmax(300px, 1fr))` — auto-wraps on any viewport width.
- [x] Toolbar: 3-column; collapses to 1 column at ≤1180px.
- [x] Detail: two-column grids collapse to single column at ≤1180px.
- [x] Mobile (≤720px): single-column everything, stacked hero/headers/rows.
- [x] Battery List table scrolls horizontally on narrow viewports (`min-width: 720px`).

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Executive Dashboard, Battery Intelligence Dashboard, or Battery Explorer.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
