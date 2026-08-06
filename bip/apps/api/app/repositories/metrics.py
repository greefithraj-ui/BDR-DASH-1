from typing import Any

import asyncpg

from app.repositories.base import BaseSQLRepository
from app.repositories.live import LiveRepository


class MetricsRepository(BaseSQLRepository):
    """Fleet metrics derived from the live tables."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)
        self._live = LiveRepository(conn)

    async def metrics(self, freshness_window: int) -> list[dict[str, Any]]:
        agg = await self._live.aggregates(freshness_window)
        machines_ok = agg["machines_total"] == 0 or agg["machines_fresh"] >= agg["machines_total"]
        return [
            {
                "id": "MT-1",
                "name": "Active Rings",
                "value": float(agg["active_rings"]),
                "unit": "rings",
                "status": "ok",
            },
            {
                "id": "MT-2",
                "name": "Machines Online",
                "value": float(agg["machines_fresh"]),
                "unit": "machines",
                "status": "ok" if machines_ok else "warn",
            },
            {
                "id": "MT-3",
                "name": "BDR Slots",
                "value": float(agg["bdr_slots"]),
                "unit": "slots",
                "status": "ok",
            },
            {
                "id": "MT-4",
                "name": "Pending Removal",
                "value": float(agg["pending_removal"]),
                "unit": "rings",
                "status": "warn" if agg["pending_removal"] else "ok",
            },
            {
                "id": "MT-5",
                "name": "Finalized Rings",
                "value": float(agg["finalized_rings"]),
                "unit": "rings",
                "status": "ok",
            },
            {
                "id": "MT-6",
                "name": "Ring Events",
                "value": float(agg["ring_events"]),
                "unit": "events",
                "status": "ok",
            },
        ]
