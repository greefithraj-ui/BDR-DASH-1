from typing import Any

import asyncpg

from app.repositories.base import BaseSQLRepository
from app.repositories.live import LiveRepository


class PerformanceRepository(BaseSQLRepository):
    """Fleet performance indicators derived from the live tables."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)
        self._live = LiveRepository(conn)

    async def summary(self, freshness_window: int) -> list[dict[str, Any]]:
        agg = await self._live.aggregates(freshness_window)
        machines_total = agg["machines_total"]
        online_pct = (agg["machines_fresh"] / machines_total * 100.0) if machines_total else 0.0
        active_rings = agg["active_rings"]
        utilization_pct = (agg["running_slots"] / active_rings * 100.0) if active_rings else 0.0
        completion_pct = (
            (agg["passed_slots"] + agg["failed_slots"]) / active_rings * 100.0
        ) if active_rings else 0.0
        return [
            {
                "id": "PF-1",
                "metric": "Machines Online",
                "value": round(online_pct, 1),
                "unit": "%",
                "status": "Good" if online_pct >= 80 else "Warn",
            },
            {
                "id": "PF-2",
                "metric": "Slot Utilization",
                "value": round(utilization_pct, 1),
                "unit": "%",
                "status": "Good",
            },
            {
                "id": "PF-3",
                "metric": "Completion Rate",
                "value": round(completion_pct, 1),
                "unit": "%",
                "status": "Good",
            },
            {
                "id": "PF-4",
                "metric": "Running Slots",
                "value": float(agg["running_slots"]),
                "unit": "slots",
                "status": "Good",
            },
            {
                "id": "PF-5",
                "metric": "Failed Slots",
                "value": float(agg["failed_slots"]),
                "unit": "slots",
                "status": "Good" if agg["failed_slots"] == 0 else "Warn",
            },
        ]
