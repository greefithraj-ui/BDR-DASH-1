from typing import Any

from app.config.settings import Settings
from app.core.exceptions import ResourceNotFoundError
from app.models.domain import Machine
from app.repositories.machines import MachinesRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class MachinesService(ReadService[Machine]):
    def __init__(self, repository: MachinesRepository, settings: Settings) -> None:
        super().__init__(repository, "machine")
        self._settings = settings

    async def list_machines(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[Machine]]:
        rows, total = await self._repository.list_machines(
            freshness_window=self._settings.freshness_window_seconds,
            search=filters.search,
            status=filters.status,
            sort_by=filters.sort_by,
            sort_dir=filters.sort_dir,
            date_from=filters.date_from,
            date_to=filters.date_to,
            limit=page.page_size,
            offset=(page.page - 1) * page.page_size,
        )
        stats = self._stats_map(await self._repository.fleet_stats())
        items = [self._to_model_with_stats(row, stats) for row in rows]
        return SuccessEnvelope.ok(
            PaginatedResponse(items=items, total=total, page=page.page, page_size=page.page_size)
        )

    async def get_by_id(self, machine_id: str) -> SuccessEnvelope[Machine]:
        row = await self._repository.get_machine(
            machine_id, freshness_window=self._settings.freshness_window_seconds
        )
        if row is None:
            raise ResourceNotFoundError(self._resource, machine_id)
        stats = self._stats_map(await self._repository.fleet_stats())
        return SuccessEnvelope.ok(self._to_model_with_stats(row, stats))

    def _stats_map(self, stats_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {row["machine_name"]: row for row in stats_rows}

    def _to_model_with_stats(self, row: dict[str, Any], stats: dict[str, dict[str, Any]]) -> Machine:
        stat = stats.get(row["machine_name"], {})
        is_online = bool(row["is_online"])
        failed = int(stat.get("failed_count") or 0)
        slot_count = int(stat.get("slot_count") or 0)
        if not is_online:
            status = "Offline"
        elif failed > 0:
            status = "Warning"
        else:
            status = "Healthy"
        return Machine(
            id=row["machine_name"],
            name=row["machine_name"],
            status=status,
            connection="Online" if is_online else "Offline",
            health_score=self._health_score(is_online, failed, slot_count),
            firmware=stat.get("dominant_firmware") or "",
            last_seen=row["last_seen_at"],
        )

    @staticmethod
    def _health_score(is_online: bool, failed: int, slot_count: int) -> float:
        score = 100.0 if is_online else 40.0
        score -= failed * 4.0
        return max(0.0, min(100.0, round(score, 1)))

    def _to_model(self, row: Any) -> Machine:  # pragma: no cover - helper hook
        return self._to_model_with_stats(row, {})
