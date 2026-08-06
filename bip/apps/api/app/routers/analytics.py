from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_analytics_service
from app.models.domain import AnalyticsSummary
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=SuccessEnvelope[PaginatedResponse[AnalyticsSummary]], summary="Analytics summary")
async def list_summary(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: AnalyticsService = Depends(get_analytics_service),
) -> SuccessEnvelope[PaginatedResponse[AnalyticsSummary]]:
    return await service.list_summary(filters, page)
