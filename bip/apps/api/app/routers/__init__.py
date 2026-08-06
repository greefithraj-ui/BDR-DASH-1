from app.routers.administration import router as administration_router
from app.routers.analytics import router as analytics_router
from app.routers.health import router as health_router
from app.routers.machines import router as machines_router
from app.routers.metrics import router as metrics_router
from app.routers.performance import router as performance_router
from app.routers.prediction import router as prediction_router
from app.routers.quality import router as quality_router
from app.routers.reports import router as reports_router
from app.routers.rings import router as rings_router
from app.routers.settings import router as settings_router
from app.routers.system import router as system_router
from app.routers.timeline import router as timeline_router

__all__ = [
    "administration_router",
    "analytics_router",
    "health_router",
    "machines_router",
    "metrics_router",
    "performance_router",
    "prediction_router",
    "quality_router",
    "reports_router",
    "rings_router",
    "settings_router",
    "system_router",
    "timeline_router",
]
