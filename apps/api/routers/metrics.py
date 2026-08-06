from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.metrics import MetricsService
from apps.api.repositories.metrics import MetricsRepository
import asyncpg

router = APIRouter(tags=["Metrics"])

@router.get("/metrics", response_model=SuccessResponse[list])
async def get_metrics(db: asyncpg.Connection = Depends(get_db_session)):
    repo = MetricsRepository(db)
    service = MetricsService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
