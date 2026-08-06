from app.config.settings import Settings


class SettingsRepository:
    """Settings sourced from the live application configuration."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def list_all(self) -> list[dict[str, str]]:
        settings = self._settings
        entries = [
            ("SET-1", "app_name", "Application Name", settings.app_name),
            ("SET-2", "api_version", "API Version", settings.api_version),
            ("SET-3", "environment", "Environment", settings.environment),
            ("SET-4", "api_prefix", "API Prefix", settings.api_prefix),
            (
                "SET-5",
                "database",
                "Database",
                f"{settings.db_host}:{settings.db_port}/{settings.db_name}",
            ),
            (
                "SET-6",
                "freshness_window",
                "Freshness Window",
                f"{settings.freshness_window_seconds}s",
            ),
        ]
        return [
            {"id": entry_id, "key": key, "label": label, "value": value}
            for entry_id, key, label, value in entries
        ]
