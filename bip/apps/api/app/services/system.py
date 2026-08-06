from app.models.domain import SystemInfo
from app.repositories.system import SystemRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class SystemService(ReadService[SystemInfo]):
    def __init__(self, repository: SystemRepository) -> None:
        super().__init__(repository, "system info")

    async def list_info(self, page: PageQuery) -> SuccessEnvelope[PaginatedResponse[SystemInfo]]:
        rows = self._repository.list_all()
        items = [self._to_model(r) for r in rows]
        return await self._page(items, page)

    def _to_model(self, row: dict[str, str]) -> SystemInfo:
        return SystemInfo(
            id=row["id"],
            hostname=row["hostname"],
            python_version=row["python_version"],
            framework=row["framework"],
            version=row["version"],
        )
