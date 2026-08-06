from fastapi import APIRouter
from apps.api.routers import health
from apps.api.routers import metrics
from apps.api.routers import machines
from apps.api.routers import rings
from apps.api.routers import timeline
from apps.api.routers import analytics
from apps.api.routers import reports
from apps.api.routers import quality
from apps.api.routers import performance
from apps.api.routers import prediction
from apps.api.routers import administration
from apps.api.routers import settings
from apps.api.routers import system

router = APIRouter()
router.include_router(health.router)
router.include_router(metrics.router)
router.include_router(machines.router)
router.include_router(rings.router)
router.include_router(timeline.router)
router.include_router(analytics.router)
router.include_router(reports.router)
router.include_router(quality.router)
router.include_router(performance.router)
router.include_router(prediction.router)
router.include_router(administration.router)
router.include_router(settings.router)
router.include_router(system.router)
