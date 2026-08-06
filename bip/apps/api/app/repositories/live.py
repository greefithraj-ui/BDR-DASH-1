"""Shared read-only SQL against the approved live tables (public.live_*).

Only ``public.live_rings_raw`` and ``public.live_bdr_raw`` are read here. No
legacy tables (machine_logs, archive_entries, ring_status) and no writes.
"""

from datetime import datetime
from typing import Any

from app.repositories.base import (
    OCCUPIED_SERIAL_CONDITION,
    BaseSQLRepository,
)

FRESHNESS_SQL = "EXTRACT(EPOCH FROM (NOW() - downloaded_at::timestamptz))"

_MACHINE_SORT_FRAGMENTS = {
    ("machine_name", "asc"): "ORDER BY machine_name ASC",
    ("machine_name", "desc"): "ORDER BY machine_name DESC",
    ("last_seen_at", "asc"): "ORDER BY last_seen_at ASC NULLS LAST",
    ("last_seen_at", "desc"): "ORDER BY last_seen_at DESC NULLS LAST",
}


class LiveRepository(BaseSQLRepository):
    """Raw SQL access to the live tables shared by the domain repositories."""

    def _machine_sort(self, sort_by: str | None, sort_dir: str) -> str:
        return _MACHINE_SORT_FRAGMENTS.get(
            (sort_by or "machine_name", sort_dir if sort_dir == "desc" else "asc"),
            _MACHINE_SORT_FRAGMENTS[("machine_name", "asc")],
        )

    async def list_machines(
        self,
        *,
        freshness_window: int,
        search: str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = f"""
WITH sources AS (
    SELECT machine_name, downloaded_at, 'rings' AS src FROM public.live_rings_raw
    UNION ALL
    SELECT machine_name, downloaded_at, 'bdr' AS src FROM public.live_bdr_raw
),
agg AS (
    SELECT machine_name,
           MAX(downloaded_at::timestamptz) AS last_seen_at,
           MAX(downloaded_at::timestamptz) FILTER (WHERE src = 'rings') AS rings_at,
           MAX(downloaded_at::timestamptz) FILTER (WHERE src = 'bdr') AS bdr_at,
           COALESCE(MAX(CASE WHEN src = 'rings' AND ({FRESHNESS_SQL}) <= $1 THEN 1 ELSE 0 END), 0) AS rings_fresh,
           COALESCE(MAX(CASE WHEN src = 'bdr' AND ({FRESHNESS_SQL}) <= $1 THEN 1 ELSE 0 END), 0) AS bdr_fresh
    FROM sources
    GROUP BY machine_name
)
SELECT machine_name, last_seen_at, rings_at, bdr_at, rings_fresh, bdr_fresh,
       (rings_fresh = 1 OR bdr_fresh = 1) AS is_online,
       COUNT(*) OVER () AS total
FROM agg
WHERE ($2::text IS NULL OR machine_name ILIKE '%' || $2 || '%')
  AND ($3::text IS NULL OR (($3 = 'Online') = (rings_fresh = 1 OR bdr_fresh = 1)))
  AND ($4::timestamptz IS NULL OR last_seen_at >= $4)
  AND ($5::timestamptz IS NULL OR last_seen_at <= $5)
{self._machine_sort(sort_by, sort_dir)}
LIMIT $6 OFFSET $7
"""
        rows = await self.fetch_all(
            query,
            freshness_window,
            search,
            status,
            date_from,
            date_to,
            limit,
            offset,
        )
        total = rows[0]["total"] if rows else 0
        return rows, int(total)

    async def get_machine(
        self, machine_name: str, *, freshness_window: int
    ) -> dict[str, Any] | None:
        query = f"""
WITH sources AS (
    SELECT machine_name, downloaded_at, 'rings' AS src FROM public.live_rings_raw
    UNION ALL
    SELECT machine_name, downloaded_at, 'bdr' AS src FROM public.live_bdr_raw
),
agg AS (
    SELECT machine_name,
           MAX(downloaded_at::timestamptz) AS last_seen_at,
           MAX(downloaded_at::timestamptz) FILTER (WHERE src = 'rings') AS rings_at,
           MAX(downloaded_at::timestamptz) FILTER (WHERE src = 'bdr') AS bdr_at,
           COALESCE(MAX(CASE WHEN src = 'rings' AND ({FRESHNESS_SQL}) <= $1 THEN 1 ELSE 0 END), 0) AS rings_fresh,
           COALESCE(MAX(CASE WHEN src = 'bdr' AND ({FRESHNESS_SQL}) <= $1 THEN 1 ELSE 0 END), 0) AS bdr_fresh
    FROM sources
    GROUP BY machine_name
)
SELECT machine_name, last_seen_at, rings_at, bdr_at, rings_fresh, bdr_fresh,
       (rings_fresh = 1 OR bdr_fresh = 1) AS is_online
FROM agg
WHERE LOWER(machine_name) = LOWER($2)
"""
        return await self.fetch_one(query, freshness_window, machine_name)

    async def fleet_stats(self) -> list[dict[str, Any]]:
        query = f"""
SELECT machine_name,
       COUNT(*) AS slot_count,
       MODE() WITHIN GROUP (ORDER BY s.payload->>'firmware_version') AS dominant_firmware,
       COUNT(*) FILTER (WHERE s.payload->>'state' = 'BDR_RUNNING') AS running_count,
       COUNT(*) FILTER (WHERE s.payload->>'state' = 'ASSIGNED') AS assigned_count,
       COUNT(*) FILTER (WHERE s.payload->>'state' = 'FAILED') AS failed_count,
       COUNT(*) FILTER (WHERE s.payload->>'state' = 'PASSED') AS passed_count
FROM public.live_rings_raw r
CROSS JOIN LATERAL jsonb_each(r.content::jsonb) AS s(slot_key, payload)
WHERE {OCCUPIED_SERIAL_CONDITION}
GROUP BY machine_name
"""
        return await self.fetch_all(query)

    async def aggregates(self, freshness_window: int) -> dict[str, Any]:
        query = f"""
SELECT
  (SELECT COUNT(*) FROM public.live_rings_raw r
     CROSS JOIN LATERAL jsonb_each(r.content::jsonb) AS s(slot_key, payload)
    WHERE {OCCUPIED_SERIAL_CONDITION}) AS active_rings,
  (SELECT COUNT(*) FILTER (WHERE s.payload->>'state' = 'BDR_RUNNING') FROM public.live_rings_raw r
     CROSS JOIN LATERAL jsonb_each(r.content::jsonb) AS s(slot_key, payload)
    WHERE {OCCUPIED_SERIAL_CONDITION}) AS running_slots,
  (SELECT COUNT(*) FILTER (WHERE s.payload->>'state' = 'ASSIGNED') FROM public.live_rings_raw r
     CROSS JOIN LATERAL jsonb_each(r.content::jsonb) AS s(slot_key, payload)
    WHERE {OCCUPIED_SERIAL_CONDITION}) AS assigned_slots,
  (SELECT COUNT(*) FILTER (WHERE s.payload->>'state' = 'FAILED') FROM public.live_rings_raw r
     CROSS JOIN LATERAL jsonb_each(r.content::jsonb) AS s(slot_key, payload)
    WHERE {OCCUPIED_SERIAL_CONDITION}) AS failed_slots,
  (SELECT COUNT(*) FILTER (WHERE s.payload->>'state' = 'PASSED') FROM public.live_rings_raw r
     CROSS JOIN LATERAL jsonb_each(r.content::jsonb) AS s(slot_key, payload)
    WHERE {OCCUPIED_SERIAL_CONDITION}) AS passed_slots,
  (SELECT COUNT(*) FROM public.live_bdr_raw r
     CROSS JOIN LATERAL jsonb_each((r.content::jsonb)->'slots') AS s(slot_key, payload)
    WHERE {OCCUPIED_SERIAL_CONDITION}) AS bdr_slots,
  (SELECT COUNT(DISTINCT machine_name) FROM (
        SELECT machine_name FROM public.live_rings_raw
        UNION ALL
        SELECT machine_name FROM public.live_bdr_raw
    ) u) AS machines_total,
  (SELECT COUNT(*) FROM (
        SELECT machine_name FROM (
            SELECT machine_name, downloaded_at FROM public.live_rings_raw
            UNION ALL
            SELECT machine_name, downloaded_at FROM public.live_bdr_raw
        ) u
        GROUP BY machine_name
        HAVING MAX({FRESHNESS_SQL}) <= $1
    ) f) AS machines_fresh,
  (SELECT COUNT(*) FROM bic.active_rings WHERE state = 'FINALIZED') AS finalized_rings,
  (SELECT COUNT(*) FROM bic.active_rings WHERE state = 'PENDING_REMOVAL') AS pending_removal,
  (SELECT COUNT(*) FROM bic.ring_events) AS ring_events,
  (SELECT COUNT(*) FROM bic.ring_history) AS ring_history,
  (SELECT COALESCE(MAX(version), 0) FROM bic.schema_version) AS schema_version
"""
        row = await self.fetch_one(query, freshness_window)
        return row or {}
