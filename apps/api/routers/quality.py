from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.quality import QualityService
from apps.api.repositories.quality import QualityRepository
import asyncpg

router = APIRouter(tags=["Quality"])

@router.get("/quality", response_model=SuccessResponse[list])
async def get_quality(db: asyncpg.Connection = Depends(get_db_session)):
    repo = QualityRepository(db)
    service = QualityService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
