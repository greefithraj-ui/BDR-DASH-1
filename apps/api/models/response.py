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
