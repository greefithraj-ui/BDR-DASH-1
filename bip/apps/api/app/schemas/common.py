from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.utils.time import utc_now_iso

T = TypeVar("T")


class SuccessEnvelope(BaseModel, Generic[T]):
    """Standard success response wrapping `data` with optional `meta`."""

    model_config = ConfigDict(frozen=True)

    data: T
    meta: dict[str, str | int | None] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T) -> "SuccessEnvelope[T]":
        return cls(data=data, meta={"generated_at": utc_now_iso()})


class ErrorModel(BaseModel):
    """Standard error response used by all exception handlers."""

    model_config = ConfigDict(frozen=True)

    error: str
    message: str
    status_code: int
    timestamp: datetime
