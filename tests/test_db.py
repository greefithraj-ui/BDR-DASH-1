"""Unit tests for bic.db (Sprint 2, Task T1).

No database required: these pin connection config behavior, env handling,
search_path pinning, credential masking, and the no-driver guard.
"""

import pytest

from bic.db import BicDatabase, DbConfig
from bic.schema import SCHEMA_NAME


def test_default_config_matches_production_env_contract():
    cfg = DbConfig()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 5432
    assert cfg.dbname == "bdr_dashboard"
    assert cfg.user == "postgres"
    assert cfg.schema == SCHEMA_NAME
    assert cfg.min_pool == 1
    assert cfg.max_pool == 5


def test_from_env_defaults():
    cfg = DbConfig.from_env()
    assert cfg.host == "127.0.0.1"
    assert cfg.schema == SCHEMA_NAME


def test_from_env_honors_environment(monkeypatch):
    monkeypatch.setenv("PG_HOST", "db.internal")
    monkeypatch.setenv("PG_PORT", "6432")
    monkeypatch.setenv("PG_DB", "bic_db")
    monkeypatch.setenv("PG_USER", "bic_user")
    monkeypatch.setenv("PG_PASSWORD", "secret")
    cfg = DbConfig.from_env()
    assert cfg.host == "db.internal"
    assert cfg.port == 6432
    assert cfg.dbname == "bic_db"
    assert cfg.user == "bic_user"
    assert cfg.password == "secret"


def test_from_env_schema_override():
    assert DbConfig.from_env(schema="bic_scratch_test").schema == "bic_scratch_test"
    assert DbConfig.from_env().schema == SCHEMA_NAME


def test_connect_kwargs_pins_search_path_to_schema():
    cfg = DbConfig(schema="bic_scratch_test")
    kwargs = cfg.connect_kwargs()
    assert "search_path=bic_scratch_test" in kwargs["options"]
    assert "statement_timeout=15000" in kwargs["options"]
    assert kwargs["host"] == cfg.host
    assert kwargs["password"] == cfg.password
    assert "options" in kwargs


def test_connect_kwargs_uses_default_schema():
    kwargs = DbConfig().connect_kwargs()
    assert "search_path=bic" in kwargs["options"]


def test_display_masks_password():
    display = DbConfig(password="hunter2").display()
    assert display["password"] == "********"
    assert "hunter2" not in str(display)


def test_invalid_schema_rejected():
    for name in ("public", "pg_catalog", "Bad-Name", "9abc"):
        with pytest.raises(ValueError):
            DbConfig(schema=name)


def test_non_positive_timeouts_rejected():
    with pytest.raises(ValueError):
        DbConfig(connect_timeout=0)
    with pytest.raises(ValueError):
        DbConfig(statement_timeout_ms=-1)


def test_bicdatabase_requires_driver(monkeypatch):
    import bic.db as bic_db

    monkeypatch.setattr(bic_db, "HAS_PSYCOPG2", False)
    with pytest.raises(RuntimeError):
        BicDatabase(DbConfig())


def test_config_is_frozen():
    cfg = DbConfig()
    with pytest.raises(Exception):
        cfg.host = "other"  # type: ignore[misc]
