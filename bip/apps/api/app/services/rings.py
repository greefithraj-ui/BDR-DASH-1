from typing import Any

from app.core.exceptions import ResourceNotFoundError
from app.models.domain import Ring
from app.repositories.rings import RingsRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class RingsService(ReadService[Ring]):
    def __init__(self, repository: RingsRepository) -> None:
        super().__init__(repository, "ring")

    async def list_rings(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[Ring]]:
        rows, total = await self._repository.list_rings(
            search=filters.search,
            status=filters.status,
            sort_by=filters.sort_by,
            sort_dir=filters.sort_dir,
            date_from=filters.date_from,
            date_to=filters.date_to,
            limit=page.page_size,
            offset=(page.page - 1) * page.page_size,
        )
        return await self._page_from_db(rows, total, page)

    async def get_by_id(self, ring_id: str) -> SuccessEnvelope[Ring]:
        row = await self._repository.get_by_id(ring_id)
        if row is None:
            raise ResourceNotFoundError(self._resource, ring_id)
        return SuccessEnvelope.ok(self._to_model(row))

    def _to_model(self, row: dict[str, Any]) -> Ring:
        return Ring(
            id=row["ring_id"],
            name=row["ring_name"] or row["ring_id"],
            status=row["status"],
            capacity_mwh=float(row["slot_count"]),
            installed_at=row["installed_at"],
        )
