from app.models.domain import PredictionModel
from app.repositories.prediction import PredictionRepository
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.base import ReadService


class PredictionService(ReadService[PredictionModel]):
    """Prediction models remain a documented placeholder: the read-only
    database exposes no model catalogue, so an in-memory source is kept."""

    def __init__(self, repository: PredictionRepository) -> None:
        super().__init__(repository, "prediction model")

    async def list_models(
        self, filters: FilterParams, page: PageQuery
    ) -> SuccessEnvelope[PaginatedResponse[PredictionModel]]:
        records = await self._repository.list_all()
        if filters.search:
            term = filters.search.lower()
            records = [r for r in records if term in r.id.lower() or term in r.name.lower()]
        if filters.status:
            status = filters.status.lower()
            records = [r for r in records if r.status.lower() == status]
        return await self._page(records, page)

    def _to_model(self, row: PredictionModel) -> PredictionModel:
        return row
