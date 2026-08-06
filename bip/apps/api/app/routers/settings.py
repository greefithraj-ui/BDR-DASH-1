from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_settings_service
from app.models.domain import SettingsEntry
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.settings import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SuccessEnvelope[PaginatedResponse[SettingsEntry]], summary="List settings")
async def list_settings(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: SettingsService = Depends(get_settings_service),
) -> SuccessEnvelope[PaginatedResponse[SettingsEntry]]:
    return await service.list_settings(filters, page)
