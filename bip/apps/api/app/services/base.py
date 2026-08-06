from typing import Any, Generic, TypeVar

from app.core.exceptions import ResourceNotFoundError
from app.schemas.common import SuccessEnvelope
from app.schemas.pagination import PageQuery, PaginatedResponse

T = TypeVar("T")


def paginate(records: list[T], query: PageQuery) -> PaginatedResponse[T]:
    total = len(records)
    start = (query.page - 1) * query.page_size
    items = records[start : start + query.page_size]
    return PaginatedResponse(items=items, total=total, page=query.page, page_size=query.page_size)


class ReadService(Generic[T]):
    """Base service for read operations over a repository.

    Concrete services inject their repository via the constructor and own the
    domain logic: mapping raw repository rows to domain models and applying
    business rules. SQL stays exclusively in the repository layer.
    """

    def __init__(self, repository: Any, resource: str) -> None:
        self._repository = repository
        self._resource = resource

    async def get_by_id(self, entity_id: str) -> SuccessEnvelope[T]:
        record = await self._repository.get_by_id(entity_id)
        if record is None:
            raise ResourceNotFoundError(self._resource, entity_id)
        return SuccessEnvelope.ok(self._to_model(record))

    def _to_model(self, row: Any) -> T:
        raise NotImplementedError

    async def _page(
        self, records: list[T], query: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[T]]:
        return SuccessEnvelope.ok(paginate(records, query))

    async def _page_from_db(
        self,
        rows: list[Any],
        total: int,
        query: PageQuery,
    ) -> SuccessEnvelope[PaginatedResponse[T]]:
        items = [self._to_model(row) for row in rows]
        return SuccessEnvelope.ok(
            PaginatedResponse(items=items, total=total, page=query.page, page_size=query.page_size)
        )
