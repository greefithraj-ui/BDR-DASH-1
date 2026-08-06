from apps.api.repositories.rings import RingRepository

class RingsService:
    def __init__(self, repository: RingRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
