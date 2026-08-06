from apps.api.repositories.health import HealthRepository

class HealthService:
    def __init__(self, repository: HealthRepository):
        self.repository = repository
        
    async def check_db_health(self) -> bool:
        return await self.repository.check_health()
