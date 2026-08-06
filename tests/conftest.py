"""Shared pytest fixtures for the BIC test suite.

Sprint 2 adds PostgreSQL integration fixtures. They use a disposable scratch
schema (`bic_scratch_<uuid>`), never the real `bic` or `public` schemas, and
skip cleanly when psycopg2/PG is unavailable (e.g. CI).
"""

import threading
import uuid

import pytest

try:
    import psycopg2

    HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None
    HAS_PSYCOPG2 = False

from bic.config import BicConfig, load_config
from bic.db import BicDatabase, DbConfig
from bic.schema import validate_schema_name


@pytest.fixture
def bic_config() -> BicConfig:
    """Spec-fixed BIC configuration from load_config()."""
    return load_config()


@pytest.fixture
def zero_cadence_config() -> BicConfig:
    """Config with cadence 0 so poll-loop tests run without sleeping."""
    return BicConfig(cadence=0)


@pytest.fixture
def shutdown_event() -> threading.Event:
    """A fresh, unset shutdown event for poll-loop tests."""
    return threading.Event()


def _pg_reachable() -> bool:
    if not HAS_PSYCOPG2:
        return False
    try:
        conn = psycopg2.connect(**DbConfig().connect_kwargs())
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def pg_available() -> bool:
    """True only when a local PostgreSQL (dev default) is reachable."""
    return _pg_reachable()


def _drop_schema(schema_name: str) -> None:
    conn = psycopg2.connect(**DbConfig().connect_kwargs())
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def scratch_db(pg_available):
    """An uninitialized BicDatabase pinned to a disposable scratch schema.

    The schema is created/dropped around the test; no migration runs until the
    test calls db.initialize(). Never touches the real `bic` or `public`.
    """
    if not pg_available:
        pytest.skip("PostgreSQL not reachable; PG integration tests skipped")
    name = f"bic_scratch_{uuid.uuid4().hex[:8]}"
    validate_schema_name(name)
    db = BicDatabase(DbConfig(schema=name))
    try:
        yield db
    finally:
        db.close()
        _drop_schema(name)


@pytest.fixture
def scratch_schema(scratch_db):
    """A BicDatabase whose scratch schema is fully initialized (migration 1)."""
    applied = scratch_db.initialize(applied_by="tests.conftest")
    assert applied == [1]
    return scratch_db


LIVE_BDR_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS live_bdr_raw (
    machine_name VARCHAR(255) PRIMARY KEY,
    content TEXT NOT NULL,
    downloaded_at TIMESTAMP NOT NULL DEFAULT NOW()
)
"""

LIVE_RINGS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS live_rings_raw (
    machine_name VARCHAR(255) PRIMARY KEY,
    content TEXT NOT NULL,
    downloaded_at TIMESTAMP NOT NULL DEFAULT NOW()
)
"""


@pytest.fixture
def reader_db(pg_available):
    """A scratch schema with the two approved live-table shapes (no BIC tables).

    Returns (db, schema_name); the LiveDataReader must be pointed at
    `{schema}.live_rings_raw` / `{schema}.live_bdr_raw` so production tables are
    never touched.
    """
    if not pg_available:
        pytest.skip("PostgreSQL not reachable; reader PG tests skipped")
    schema = f"bic_scratch_{uuid.uuid4().hex[:8]}"
    validate_schema_name(schema)
    setup = psycopg2.connect(**DbConfig().connect_kwargs())
    try:
        with setup.cursor() as cur:
            cur.execute(f'CREATE SCHEMA "{schema}"')
        setup.commit()
    finally:
        setup.close()
    db = BicDatabase(DbConfig(schema=schema))
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(LIVE_BDR_TABLE_DDL)
            cur.execute(LIVE_RINGS_TABLE_DDL)
        conn.commit()
    finally:
        conn.close()
    try:
        yield db, schema
    finally:
        db.close()
        _drop_schema(schema)
