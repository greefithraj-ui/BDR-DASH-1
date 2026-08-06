# Phase 3 Acceptance Checklist

## Battery Explorer — Functional Requirements

- [x] Route `/battery-explorer` renders the Battery Explorer page (via `getRouteElement` in `router.tsx`).
- [x] Page title, eyebrow label, and mock-data badge displayed.
- [x] Search by serial number (partial, case-insensitive).
- [x] Search by ring MAC (partial, case-insensitive).
- [x] Search by ring name (partial, case-insensitive).
- [x] Filter by product (select).
- [x] Filter by machine (select).
- [x] Filter by slot (select).
- [x] Filter by state (select).
- [x] Filter by firmware (select).
- [x] Date range filter (from / to) against `lastSeen`.
- [x] Active filter chips render for every non-empty filter; each removable via `×`.
- [x] "Clear all" clears every filter at once.
- [x] Result count reflects the filtered set ("X batteries found").
- [x] Active-filter count shown in the summary row.
- [x] Sortable columns: Serial Number, Ring Name, Product, Machine, Current State, Firmware, First Seen, Last Seen.
- [x] Sort toggle asc/desc with indicator; first click on a new column sorts asc.
- [x] Non-sortable columns render as plain headers.
- [x] Pagination at 10 rows/page; Previous/Next disabled at bounds; page numbers re-render on filter change.
- [x] "Showing 1–10 of 58" summary updates with the current page and total.
- [x] Table shows all 12 required columns: Serial Number, Ring MAC, Ring Name, Product, Machine, Slot, Current State, Firmware, First Seen, Last Seen, Lifecycle Status, Actions.
- [x] Row click opens Battery Detail.
- [x] "View" action button opens Battery Detail without triggering row click twice.
- [x] Empty result set renders the design-system `EmptyState`.

## Battery Detail — Functional Requirements

- [x] Back button returns to the results table.
- [x] Identity Card: serial number, product, firmware, ring name, ring MAC, lifecycle status.
- [x] Current Machine & Slot: machine, slot, state, first seen, last seen, ring.
- [x] Lifecycle Timeline: Registered → Tracking → Review → Finalized, with reached/current markers and a Placeholder badge.
- [x] Decision Summary panel labeled "Placeholder" with mock recommendation/confidence/note.
- [x] Recent Events list (mock timestamps, event, context).
- [x] Placeholder charts: Signal Timeline and State History rendered via `ChartContainer`.
- [x] Current State rendered as a tone-coded `Badge`.

## Mock Data Requirements

- [x] 58 records → 6 pagination pages at 10/page.
- [x] Serial format family `RP-CH3-P18-WD-PG##-#######` / `RP-CH3-P18-WD-PR##-#######`.
- [x] Deterministic (same values on every render/reload).
- [x] Realistic spread across machines, products, states, firmwares, and ring names.
- [x] Mock-data badges/placeholders clearly mark non-real content.

## Design / Responsive

- [x] Toolbar uses tokens only (`--color/surface/text/border/radius/space-*`) — no hardcoded colors.
- [x] Desktop: 5-column filter grid; detail two-column grid.
- [x] Tablet (≤1180px): 2-column filter grid; detail single column.
- [x] Mobile (≤720px): single-column layouts, stacked hero, column-based pagination.
- [x] Table horizontally scrolls on narrow viewports (`min-width: 1120px`).

## Quality Gates

- [x] `npm run lint:web` (`tsc --noEmit`) — passed.
- [x] `npm run build:web` — passed.
- [x] No modification to Foundation, Theme, Providers, Tokens, Layout, Sidebar, Header, Executive Dashboard, or Battery Intelligence Dashboard.
- [x] Route mapping follows the standard `getRouteElement` pattern.
- [x] No secrets, no backend calls, no API dependencies introduced.
