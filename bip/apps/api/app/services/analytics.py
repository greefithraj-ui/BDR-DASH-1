from typing import Any

from app.config.settings import Settings
from app.models.domain import AnalyticsSummary
from app.repositories.analytics import AnalyticsRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class AnalyticsService(ReadService[AnalyticsSummary]):
    def __init__(self, repository: AnalyticsRepository, settings: Settings) -> None:
        super().__init__(repository, "analytics")
        self._settings = settings

    async def list_summary(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[AnalyticsSummary]]:
        rows = await self._repository.summary(self._settings.freshness_window_seconds)
        if filters.search:
            term = filters.search.lower()
            rows = [
                r
                for r in rows
                if term in r["id"].lower() or term in r["label"].lower()
            ]
        rows = self._sort(rows, filters)
        items = [self._to_model(r) for r in rows]
        return await self._page(items, page)

    def _sort(self, rows: list[dict[str, Any]], filters: FilterParams) -> list[dict[str, Any]]:
        key = filters.sort_by or "label"
        reverse = filters.sort_dir == "desc"
        if key not in {"id", "label", "key", "value"}:
            key = "label"
        return sorted(rows, key=lambda r: (r[key] is None, r[key]), reverse=reverse)

    def _to_model(self, row: dict[str, Any]) -> AnalyticsSummary:
        return AnalyticsSummary(
            id=row["id"],
            key=row["key"],
            label=row["label"],
            value=float(row["value"]),
            unit=row["unit"],
        )
