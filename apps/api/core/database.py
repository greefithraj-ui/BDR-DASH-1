import asyncpg
from typing import Optional
from apps.api.core.config import settings

class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                min_size=1,
                max_size=10
            )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            self.pool = None

    def get_pool(self) -> asyncpg.Pool:
        if not self.pool:
            raise Exception("Database pool not initialized.")
        return self.pool

db = Database()
