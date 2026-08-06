from datetime import datetime
from typing import Any

import asyncpg

from app.repositories.base import BaseSQLRepository
from app.repositories.live import LiveRepository


class MachinesRepository(BaseSQLRepository):
    """SQL access for machines, sourced from the live ring/BDR snapshots."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)
        self._live = LiveRepository(conn)

    async def list_machines(
        self,
        *,
        freshness_window: int,
        search: str | None,
        status: str | None,
        sort_by: str | None,
        sort_dir: str,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        return await self._live.list_machines(
            freshness_window=freshness_window,
            search=search,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

    async def get_machine(self, machine_name: str, *, freshness_window: int) -> dict[str, Any] | None:
        return await self._live.get_machine(machine_name, freshness_window=freshness_window)

    async def fleet_stats(self) -> list[dict[str, Any]]:
        return await self._live.fleet_stats()
