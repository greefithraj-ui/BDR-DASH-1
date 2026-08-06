import asyncpg
from typing import List, Dict, Any, Optional

class BaseRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        records = await self.conn.fetch(query, *args)
        return [dict(record) for record in records]

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        record = await self.conn.fetchrow(query, *args)
        return dict(record) if record else None
