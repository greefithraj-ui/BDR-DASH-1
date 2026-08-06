from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.settings import SettingsService
from apps.api.repositories.settings import SettingsRepository
import asyncpg

router = APIRouter(tags=["Settings"])

@router.get("/settings", response_model=SuccessResponse[list])
async def get_settings(db: asyncpg.Connection = Depends(get_db_session)):
    repo = SettingsRepository(db)
    service = SettingsService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
