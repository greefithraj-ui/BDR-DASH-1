from apps.api.repositories.analytics import AnalyticsRepository

class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
