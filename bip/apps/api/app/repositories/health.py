from typing import Any

import asyncpg

from app.repositories.base import BaseSQLRepository


class HealthRepository(BaseSQLRepository):
    """Database-backed health data source."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)

    async def get_health_data(self) -> dict[str, Any]:
        schema_version = await self.fetch_val(
            "SELECT COALESCE(MAX(version), 0) FROM bic.schema_version"
        )
        return {
            "status": "ok",
            "service": "Battery Intelligence Platform API",
            "schema_version": int(schema_version or 0),
        }
