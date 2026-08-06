from app.config.settings import Settings
from app.models.health import HealthResponse
from app.repositories.health import HealthRepository
from app.utils.time import utc_now


class HealthService:
    """Builds the health payload from database-backed data and configuration."""

    def __init__(self, repository: HealthRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def get_health(self) -> HealthResponse:
        snapshot = await self._repository.get_health_data()
        return HealthResponse(
            status=snapshot["status"],
            version=self._settings.api_version,
            service=snapshot["service"],
            timestamp=utc_now(),
            environment=self._settings.environment,
        )
