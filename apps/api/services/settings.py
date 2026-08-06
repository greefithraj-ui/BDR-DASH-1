from apps.api.repositories.settings import SettingsRepository

class SettingsService:
    def __init__(self, repository: SettingsRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
