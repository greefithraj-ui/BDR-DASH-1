from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_rings_service
from app.models.domain import Ring
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.rings import RingsService

router = APIRouter(prefix="/rings", tags=["rings"])


@router.get("", response_model=SuccessEnvelope[PaginatedResponse[Ring]], summary="List rings")
async def list_rings(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: RingsService = Depends(get_rings_service),
) -> SuccessEnvelope[PaginatedResponse[Ring]]:
    return await service.list_rings(filters, page)


@router.get("/{ring_id}", response_model=SuccessEnvelope[Ring], summary="Get one ring")
async def get_ring(
    ring_id: str,
    service: RingsService = Depends(get_rings_service),
) -> SuccessEnvelope[Ring]:
    return await service.get_by_id(ring_id)
