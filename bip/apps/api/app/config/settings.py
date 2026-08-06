import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    """Nearest ancestor of the CWD that holds an ``apps`` directory.

    This is the bip monorepo root (``D:\\BDR\\bip``). The search never
    escapes it, so the API only ever reads the project's own env files.
    """
    current = Path.cwd()
    while True:
        if (current / "apps").is_dir():
            return current
        if current.parent == current:
            return Path.cwd()
        current = current.parent


def _find_env_file(name: str, root: Path) -> str:
    """Locate an env file by walking up from the CWD, stopping at ``root``."""
    current = Path.cwd()
    while True:
        candidate = current / name
        if candidate.is_file():
            return str(candidate)
        if current == root or current.parent == current:
            break
        current = current.parent
    return name


def _default_env_file() -> str:
    """Pick the env file that actually exists.

    An explicit ``.env`` wins; otherwise the file matching the process
    ``BIP_ENVIRONMENT`` value is used (``.env.development`` /
    ``.env.production``). Falls back to the file name so pydantic-settings
    reports it cleanly when nothing exists.
    """
    root = _project_root()
    environment = os.environ.get("BIP_ENVIRONMENT", "development")
    for name in (".env", f".env.{environment}"):
        found = _find_env_file(name, root)
        if found != name:
            return found
    return str(root / f".env.{environment}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BIP_", env_file=_default_env_file(), extra="ignore")

    app_name: str = "Battery Intelligence Platform API"
    api_version: str = "0.3.0"
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3100,http://127.0.0.1:3100"

    # Read-only database configuration (bip_reader role; the API never writes).
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "bdr_dashboard"
    db_user: str = "bip_reader"
    db_password: str = "reader_pass"
    db_pool_min: int = 1
    db_pool_max: int = 10
    db_connect_timeout: int = 5
    db_command_timeout: int = 15

    # Live data freshness window in seconds, aligned with the BIC spec value.
    freshness_window_seconds: int = 60

    # Directory used for temporary report document storage (filesystem cache).
    # Empty means "use the platform temp directory" (no database writes).
    report_storage_dir: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
