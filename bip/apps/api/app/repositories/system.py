import platform
import sys


class SystemRepository:
    """Runtime system information (no database source required)."""

    def __init__(self, api_version: str) -> None:
        self._api_version = api_version

    def list_all(self) -> list[dict[str, str]]:
        return [
            {
                "id": "SYS-1",
                "hostname": platform.node(),
                "python_version": sys.version.split()[0],
                "framework": "FastAPI",
                "version": self._api_version,
            }
        ]
