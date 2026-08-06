from apps.api.repositories.administration import AdministrationRepository

class AdministrationService:
    def __init__(self, repository: AdministrationRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
