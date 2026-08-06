from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FilterParams(BaseModel):
    """Query parameters accepted by list GET endpoints for narrowing results."""

    model_config = ConfigDict(frozen=True)

    search: str | None = Field(default=None, description="Free-text search term")
    status: str | None = Field(default=None, description="Exact status filter")
    sort_by: str | None = Field(default=None, description="Column to sort by")
    sort_dir: Literal["asc", "desc"] = Field(
        default="asc", description="Sort direction (used with sort_by)"
    )
    date_from: datetime | None = Field(default=None, description="Inclusive start of date range")
    date_to: datetime | None = Field(default=None, description="Inclusive end of date range")
