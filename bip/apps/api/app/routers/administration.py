from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_administration_service
from app.models.domain import AdministrationOverview
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.administration import AdministrationService

router = APIRouter(prefix="/administration", tags=["administration"])


@router.get(
    "/overview",
    response_model=SuccessEnvelope[PaginatedResponse[AdministrationOverview]],
    summary="Administration overview",
)
async def list_overview(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: AdministrationService = Depends(get_administration_service),
) -> SuccessEnvelope[PaginatedResponse[AdministrationOverview]]:
    return await service.list_overview(filters, page)
