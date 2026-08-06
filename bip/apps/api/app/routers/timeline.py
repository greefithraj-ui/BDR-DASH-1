from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_timeline_service
from app.models.domain import TimelineEvent
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.timeline import TimelineService

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=SuccessEnvelope[PaginatedResponse[TimelineEvent]], summary="List timeline events")
async def list_events(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: TimelineService = Depends(get_timeline_service),
) -> SuccessEnvelope[PaginatedResponse[TimelineEvent]]:
    return await service.list_events(filters, page)


@router.get("/{event_id}", response_model=SuccessEnvelope[TimelineEvent], summary="Get one timeline event")
async def get_event(
    event_id: str,
    service: TimelineService = Depends(get_timeline_service),
) -> SuccessEnvelope[TimelineEvent]:
    return await service.get_by_id(event_id)
