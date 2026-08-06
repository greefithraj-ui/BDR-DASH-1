from typing import Any

from app.config.settings import Settings
from app.models.domain import MetricSummary
from app.repositories.metrics import MetricsRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class MetricsService(ReadService[MetricSummary]):
    def __init__(self, repository: MetricsRepository, settings: Settings) -> None:
        super().__init__(repository, "metric")
        self._settings = settings

    async def list_metrics(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[MetricSummary]]:
        rows = await self._repository.metrics(self._settings.freshness_window_seconds)
        if filters.search:
            term = filters.search.lower()
            rows = [
                r
                for r in rows
                if term in r["id"].lower() or term in r["name"].lower()
            ]
        if filters.status:
            status = filters.status.lower()
            rows = [r for r in rows if r["status"].lower() == status]
        rows = self._sort(rows, filters)
        items = [self._to_model(r) for r in rows]
        return await self._page(items, page)

    def _sort(self, rows: list[dict[str, Any]], filters: FilterParams) -> list[dict[str, Any]]:
        key = filters.sort_by or "name"
        reverse = filters.sort_dir == "desc"
        if key not in {"id", "name", "value"}:
            key = "name"
        return sorted(rows, key=lambda r: (r[key] is None, r[key]), reverse=reverse)

    def _to_model(self, row: dict[str, Any]) -> MetricSummary:
        return MetricSummary(
            id=row["id"],
            name=row["name"],
            value=float(row["value"]),
            unit=row["unit"],
            status=row["status"],
        )
