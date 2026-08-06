from apps.api.repositories.machines import MachineRepository

class MachinesService:
    def __init__(self, repository: MachineRepository):
        self.repository = repository
        
    async def get_data(self) -> list:
        return await self.repository.get_data()
