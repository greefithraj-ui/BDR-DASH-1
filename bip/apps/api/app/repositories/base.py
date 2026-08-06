from typing import Any, Generic, Protocol, TypeVar

import asyncpg

TEntity = TypeVar("TEntity")

# Shared read-only SQL fragment identifying occupied slots in the live ring
# payloads. Ring payloads are flat slot maps whose values carry a serial number;
# empty/placeholder serials are treated as unoccupied slots.
OCCUPIED_SERIAL_CONDITION = (
    "s.payload->>'serial_number' IS NOT NULL"
    " AND s.payload->>'serial_number' <> ''"
    " AND s.payload->>'serial_number' NOT IN ('--', 'N/A')"
)


class ReadOnlyRepository(Protocol[TEntity]):
    """Read-only repository contract for data sources."""

    async def get_by_id(self, entity_id: str) -> TEntity | None:
        """Return one entity by identifier."""


class BaseSQLRepository:
    """Base for every repository backed by the read-only asyncpg pool.

    Repositories contain SQL only: they fetch raw rows and never apply business
    rules. All values are passed as query parameters; identifiers and sort
    columns are resolved from fixed whitelists defined by each repository.
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn

    async def fetch_all(self, query: str, *args: Any) -> list[dict[str, Any]]:
        rows = await self.conn.fetch(query, *args)
        return [dict(row) for row in rows]

    async def fetch_one(self, query: str, *args: Any) -> dict[str, Any] | None:
        row = await self.conn.fetchrow(query, *args)
        return dict(row) if row is not None else None

    async def fetch_val(self, query: str, *args: Any) -> Any:
        return await self.conn.fetchval(query, *args)


class InMemoryListRepository(Generic[TEntity]):
    """Deterministic in-memory read-only repository (placeholder data source).

    Used only by the prediction domain, which has no database table. Mutation
    paths remain unsupported.
    """

    def __init__(self, records: tuple[TEntity, ...]) -> None:
        self._records = records

    async def list_all(self) -> list[TEntity]:
        return list(self._records)

    async def get_by_id(self, entity_id: str) -> TEntity | None:
        for record in self._records:
            if getattr(record, "id", None) == entity_id:
                return record
        return None

    def write(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError("Repository writes are not supported.")
