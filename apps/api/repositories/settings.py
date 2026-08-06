from apps.api.repositories.base import BaseRepository

class SettingsRepository(BaseRepository):
    async def get_data(self) -> list:
        
        # TODO: Placeholder repositories remain intentional.
        return await self.fetch_all("SELECT 1 as placeholder")
