"""Read-only database adapter boundary backed by an asyncpg connection pool."""

from app.db.session import Database, db

__all__ = ["Database", "db"]
