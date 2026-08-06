from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_quality_service
from app.models.domain import QualitySummary
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.quality import QualityService

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/summary", response_model=SuccessEnvelope[PaginatedResponse[QualitySummary]], summary="Quality summary")
async def list_summary(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: QualityService = Depends(get_quality_service),
) -> SuccessEnvelope[PaginatedResponse[QualitySummary]]:
    return await service.list_summary(filters, page)
