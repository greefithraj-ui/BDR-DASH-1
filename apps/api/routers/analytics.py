from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.analytics import AnalyticsService
from apps.api.repositories.analytics import AnalyticsRepository
import asyncpg

router = APIRouter(tags=["Analytics"])

@router.get("/analytics", response_model=SuccessResponse[list])
async def get_analytics(db: asyncpg.Connection = Depends(get_db_session)):
    repo = AnalyticsRepository(db)
    service = AnalyticsService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
