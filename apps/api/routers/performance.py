from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.performance import PerformanceService
from apps.api.repositories.performance import PerformanceRepository
import asyncpg

router = APIRouter(tags=["Performance"])

@router.get("/performance", response_model=SuccessResponse[list])
async def get_performance(db: asyncpg.Connection = Depends(get_db_session)):
    repo = PerformanceRepository(db)
    service = PerformanceService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
