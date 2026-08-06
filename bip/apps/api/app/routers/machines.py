from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.services import get_machines_service
from app.models.domain import Machine
from app.schemas.common import SuccessEnvelope
from app.schemas.filters import FilterParams
from app.schemas.pagination import PageQuery, PaginatedResponse
from app.services.machines import MachinesService

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("", response_model=SuccessEnvelope[PaginatedResponse[Machine]], summary="List machines")
async def list_machines(
    filters: Annotated[FilterParams, Depends()],
    page: Annotated[PageQuery, Depends()],
    service: MachinesService = Depends(get_machines_service),
) -> SuccessEnvelope[PaginatedResponse[Machine]]:
    return await service.list_machines(filters, page)


@router.get("/{machine_id}", response_model=SuccessEnvelope[Machine], summary="Get one machine")
async def get_machine(
    machine_id: str,
    service: MachinesService = Depends(get_machines_service),
) -> SuccessEnvelope[Machine]:
    return await service.get_by_id(machine_id)
