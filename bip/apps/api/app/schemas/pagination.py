from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageQuery(BaseModel):
    """Query parameters accepted by every paginated GET endpoint."""

    model_config = ConfigDict(frozen=True)

    page: int = Field(default=1, ge=1, description="One-based page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response."""

    model_config = ConfigDict(frozen=True)

    items: list[T]
    total: int
    page: int
    page_size: int
