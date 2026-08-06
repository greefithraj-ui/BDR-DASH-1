from typing import Any

import asyncpg

from app.repositories.base import BaseSQLRepository
from app.repositories.live import LiveRepository


class QualityRepository(BaseSQLRepository):
    """Quality indicators derived from live slot outcome states."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)
        self._live = LiveRepository(conn)

    async def summary(self, freshness_window: int) -> list[dict[str, Any]]:
        agg = await self._live.aggregates(freshness_window)
        passed = agg["passed_slots"]
        failed = agg["failed_slots"]
        completed = passed + failed
        pass_rate = (passed / completed * 100.0) if completed else 0.0
        return [
            {
                "id": "QL-1",
                "metric": "Pass Rate",
                "value": round(pass_rate, 1),
                "target": 100.0,
                "status": "Pass",
            },
            {
                "id": "QL-2",
                "metric": "Failed Slots",
                "value": float(failed),
                "target": 0.0,
                "status": "Pass" if failed == 0 else "Warn",
            },
            {
                "id": "QL-3",
                "metric": "Running Slots",
                "value": float(agg["running_slots"]),
                "target": 0.0,
                "status": "Pass",
            },
            {
                "id": "QL-4",
                "metric": "Assigned Slots",
                "value": float(agg["assigned_slots"]),
                "target": 0.0,
                "status": "Pass",
            },
            {
                "id": "QL-5",
                "metric": "Completed Slots",
                "value": float(completed),
                "target": 0.0,
                "status": "Pass",
            },
        ]
