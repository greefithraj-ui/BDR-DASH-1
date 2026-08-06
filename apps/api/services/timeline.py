from apps.api.repositories.timeline import TimelineRepository

class TimelineService:
    def __init__(self, repository: TimelineRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
