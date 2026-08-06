import time
from typing import Any

from app.config.settings import Settings
from app.models.domain import AdministrationOverview
from app.repositories.administration import AdministrationRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService

_PROCESS_START = time.time()


class AdministrationService(ReadService[AdministrationOverview]):
    def __init__(self, repository: AdministrationRepository, settings: Settings) -> None:
        super().__init__(repository, "administration overview")
        self._settings = settings

    async def list_overview(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[AdministrationOverview]]:
        rows = await self._overview_rows()
        if filters.search:
            term = filters.search.lower()
            rows = [r for r in rows if term in r["id"].lower() or term in r["platform"].lower()]
        rows = self._sort(rows, filters)
        items = [self._to_model(r) for r in rows]
        return await self._page(items, page)

    async def _overview_rows(self) -> list[dict[str, Any]]:
        schema_version = await self._repository.schema_version()
        return [
            {
                "id": "ADM-1",
                "platform": "Battery Intelligence Platform API",
                "version": self._settings.api_version,
                "environment": self._settings.environment,
                "uptime_seconds": int(time.time() - _PROCESS_START),
            },
            {
                "id": "ADM-2",
                "platform": "BIC Read-Only Database",
                "version": f"schema v{schema_version}",
                "environment": "bic",
                "uptime_seconds": 0,
            },
        ]

    def _sort(self, rows: list[dict[str, Any]], filters: FilterParams) -> list[dict[str, Any]]:
        key = filters.sort_by or "platform"
        reverse = filters.sort_dir == "desc"
        if key not in {"id", "platform", "version"}:
            key = "platform"
        return sorted(rows, key=lambda r: (r[key] is None, r[key]), reverse=reverse)

    def _to_model(self, row: dict[str, Any]) -> AdministrationOverview:
        return AdministrationOverview(
            id=row["id"],
            platform=row["platform"],
            version=row["version"],
            environment=row["environment"],
            uptime_seconds=int(row["uptime_seconds"]),
        )
