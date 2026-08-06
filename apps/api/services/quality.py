from apps.api.repositories.quality import QualityRepository

class QualityService:
    def __init__(self, repository: QualityRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
