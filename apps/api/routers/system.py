from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.system import SystemService
from apps.api.repositories.system import SystemRepository
import asyncpg

router = APIRouter(tags=["System"])

@router.get("/system", response_model=SuccessResponse[list])
async def get_system(db: asyncpg.Connection = Depends(get_db_session)):
    repo = SystemRepository(db)
    service = SystemService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
