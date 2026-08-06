from app.models.domain import SettingsEntry
from app.repositories.settings import SettingsRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class SettingsService(ReadService[SettingsEntry]):
    def __init__(self, repository: SettingsRepository) -> None:
        super().__init__(repository, "settings entry")

    async def list_settings(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[SettingsEntry]]:
        rows = self._repository.list_all()
        if filters.search:
            term = filters.search.lower()
            rows = [r for r in rows if term in r["id"].lower() or term in r["label"].lower()]
        if filters.status:
            status = filters.status.lower()
            rows = [r for r in rows if r["key"].lower() == status]
        rows = self._sort(rows, filters)
        items = [self._to_model(r) for r in rows]
        return await self._page(items, page)

    def _sort(self, rows: list[dict[str, str]], filters: FilterParams) -> list[dict[str, str]]:
        key = filters.sort_by or "label"
        reverse = filters.sort_dir == "desc"
        if key not in {"id", "key", "label"}:
            key = "label"
        return sorted(rows, key=lambda r: (r[key] is None, r[key]), reverse=reverse)

    def _to_model(self, row: dict[str, str]) -> SettingsEntry:
        return SettingsEntry(
            id=row["id"],
            key=row["key"],
            label=row["label"],
            value=row["value"],
        )
