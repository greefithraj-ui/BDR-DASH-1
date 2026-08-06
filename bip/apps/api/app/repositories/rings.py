from datetime import datetime
from typing import Any

import asyncpg

from app.repositories.base import OCCUPIED_SERIAL_CONDITION, BaseSQLRepository

_RING_SORT_FRAGMENTS = {
    ("ring_id", "asc"): "ORDER BY ring_id ASC",
    ("ring_id", "desc"): "ORDER BY ring_id DESC",
    ("ring_name", "asc"): "ORDER BY ring_name ASC NULLS LAST",
    ("ring_name", "desc"): "ORDER BY ring_name DESC NULLS LAST",
    ("status", "asc"): "ORDER BY status ASC",
    ("status", "desc"): "ORDER BY status DESC",
    ("slot_count", "asc"): "ORDER BY slot_count ASC",
    ("slot_count", "desc"): "ORDER BY slot_count DESC",
    ("last_seen_at", "asc"): "ORDER BY last_seen_at ASC NULLS LAST",
    ("last_seen_at", "desc"): "ORDER BY last_seen_at DESC NULLS LAST",
}

_RING_SELECT_SQL = f"""
SELECT ring_id,
       ring_mac,
       ring_name,
       product,
       slot_count,
       running_count,
       failed_count,
       passed_count,
       assigned_count,
       installed_at,
       last_seen_at,
       CASE
           WHEN failed_count > 0 THEN 'Warning'
           WHEN running_count = 0 AND assigned_count = 0 AND passed_count > 0 THEN 'Finalized'
           ELSE 'Active'
       END AS status
FROM (
    SELECT COALESCE(NULLIF(s.payload->>'ring_mac', ''), s.payload->>'ring_name',
                    s.payload->>'serial_number') AS ring_id,
           s.payload->>'ring_mac' AS ring_mac,
           s.payload->>'ring_name' AS ring_name,
           s.payload->>'product' AS product,
           COUNT(*) AS slot_count,
           COUNT(*) FILTER (WHERE s.payload->>'state' = 'BDR_RUNNING') AS running_count,
           COUNT(*) FILTER (WHERE s.payload->>'state' = 'FAILED') AS failed_count,
           COUNT(*) FILTER (WHERE s.payload->>'state' = 'PASSED') AS passed_count,
           COUNT(*) FILTER (WHERE s.payload->>'state' = 'ASSIGNED') AS assigned_count,
           MIN(r.downloaded_at::timestamptz) AS installed_at,
           MAX(r.downloaded_at::timestamptz) AS last_seen_at
    FROM public.live_rings_raw r
    CROSS JOIN LATERAL jsonb_each(r.content::jsonb) AS s(slot_key, payload)
    WHERE {OCCUPIED_SERIAL_CONDITION}
    GROUP BY 1, 2, 3, 4
) ring_agg
"""


class RingsRepository(BaseSQLRepository):
    """SQL access for rings, derived from the live ring slot snapshots.

    Rings are identified by their ring MAC address (falling back to ring name
    or battery serial number when the MAC is absent). Capacity is not recorded
    anywhere in the read-only sources, so ``slot_count`` is surfaced as the
    occupied-slot approximation.
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)

    def _sort(self, sort_by: str | None, sort_dir: str) -> str:
        key = (sort_by or "ring_id", sort_dir if sort_dir == "desc" else "asc")
        return _RING_SORT_FRAGMENTS.get(key, _RING_SORT_FRAGMENTS[("ring_id", "asc")])

    async def list_rings(
        self,
        *,
        search: str | None,
        status: str | None,
        sort_by: str | None,
        sort_dir: str,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        query = f"""
SELECT ring_id, ring_mac, ring_name, product, slot_count, running_count, failed_count,
       passed_count, assigned_count, installed_at, last_seen_at, status,
       COUNT(*) OVER () AS total
FROM ({_RING_SELECT_SQL}) q
WHERE ($1::text IS NULL
       OR ring_name ILIKE '%' || $1 || '%'
       OR ring_id ILIKE '%' || $1 || '%')
  AND ($2::text IS NULL OR status = $2)
  AND ($3::timestamptz IS NULL OR last_seen_at >= $3)
  AND ($4::timestamptz IS NULL OR last_seen_at <= $4)
{self._sort(sort_by, sort_dir)}
LIMIT $5 OFFSET $6
"""
        rows = await self.fetch_all(query, search, status, date_from, date_to, limit, offset)
        total = rows[0]["total"] if rows else 0
        return rows, int(total)

    async def get_by_id(self, ring_id: str) -> dict[str, Any] | None:
        query = f"""
SELECT ring_id, ring_mac, ring_name, product, slot_count, running_count, failed_count,
       passed_count, assigned_count, installed_at, last_seen_at, status
FROM ({_RING_SELECT_SQL}) q
WHERE ring_id = $1
"""
        return await self.fetch_one(query, ring_id)
