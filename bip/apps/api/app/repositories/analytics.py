from typing import Any

import asyncpg

from app.repositories.base import BaseSQLRepository
from app.repositories.live import LiveRepository


class AnalyticsRepository(BaseSQLRepository):
    """Fleet analytics derived from the live ring snapshots."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)
        self._live = LiveRepository(conn)

    async def summary(self, freshness_window: int) -> list[dict[str, Any]]:
        agg = await self._live.aggregates(freshness_window)
        total = agg["active_rings"]
        passed = agg["passed_slots"]
        failed = agg["failed_slots"]
        completed = passed + failed
        pass_rate = (passed / completed * 100.0) if completed else 0.0
        machines_total = agg["machines_total"]
        online_pct = (agg["machines_fresh"] / machines_total * 100.0) if machines_total else 0.0
        return [
            {"id": "AN-1", "key": "active_rings", "label": "Active Rings", "value": float(total), "unit": "rings"},
            {"id": "AN-2", "key": "slots_running", "label": "Slots Running", "value": float(agg["running_slots"]), "unit": "slots"},
            {"id": "AN-3", "key": "pass_rate", "label": "Pass Rate", "value": round(pass_rate, 1), "unit": "%"},
            {"id": "AN-4", "key": "machines_online", "label": "Machines Online", "value": float(agg["machines_fresh"]), "unit": "machines"},
            {"id": "AN-5", "key": "collector_health", "label": "Collector Health", "value": round(online_pct, 1), "unit": "%"},
        ]
