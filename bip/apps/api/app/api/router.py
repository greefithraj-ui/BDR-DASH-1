from fastapi import APIRouter

from app.api.v1.router import v1_router
from app.routers.health import router as health_router

api_router = APIRouter(prefix="/api")
api_router.include_router(v1_router)
# Legacy alias kept for backward compatibility with the pre-Phase 15 client
# (scripts/check_health.py and apps/web/src/lib/apiClient.ts) that calls /api/health.
api_router.include_router(health_router)
