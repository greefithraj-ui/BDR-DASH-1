from fastapi import APIRouter, Depends
from apps.api.models.response import HealthResponse
from apps.api.core.config import settings
from apps.api.dependencies.providers import get_db_session
from apps.api.services.health import HealthService
from apps.api.repositories.health import HealthRepository
from datetime import datetime, timezone
import asyncpg

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def get_health(db: asyncpg.Connection = Depends(get_db_session)):
    repo = HealthRepository(db)
    service = HealthService(repo)
    db_status = await service.check_db_health()
    
    return HealthResponse(
        status="healthy" if db_status else "unhealthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc)
    )
