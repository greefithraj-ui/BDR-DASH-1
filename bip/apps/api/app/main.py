import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware
from app.db.session import db

logger = logging.getLogger("bip")

OPENAPI_TAGS = [
    {"name": "health", "description": "Service health and readiness."},
    {"name": "metrics", "description": "Platform metrics and KPIs."},
    {"name": "machines", "description": "Machine registry."},
    {"name": "rings", "description": "Battery production rings."},
    {"name": "reports", "description": "Generated reports."},
    {"name": "analytics", "description": "Analytics summaries."},
    {"name": "timeline", "description": "Timeline events."},
    {"name": "prediction", "description": "Prediction models."},
    {"name": "quality", "description": "Quality summaries."},
    {"name": "performance", "description": "Performance summaries."},
    {"name": "administration", "description": "Administration overview."},
    {"name": "settings", "description": "Platform settings."},
    {"name": "system", "description": "System information."},
]


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Application startup: %s v%s (%s)",
        application.title,
        application.version,
        application.docs_url,
    )
    await db.connect()
    yield
    await db.disconnect()
    logger.info("Application shutdown complete: %s", application.title)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    application = FastAPI(
        title=settings.app_name,
        version=settings.api_version,
        description="Battery Intelligence Platform API. Serves live operational data from the read-only battery database: metrics, machines, rings, timeline events, analytics, quality, performance, administration, settings, system, health, and generated reports (CSV/XLSX/PDF downloads).",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )

    register_middleware(application, settings)
    register_exception_handlers(application)
    application.include_router(api_router)

    return application


app = create_app()
