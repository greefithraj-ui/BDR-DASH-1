from apps.api.repositories.base import BaseRepository

class MachineRepository(BaseRepository):
    async def get_data(self) -> list:
        # Phase 16.1: Read from bic.machine_checkpoint and public.live_rings_raw where appropriate
        
        # TODO: Current SELECT lists are intentionally minimal. Pagination will be implemented later.
        query = """
            SELECT m.machine_name, l.downloaded_at
            FROM bic.machine_checkpoint m
            LEFT JOIN public.live_rings_raw l ON m.machine_name = l.machine_name
            LIMIT 10
        """
        return await self.fetch_all(query)
