from typing import AsyncIterator

import asyncpg
from fastapi import HTTPException, status

from app.db.session import db


async def get_db_connection() -> AsyncIterator[asyncpg.Connection]:
    """Yield a pooled read-only connection for the duration of one request."""
    try:
        pool = db.pool()
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not available.",
        )
    async with pool.acquire() as conn:
        yield conn
