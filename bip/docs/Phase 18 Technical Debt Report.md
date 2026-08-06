# Phase 18 Technical Debt Report

## 1. Slot-Level Data Missing (Highest Impact)

The Phase 17 backend aggregates slot payloads into ring/machine/summary rows but exposes **no per-battery endpoint** (no `serial_number`, `slot_key`, `state`, `firmware_version` per battery row). Consequences:

- Battery Explorer rows are ring aggregates: `serialNumber` = ring MAC, `product`/`machine`/`slot`/`firmware` columns empty; state filters only cover Active/Warning/Finalized derived states.
- Battery detail and machine detail panels cannot show per-slot occupancy, battery lists, or firmware distribution.
- Machine Explorer shows real health/firmware/last-seen but zero slot counts.

**Suggested resolution (future phase, requires backend work):** add a read-only `/v1/ring-slots` endpoint over `CROSS JOIN LATERAL jsonb_each(content::jsonb)` (the SQL already exists in `RingsRepository`) and re-map the explorer hooks to it. Until then, the missing dimensions are deliberately surfaced as empty columns/states rather than fabricated.

## 2. Product and Per-Record Quality Dimensions Absent

No product catalog or per-record quality data exists in the read-only sources:

- Product Analytics: products list is empty; the page shows fleet KPIs (real), a real firmware distribution derived from `/v1/machines`, and the existing empty state for the table/panels.
- Quality Analytics: records/trend/defect tables empty; KPIs real from `/v1/quality/summary`; machine comparisons derived from live machine health as a documented proxy.

**Suggested resolution:** persist outcome rows in the read path (e.g. a `bic.quality_snapshot` view) in a later phase, then map the hooks to a new summary/records endpoint.

## 3. Timeline Event Fields Incomplete

`bic.ring_events` exposes `event_type`, `machine_name`, `occurred_at`, `reason` — no battery serial, slot, or previous/current state. Timeline events therefore carry empty battery/slot fields, and battery-grouping groups everything under one empty key. The source itself is currently empty, so the page shows the empty state.

**Suggested resolution:** extend the collector ingestion to populate battery identifiers on `bic.ring_events`, then enrich the timeline DTO.

## 4. Reports Surface is Aggregate-Derived

Reports are the per-machine "Ring Snapshot" rows derived from `live_rings_raw`; schedule/history/preview data has no source. The Reports page shows real snapshot rows with empty schedule/history/preview sections, and the "Scheduled Reports" grid is empty.

**Suggested resolution:** introduce a report catalogue + schedule table in a future phase if report management is productized.

## 5. Presentational Copy Still References Mocks

Per the strict "screenshots identical / only data source changes" constraint, pages still render provenance strings such as the `Mock Data` badge, `Mock operational snapshot` helpers, and `Placeholder …` descriptions. These are emitted by the pages/components (untouched) and by hook-emitted fallback content.

**Suggested resolution:** a small future cleanup phase may reword page copy and hero subtitles once the identical-UI constraint is lifted.

## 6. Detail Hooks Are Derivation-Only

`useBatteryDetail`/`useMachineDetail` derive detail panels synchronously from the live list record instead of fetching `/v1/rings/{id}` / `/v1/machines/{id}`. The endpoints exist and are typed in `apiClient` (verified 200), but are not consumed. This avoids N+1 and flicker; it becomes moot once slot-level data exists (debt item 1).

## 7. Metrics Collection Capped at page_size

Dashboard queries pass `page_size: 100`; summary collections (metrics, analytics, quality, performance) are small (<10 rows), so this is safe today. `fetchAllPages` is applied to rings/timeline/reports only. If a collection ever exceeds 100 rows and is consumed without `fetchAllPages`, it would silently truncate.

## 8. Pre-Existing (Not Introduced in Phase 18)

- ECharts bundle > 500 kB chunk-size warning (no code-splitting).
- Out-of-scope features (settings, prediction, performance-analytics, ai-intelligence, administration) remain mock-backed — consolidated migration should follow the same hook pattern as Phase 18.
- The `D:\BDR\apps\api` Phase 16 tree remains as dead code alongside `bip/apps/api`; removal is recommended in a future cleanup phase.
