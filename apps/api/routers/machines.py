from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.machines import MachinesService
from apps.api.repositories.machines import MachineRepository
import asyncpg

router = APIRouter(tags=["Machines"])

@router.get("/machines", response_model=SuccessResponse[list])
async def get_machines(db: asyncpg.Connection = Depends(get_db_session)):
    repo = MachineRepository(db)
    service = MachinesService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
