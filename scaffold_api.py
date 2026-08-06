import os
import textwrap

BASE_DIR = r"d:\BDR\apps\api"

dirs = [
    "app",
    "core",
    "config",
    "middleware",
    "dependencies",
    "models",
    "schemas",
    "routers",
    "repositories",
    "services",
    "utils",
]

for d in dirs:
    os.makedirs(os.path.join(BASE_DIR, d), exist_ok=True)
    with open(os.path.join(BASE_DIR, d, "__init__.py"), "w") as f:
        pass

# core/config.py
config_content = """\
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Battery Intelligence Platform API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
"""
with open(os.path.join(BASE_DIR, "core", "config.py"), "w") as f:
    f.write(config_content)

# models/response.py
response_model = """\
from pydantic import BaseModel, Field
from typing import Any, Generic, TypeVar, Optional, List
from datetime import datetime, timezone

T = TypeVar("T")

def current_time():
    return datetime.now(timezone.utc)

class Timestamp(BaseModel):
    created_at: datetime = Field(default_factory=current_time)
    updated_at: Optional[datetime] = None

class Metadata(BaseModel):
    version: str = "1.0.0"
    environment: str = "development"
    timestamp: datetime = Field(default_factory=current_time)

class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: Optional[Metadata] = Field(default_factory=Metadata)

class ErrorResponse(BaseModel):
    success: bool = False
    error_code: str
    message: str
    details: Optional[Any] = None
    meta: Optional[Metadata] = Field(default_factory=Metadata)

class PaginationResponse(BaseModel, Generic[T]):
    success: bool = True
    data: List[T]
    total: int
    page: int
    size: int
    meta: Optional[Metadata] = Field(default_factory=Metadata)

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=current_time)

class Filter(BaseModel):
    field: str
    operator: str
    value: Any
"""
with open(os.path.join(BASE_DIR, "models", "response.py"), "w") as f:
    f.write(response_model)

# middleware/exceptions.py
middleware_exceptions = """\
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from apps.api.models.response import ErrorResponse

async def global_exception_handler(request: Request, exc: Exception):
    error = ErrorResponse(
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
        details=str(exc)
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error.dict())

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error = ErrorResponse(
        error_code="VALIDATION_ERROR",
        message="Request validation failed.",
        details=exc.errors()
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error.dict())
"""
with open(os.path.join(BASE_DIR, "middleware", "exceptions.py"), "w") as f:
    f.write(middleware_exceptions)

# middleware/logging.py
middleware_logging = """\
from fastapi import Request
import logging
import time

logger = logging.getLogger(__name__)

async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response
"""
with open(os.path.join(BASE_DIR, "middleware", "logging.py"), "w") as f:
    f.write(middleware_logging)

# routers
routers_list = [
    "health",
    "metrics",
    "machines",
    "rings",
    "timeline",
    "analytics",
    "reports",
    "quality",
    "performance",
    "prediction",
    "administration",
    "settings",
    "system"
]

for router_name in routers_list:
    if router_name == "health":
        content = """\
from fastapi import APIRouter
from apps.api.models.response import HealthResponse
from apps.api.core.config import settings
from datetime import datetime, timezone

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
async def get_health():
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc)
    )
"""
    else:
        content = f"""\
from fastapi import APIRouter
from apps.api.models.response import SuccessResponse

router = APIRouter(tags=["{router_name.capitalize()}"])

@router.get("/{router_name}", response_model=SuccessResponse[dict])
async def get_{router_name}():
    return SuccessResponse(data={{"message": "{router_name} endpoint placeholder"}})
"""
    with open(os.path.join(BASE_DIR, "routers", f"{router_name}.py"), "w") as f:
        f.write(content)

# routers/api_v1.py
api_v1_content = "from fastapi import APIRouter\n"
for r in routers_list:
    api_v1_content += f"from apps.api.routers import {r}\n"

api_v1_content += "\nrouter = APIRouter()\n"
for r in routers_list:
    prefix = "" if r == "health" else f"/{r}"
    # Wait, the health endpoint is /api/v1/health. The router itself defines @router.get("/health"), so no prefix needed.
    # The others define @router.get("/metrics") etc, so no prefix needed there either!
    api_v1_content += f"router.include_router({r}.router)\n"

with open(os.path.join(BASE_DIR, "routers", "api_v1.py"), "w") as f:
    f.write(api_v1_content)


# main.py
main_content = """\
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

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")

app.include_router(api_v1.router, prefix=settings.API_V1_STR)
"""
with open(os.path.join(BASE_DIR, "main.py"), "w") as f:
    f.write(main_content)

# repositories/base.py
base_repo = """\
class BaseRepository:
    def __init__(self):
        pass

    def get_all(self):
        raise NotImplementedError("Method not implemented")

    def get_by_id(self, id: int):
        raise NotImplementedError("Method not implemented")
"""
with open(os.path.join(BASE_DIR, "repositories", "base.py"), "w") as f:
    f.write(base_repo)

# services/base.py
base_service = """\
class BaseService:
    def __init__(self, repository):
        self.repository = repository
        
    def get_all(self):
        return self.repository.get_all()
"""
with open(os.path.join(BASE_DIR, "services", "base.py"), "w") as f:
    f.write(base_service)

# dependencies/providers.py
providers = """\
# Dependency injection placeholders
def get_db_session():
    # Placeholder for database session
    yield None

def get_current_user():
    # Placeholder for authentication
    return None
"""
with open(os.path.join(BASE_DIR, "dependencies", "providers.py"), "w") as f:
    f.write(providers)

print("Scaffolding complete.")
