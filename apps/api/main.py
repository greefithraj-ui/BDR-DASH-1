from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from apps.api.core.config import settings
from apps.api.routers import api_v1
from apps.api.middleware.exceptions import global_exception_handler, validation_exception_handler
from apps.api.middleware.logging import request_logging_middleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API Foundation for Battery Intelligence Platform",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging_middleware)

app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

from apps.api.core.database import db

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    await db.connect()
    logger.info("Database connected.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    await db.disconnect()
    logger.info("Database disconnected.")

app.include_router(api_v1.router, prefix=settings.API_V1_STR)
