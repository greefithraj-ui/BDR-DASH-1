import asyncpg

from app.repositories.base import BaseSQLRepository


class AdministrationRepository(BaseSQLRepository):
    """SQL access for the administration overview (schema metadata)."""

    def __init__(self, conn: asyncpg.Connection) -> None:
        super().__init__(conn)

    async def schema_version(self) -> int:
        value = await self.fetch_val(
            "SELECT COALESCE(MAX(version), 0) FROM bic.schema_version"
        )
        return int(value or 0)
