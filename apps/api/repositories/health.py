from apps.api.repositories.base import BaseRepository

class HealthRepository(BaseRepository):
    async def check_health(self) -> bool:
        try:
            # Phase 16.3: Verify connectivity, schema, and permissions without depending on table contents.
            await self.fetch_one("SELECT 1 FROM bic.active_rings LIMIT 1")
            return True
        except Exception:
            return False
