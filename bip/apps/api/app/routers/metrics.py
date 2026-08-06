from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_metrics_service
from app.models.domain import MetricSummary
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.metrics import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=SuccessEnvelope[PaginatedResponse[MetricSummary]], summary="List metrics")
async def list_metrics(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: MetricsService = Depends(get_metrics_service),
) -> SuccessEnvelope[PaginatedResponse[MetricSummary]]:
    return await service.list_metrics(filters, page)


@router.get("/{metric_id}", response_model=SuccessEnvelope[MetricSummary], summary="Get one metric")
async def get_metric(
    metric_id: str,
    service: MetricsService = Depends(get_metrics_service),
) -> SuccessEnvelope[MetricSummary]:
    return await service.get_by_id(metric_id)
