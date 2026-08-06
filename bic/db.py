"""BIC database connection management (Sprint 2 Task 1).

Connection parameters reuse the production reader's env contract
(PG_HOST/PG_PORT/PG_DB/PG_USER/PG_PASSWORD, see data/postgres_db.py) so BIC can
share the same database while owning ONLY its own schema. Every connection is
pinned to the BIC schema via search_path; BIC never queries the public schema.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import psycopg2
    import psycopg2.pool

    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    HAS_PSYCOPG2 = False

from bic.schema import (
    SCHEMA_NAME,
    apply_migrations,
    current_schema_version,
    is_current,
    latest_schema_version,
    validate_schema_name,
    verify_checksums,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DbConfig:
    """Connection configuration. Schema name must be a safe, non-reserved identifier."""

    host: str = "127.0.0.1"
    port: int = 5432
    dbname: str = "bdr_dashboard"
    user: str = "postgres"
    password: str = "postgres"
    schema: str = SCHEMA_NAME
    connect_timeout: int = 3
    min_pool: int = 1
    max_pool: int = 5
    statement_timeout_ms: int = 15000

    def __post_init__(self) -> None:
        validate_schema_name(self.schema)
        if self.connect_timeout <= 0 or self.statement_timeout_ms <= 0:
            raise ValueError("connect_timeout and statement_timeout_ms must be positive")

    @classmethod
    def from_env(cls, schema: str | None = None) -> "DbConfig":
        return cls(
            host=os.environ.get("PG_HOST", "127.0.0.1"),
            port=int(os.environ.get("PG_PORT", "5432")),
            dbname=os.environ.get("PG_DB", "bdr_dashboard"),
            user=os.environ.get("PG_USER", "postgres"),
            password=os.environ.get("PG_PASSWORD", "postgres"),
            schema=schema or os.environ.get("BIC_SCHEMA", SCHEMA_NAME),
        )

    def connect_kwargs(self) -> dict:
        """psycopg2.connect kwargs. search_path and statement_timeout are pinned
        at connection startup, so every pooled connection is correctly scoped."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
            "connect_timeout": self.connect_timeout,
            "options": f"-c statement_timeout={self.statement_timeout_ms} "
            f"-c search_path={self.schema}",
            "keepalives": 1,
            "keepalives_idle": 5,
            "keepalives_interval": 2,
            "keepalives_count": 2,
        }

    def display(self) -> dict:
        """Connection info with the password masked, safe to log."""
        return {
            k: (v if k != "password" else "********")
            for k, v in {
                "host": self.host,
                "port": self.port,
                "dbname": self.dbname,
                "user": self.user,
                "password": self.password,
                "schema": self.schema,
                "connect_timeout": self.connect_timeout,
            }.items()
        }


class BicDatabase:
    """Owns the BIC connection pool, schema initialization, and health checks."""

    def __init__(self, config: DbConfig) -> None:
        if not HAS_PSYCOPG2:
            raise RuntimeError(
                "psycopg2-binary is not installed; BIC database module requires it"
            )
        self.config = config
        self._pool = None
        self._pool_lock = threading.Lock()

    def _get_pool(self) -> psycopg2.pool.SimpleConnectionPool:
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    self._pool = psycopg2.pool.SimpleConnectionPool(
                        self.config.min_pool,
                        self.config.max_pool,
                        **self.config.connect_kwargs(),
                    )
        return self._pool

    def get_connection(self) -> "_PooledConnection":
        """Return a connection pinned to the BIC schema; close() returns it to the pool."""
        pool = self._get_pool()
        try:
            conn = pool.getconn()
            return _PooledConnection(conn, self, pooled=True)
        except psycopg2.pool.PoolError:
            return _PooledConnection(
                psycopg2.connect(**self.config.connect_kwargs()), self, pooled=False
            )

    def initialize(self, applied_by: str = "bic.init") -> list[int]:
        """Ensure the schema/ledger exist and apply pending migrations."""
        conn = self.get_connection()
        try:
            return apply_migrations(conn, self.config.schema, applied_by)
        finally:
            conn.close()

    def schema_status(self) -> dict:
        """Current/latest versions, currency flag, and ledger checksum verification."""
        conn = self.get_connection()
        try:
            return {
                "schema": self.config.schema,
                "current_version": current_schema_version(conn, self.config.schema),
                "latest_version": latest_schema_version(),
                "is_current": is_current(conn, self.config.schema),
                "checksums": verify_checksums(conn, self.config.schema),
            }
        finally:
            conn.close()

    def health(self) -> dict:
        """Non-raising connectivity check; returns a JSON-serializable dict."""
        status = {
            "available": HAS_PSYCOPG2,
            "connected": False,
            "schema": self.config.schema,
            "schema_version": None,
            "is_current": False,
            "latency_ms": None,
            "error": None,
            "config": self.config.display(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if not HAS_PSYCOPG2:
            status["error"] = "psycopg2-binary not installed"
            return status
        started = time.monotonic()
        try:
            conn = psycopg2.connect(**self.config.connect_kwargs())
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    status["connected"] = cur.fetchone()[0] == 1
                status["schema_version"] = current_schema_version(
                    conn, self.config.schema
                )
                status["is_current"] = is_current(conn, self.config.schema)
            finally:
                conn.close()
            status["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
        except Exception as exc:  # noqa: BLE001 - health check must not raise
            status["error"] = str(exc)
        return status

    def close(self) -> None:
        """Close the pool. Safe to call multiple times."""
        if self._pool is not None:
            try:
                self._pool.closeall()
            except Exception as exc:  # noqa: BLE001
                logger.warning("pool close error: %s", exc)
            self._pool = None


class _PooledConnection:
    """Wraps a psycopg2 connection so that .close() returns it to the pool."""

    def __init__(self, conn, db: BicDatabase, pooled: bool) -> None:
        self._conn = conn
        self._db = db
        self._pooled = pooled

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self) -> None:
        if not self._pooled:
            try:
                self._conn.close()
            except Exception:  # noqa: BLE001
                pass
            return
        try:
            pool = self._db._get_pool()
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            pool.putconn(self._conn)
        except Exception:  # noqa: BLE001 - discard dead connection
            try:
                self._db._get_pool().putconn(self._conn, close=True)
            except Exception:  # noqa: BLE001
                pass
