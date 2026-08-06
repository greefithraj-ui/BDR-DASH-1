from typing import Any

from app.config.settings import Settings
from app.models.domain import QualitySummary
from app.repositories.quality import QualityRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class QualityService(ReadService[QualitySummary]):
    def __init__(self, repository: QualityRepository, settings: Settings) -> None:
        super().__init__(repository, "quality summary")
        self._settings = settings

    async def list_summary(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[QualitySummary]]:
        rows = await self._repository.summary(self._settings.freshness_window_seconds)
        if filters.search:
            term = filters.search.lower()
            rows = [r for r in rows if term in r["id"].lower() or term in r["metric"].lower()]
        if filters.status:
            status = filters.status.lower()
            rows = [r for r in rows if r["status"].lower() == status]
        rows = self._sort(rows, filters)
        items = [self._to_model(r) for r in rows]
        return await self._page(items, page)

    def _sort(self, rows: list[dict[str, Any]], filters: FilterParams) -> list[dict[str, Any]]:
        key = filters.sort_by or "metric"
        reverse = filters.sort_dir == "desc"
        if key not in {"id", "metric", "value"}:
            key = "metric"
        return sorted(rows, key=lambda r: (r[key] is None, r[key]), reverse=reverse)

    def _to_model(self, row: dict[str, Any]) -> QualitySummary:
        return QualitySummary(
            id=row["id"],
            metric=row["metric"],
            value=float(row["value"]),
            target=float(row["target"]),
            status=row["status"],
        )
