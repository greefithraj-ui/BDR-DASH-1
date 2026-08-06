import logging
from typing import Optional

import asyncpg

from app.config.settings import Settings, get_settings

logger = logging.getLogger("bip.db")


class Database:
    """Owns the read-only asyncpg connection pool.

    The pool is opened on application startup and closed on shutdown. Every
    query runs through the ``bip_reader`` role, which has SELECT access only,
    so the API remains 100% read-only.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._pool: Optional[asyncpg.Pool] = None

    @property
    def is_connected(self) -> bool:
        return self._pool is not None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        self._pool = await asyncpg.create_pool(
            host=self._settings.db_host,
            port=self._settings.db_port,
            user=self._settings.db_user,
            password=self._settings.db_password,
            database=self._settings.db_name,
            min_size=self._settings.db_pool_min,
            max_size=self._settings.db_pool_max,
            timeout=self._settings.db_connect_timeout,
            command_timeout=self._settings.db_command_timeout,
            server_settings={"application_name": "bip-api"},
        )
        logger.info(
            "Database pool connected to %s:%s/%s",
            self._settings.db_host,
            self._settings.db_port,
            self._settings.db_name,
        )

    async def disconnect(self) -> None:
        if self._pool is None:
            return
        await self._pool.close()
        self._pool = None
        logger.info("Database pool disconnected")

    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized")
        return self._pool

    async def ping(self) -> bool:
        """Non-raising connectivity check used by the health endpoint."""
        try:
            pool = self.pool()
            async with pool.acquire() as conn:
                return await conn.fetchval("SELECT 1") == 1
        except Exception:  # noqa: BLE001 - health check must not raise
            return False


db = Database(get_settings())
