from apps.api.repositories.performance import PerformanceRepository

class PerformanceService:
    def __init__(self, repository: PerformanceRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
