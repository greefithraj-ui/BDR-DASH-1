from apps.api.repositories.metrics import MetricsRepository

class MetricsService:
    def __init__(self, repository: MetricsRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
