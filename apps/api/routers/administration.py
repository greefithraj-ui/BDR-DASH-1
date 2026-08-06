from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.administration import AdministrationService
from apps.api.repositories.administration import AdministrationRepository
import asyncpg

router = APIRouter(tags=["Administration"])

@router.get("/administration", response_model=SuccessResponse[list])
async def get_administration(db: asyncpg.Connection = Depends(get_db_session)):
    repo = AdministrationRepository(db)
    service = AdministrationService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
