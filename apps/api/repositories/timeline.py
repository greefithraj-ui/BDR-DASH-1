from apps.api.repositories.base import BaseRepository

class TimelineRepository(BaseRepository):
    async def get_data(self) -> list:
        # Phase 16.1: Read from bic.ring_events
        
        # TODO: Current SELECT lists are intentionally minimal. Pagination will be implemented later.
        query = "SELECT id, event_type FROM bic.ring_events ORDER BY id DESC LIMIT 10"
        return await self.fetch_all(query)
