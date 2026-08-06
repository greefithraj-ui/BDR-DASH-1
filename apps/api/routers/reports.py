from fastapi import APIRouter, Depends
from apps.api.models.response import SuccessResponse
from apps.api.dependencies.providers import get_db_session
from apps.api.services.reports import ReportsService
from apps.api.repositories.reports import ReportsRepository
import asyncpg

router = APIRouter(tags=["Reports"])

@router.get("/reports", response_model=SuccessResponse[list])
async def get_reports(db: asyncpg.Connection = Depends(get_db_session)):
    repo = ReportsRepository(db)
    service = ReportsService(repo)
    data = await service.get_data()
    return SuccessResponse(data=data)
