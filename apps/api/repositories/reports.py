from apps.api.repositories.base import BaseRepository

class ReportsRepository(BaseRepository):
    async def get_data(self) -> list:
        # Phase 16.1: Read from bic.ring_history
        
        # TODO: Current SELECT lists are intentionally minimal. Pagination will be implemented later.
        query = "SELECT id, serial_number FROM bic.ring_history LIMIT 10"
        return await self.fetch_all(query)
