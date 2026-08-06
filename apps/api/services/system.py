from apps.api.repositories.system import SystemRepository

class SystemService:
    def __init__(self, repository: SystemRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
