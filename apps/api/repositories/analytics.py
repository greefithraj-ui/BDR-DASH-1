from apps.api.repositories.base import BaseRepository

class AnalyticsRepository(BaseRepository):
    async def get_data(self) -> list:
        # Phase 16.1: Read from bic.ring_history and bic.ring_events
        
        # TODO: Current SELECT lists are intentionally minimal. Pagination will be implemented later.
        query = """
            SELECT h.id, h.serial_number, e.event_type 
            FROM bic.ring_history h
            LEFT JOIN bic.ring_events e ON h.id = e.id
            LIMIT 10
        """
        return await self.fetch_all(query)
