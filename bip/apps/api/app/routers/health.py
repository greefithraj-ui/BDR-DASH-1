from fastapi import APIRouter, Depends

from app.dependencies.services import get_health_service
from app.models.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse, summary="Service health", description="Returns the health payload of the platform.")
async def get_health(service: HealthService = Depends(get_health_service)) -> HealthResponse:
    return await service.get_health()
