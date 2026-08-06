from fastapi import APIRouter

from app.routers import (
    administration_router,
    analytics_router,
    health_router,
    machines_router,
    metrics_router,
    performance_router,
    prediction_router,
    quality_router,
    reports_router,
    rings_router,
    settings_router,
    system_router,
    timeline_router,
)

v1_router = APIRouter(prefix="/v1", tags=["v1"])
v1_router.include_router(health_router)
v1_router.include_router(metrics_router)
v1_router.include_router(machines_router)
v1_router.include_router(rings_router)
v1_router.include_router(reports_router)
v1_router.include_router(analytics_router)
v1_router.include_router(timeline_router)
v1_router.include_router(prediction_router)
v1_router.include_router(quality_router)
v1_router.include_router(performance_router)
v1_router.include_router(administration_router)
v1_router.include_router(settings_router)
v1_router.include_router(system_router)
