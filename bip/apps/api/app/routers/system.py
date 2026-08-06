from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_system_service
from app.models.domain import SystemInfo
from app.schemas.common import SuccessEnvelope
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.system import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info", response_model=SuccessEnvelope[PaginatedResponse[SystemInfo]], summary="System information")
async def list_info(
    page: Annotated[PageQuery, Depends()],
    service: SystemService = Depends(get_system_service),
) -> SuccessEnvelope[PaginatedResponse[SystemInfo]]:
    return await service.list_info(page)
