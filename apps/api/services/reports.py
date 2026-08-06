from apps.api.repositories.reports import ReportsRepository

class ReportsService:
    def __init__(self, repository: ReportsRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
