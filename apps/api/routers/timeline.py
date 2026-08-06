from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.timeline import TimelineService
from apps.api.repositories.timeline import TimelineRepository
import asyncpg

router = APIRouter(tags=["Timeline"])

@router.get("/timeline", response_model=SuccessResponse[list])
async def get_timeline(db: asyncpg.Connection = Depends(get_db_session)):
    repo = TimelineRepository(db)
    service = TimelineService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
