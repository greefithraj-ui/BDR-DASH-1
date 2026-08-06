from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_performance_service
from app.models.domain import PerformanceSummary
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.performance import PerformanceService

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/summary", response_model=SuccessEnvelope[PaginatedResponse[PerformanceSummary]], summary="Performance summary")
async def list_summary(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: PerformanceService = Depends(get_performance_service),
) -> SuccessEnvelope[PaginatedResponse[PerformanceSummary]]:
    return await service.list_summary(filters, page)
