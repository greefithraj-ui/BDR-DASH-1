from typing import Any

from app.core.exceptions import ResourceNotFoundError
from app.models.domain import TimelineEvent
from app.repositories.timeline import TimelineRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class TimelineService(ReadService[TimelineEvent]):
    def __init__(self, repository: TimelineRepository) -> None:
        super().__init__(repository, "timeline event")

    async def list_events(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[TimelineEvent]]:
        rows, total = await self._repository.list_events(
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

    async def get_by_id(self, event_id: str) -> SuccessEnvelope[TimelineEvent]:
        row = await self._repository.get_by_id(event_id)
        if row is None:
            raise ResourceNotFoundError(self._resource, event_id)
        return SuccessEnvelope.ok(self._to_model(row))

    def _to_model(self, row: dict[str, Any]) -> TimelineEvent:
        return TimelineEvent(
            id=row["id"],
            timestamp=row["timestamp"],
            type=row["type"],
            machine_id=row["machine_id"],
            message=row["message"],
        )
