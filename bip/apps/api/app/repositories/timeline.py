from datetime import datetime
from typing import Any

import asyncpg

from app.repositories.base import BaseSQLRepository

_TIMELINE_SORT_FRAGMENTS = {
    ("timestamp", "asc"): "ORDER BY occurred_at ASC NULLS LAST",
    ("timestamp", "desc"): "ORDER BY occurred_at DESC NULLS LAST",
    ("type", "asc"): "ORDER BY event_type ASC",
    ("type", "desc"): "ORDER BY event_type DESC",
    ("machine_id", "asc"): "ORDER BY machine_name ASC NULLS LAST",
    ("machine_id", "desc"): "ORDER BY machine_name DESC NULLS LAST",
}


class TimelineRepository(BaseSQLRepository):
    """SQL access for the event timeline, sourced from bic.ring_events."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)

    def _sort(self, sort_by: str | None, sort_dir: str) -> str:
        key = (sort_by or "timestamp", sort_dir if sort_dir == "desc" else "asc")
        if key not in _TIMELINE_SORT_FRAGMENTS:
            return _TIMELINE_SORT_FRAGMENTS[("timestamp", "desc")]
        return _TIMELINE_SORT_FRAGMENTS[key]

    async def list_events(
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
SELECT e.id::text AS id,
       e.occurred_at AS timestamp,
       e.event_type AS type,
       COALESCE(e.machine_name, '') AS machine_id,
       COALESCE(NULLIF(e.reason, ''), e.event_type) AS message,
       COUNT(*) OVER () AS total
FROM bic.ring_events e
WHERE ($1::text IS NULL
       OR e.event_type ILIKE '%' || $1 || '%'
       OR COALESCE(e.machine_name, '') ILIKE '%' || $1 || '%')
  AND ($2::text IS NULL OR e.event_type = $2)
  AND ($3::timestamptz IS NULL OR e.occurred_at >= $3)
  AND ($4::timestamptz IS NULL OR e.occurred_at <= $4)
{self._sort(sort_by, sort_dir)}
LIMIT $5 OFFSET $6
"""
        rows = await self.fetch_all(query, search, status, date_from, date_to, limit, offset)
        total = rows[0]["total"] if rows else 0
        return rows, int(total)

    async def get_by_id(self, event_id: str) -> dict[str, Any] | None:
        query = """
SELECT e.id::text AS id,
       e.occurred_at AS timestamp,
       e.event_type AS type,
       COALESCE(e.machine_name, '') AS machine_id,
       COALESCE(NULLIF(e.reason, ''), e.event_type) AS message
FROM bic.ring_events e
WHERE e.id::text = $1
"""
        return await self.fetch_one(query, event_id)
