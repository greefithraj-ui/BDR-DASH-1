from apps.api.repositories.base import BaseRepository

class AdministrationRepository(BaseRepository):
    async def get_data(self) -> list:
        # Placeholders
        
        # TODO: Placeholder repositories remain intentional.
        return await self.fetch_all("SELECT 1 as placeholder")
