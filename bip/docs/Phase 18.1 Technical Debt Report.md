# Phase 18.1 Technical Debt Report

## 1. Per-Battery (Slot-Level) Data Still Absent (Highest Impact)

The Phase 17 backend aggregates slot payloads into ring/machine/summary rows but exposes no per-battery endpoint. Phase 18.1 detail hooks now fetch the freshest ring/machine snapshot (`/v1/rings/{id}`, `/v1/machines/{id}`), but the payloads remain ring/machine aggregates:

- Battery detail: identity/product/slot/firmware fields still empty; machine context is blank; charts are placeholder containers.
- Machine detail: `slotCount`/`slotsOccupied` are 0, battery list is empty, slot overview shows no occupancy.
- Battery Explorer rows and Timeline events still lack battery serials.

**Suggested resolution (future phase, backend work required):** add a read-only `/v1/ring-slots` endpoint over `CROSS JOIN LATERAL jsonb_each` (the SQL exists in `RingsRepository`), then map the explorer and detail hooks to it.

## 2. Product and Per-Record Quality Dimensions Absent

- Product Analytics: products list empty; KPIs and firmware distribution are real; table shows the empty state.
- Quality Analytics: records/trend/defect tables empty; machine comparisons are a documented live proxy (machine health as quality signal).

**Suggested resolution:** persist outcome rows in the read path (e.g. a `bic.quality_snapshot` view) in a later phase, then map the hooks to a records endpoint.

## 3. Timeline Event Fields Incomplete

`bic.ring_events` exposes `event_type`, `machine_name`, `occurred_at`, `reason` only — no battery serial, slot, or previous/current state. Timeline events carry empty battery/slot fields; battery grouping collapses under one empty key; the source is currently empty (0 rows).

**Suggested resolution:** extend collector ingestion to populate battery identifiers on `bic.ring_events`, then enrich the timeline DTO.

## 4. Reports Surface Is Aggregate-Derived

Reports are per-machine "Ring Snapshot" rows derived from `live_rings_raw`; schedule/history/preview data has no source. The Reports page shows real snapshot rows with empty schedule/history/preview sections; execution-history KPIs are static zeros.

**Suggested resolution:** introduce a report catalogue + schedule table in a future phase if report management is productized.

## 5. Static Placeholder Content Remains Inside Hooks

- Executive dashboard activity/alerts/operations descriptions are static (values live, narrative static).
- Battery Intelligence pending-removal rows are static placeholder entries (`BAT-1024` …) with neutralized wording; there is no API for removal-queue detail.
- Analytics Hub insights/alerts/quick-nav and most card sub-metrics are static copy with a few live numbers.
- Chart containers everywhere remain placeholders by design.

These are documented constraints of the Phase 17 read-only API, not regressions.

## 6. Detail Hooks Still Fall Back to the List Row

`useBatteryDetail`/`useMachineDetail` render the last-known state while the detail query is in flight and keep showing it (with a `Cached` banner) if the detail request fails. This is deliberate (no blank screens), but it means a failed detail fetch never shows a full error-only screen — acceptable trade-off, revisit if full-error UX is preferred.

## 7. Shared-Query Layer Is Per-Endpoint, Not Per-Feature

The new `lib/useApiQueries.ts` shares caches across features (metrics/machines/rings/…), but each feature still re-maps DTOs to its domain types independently (e.g. ring→BatteryRecord mapping exists in both `useBatteryExplorer` and the battery detail). A future mapper layer could deduplicate this, but the mapping cost is trivial and hooks remain the single mapping point per the architecture.

## 8. Design-System `Button` Component Is Incomplete

`components/design-system` `Button` accepts no `onClick`/`onSubmit` props, so it cannot be used for real actions. Phase 18.1 avoided it (native buttons with `ds-button`/`__button` classes). The component should be extended or deprecated in a future phase.

## 9. Pre-Existing (Not Introduced in Phase 18.1)

- ECharts bundle >500 kB chunk warning (no code-splitting).
- Out-of-scope features (settings, prediction, performance-analytics, ai-intelligence, administration) remain mock-backed; consolidation should follow the Phase 18/18.1 hook pattern.
- The `D:\BDR\apps\api` Phase 16 tree remains as dead code alongside `bip/apps/api`; removal recommended in a future cleanup phase.
- Vite dev server on port 3100 left running (pre-existing).
