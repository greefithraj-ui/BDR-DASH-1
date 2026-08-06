from apps.api.repositories.base import BaseRepository

class RingRepository(BaseRepository):
    async def get_data(self) -> list:
        # Phase 16.1: Read from bic.active_rings and join bic.ring_identities
        
        # TODO: Current SELECT lists are intentionally minimal. Pagination will be implemented later.
        query = """
            SELECT a.id, a.serial_number, i.serial_number as identity_serial 
            FROM bic.active_rings a
            LEFT JOIN bic.ring_identities i ON a.serial_number = i.serial_number
            LIMIT 10
        """
        return await self.fetch_all(query)
