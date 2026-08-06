from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.rings import RingsService
from apps.api.repositories.rings import RingRepository
import asyncpg

router = APIRouter(tags=["Rings"])

@router.get("/rings", response_model=SuccessResponse[list])
async def get_rings(db: asyncpg.Connection = Depends(get_db_session)):
    repo = RingRepository(db)
    service = RingsService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
