"""Unit tests for bic.schema (Sprint 2, Task T1).

These tests never touch a database: they pin the frozen review decisions to the
DDL module so that any future drift fails in CI.
"""

import re

import pytest

from bic.schema import (
    END_REASONS,
    EVENT_TYPES,
    LIFECYCLE_STATES,
    MIGRATIONS,
    SCHEMA_VERSION_DDL,
    Migration,
    latest_schema_version,
    migration_checksum,
    validate_schema_name,
)


def _table_block(table_name: str, sql: str) -> str:
    match = re.search(
        rf"CREATE TABLE {table_name} \((.*?)\);",
        sql,
        flags=re.DOTALL,
    )
    assert match, f"CREATE TABLE {table_name} not found"
    return match.group(1)


def test_lifecycle_states_frozen():
    assert LIFECYCLE_STATES == (
        "OBSERVED",
        "TRACKING",
        "PENDING_REMOVAL",
        "FINALIZED",
    )


def test_end_reasons_frozen():
    assert END_REASONS == (
        "COMPLETED",
        "COMPLETED_FAILED",
        "REPLACED",
        "REMOVED",
        "TIMEOUT",
        "DECOMMISSIONED",
        "MANUAL_RESET",
        "UNKNOWN",
    )


def test_event_types_frozen():
    assert EVENT_TYPES == (
        "OBSERVED",
        "STATE_CHANGED",
        "ABSENT",
        "REAPPEARED",
        "CONFLICT",
        "REPLACED",
        "REMOVAL_PENDING",
        "FINALIZED",
        "OFFLINE",
        "MANUAL_RESET",
    )


def test_migrations_are_forward_only_and_ordered():
    assert isinstance(MIGRATIONS, tuple)
    assert MIGRATIONS
    versions = [m.version for m in MIGRATIONS]
    assert versions == sorted(set(versions))
    assert versions[0] == 1
    for migration in MIGRATIONS:
        assert migration.description.strip()
        assert migration.sql.strip()


def test_latest_schema_version():
    assert latest_schema_version() == max(m.version for m in MIGRATIONS)


def test_migration_checksum_is_deterministic():
    sql = "SELECT 1;\n"
    assert migration_checksum(sql) == migration_checksum(sql)
    assert migration_checksum(sql) != migration_checksum("SELECT 2;\n")


def test_migration_checksum_property():
    migration = MIGRATIONS[0]
    assert migration.checksum == migration_checksum(migration.sql)


def test_migration_1_defines_all_frozen_tables():
    sql = MIGRATIONS[0].sql
    for table in (
        "ring_identities",
        "active_rings",
        "ring_events",
        "ring_history",
        "machine_checkpoint",
    ):
        assert f"CREATE TABLE {table}" in sql


def test_ledger_ddl_is_present():
    assert "CREATE TABLE IF NOT EXISTS schema_version" in SCHEMA_VERSION_DDL
    assert "checksum" in SCHEMA_VERSION_DDL
    assert "applied_by" in SCHEMA_VERSION_DDL


def test_ddl_never_qualifies_other_schemas():
    sql = MIGRATIONS[0].sql + SCHEMA_VERSION_DDL
    assert "public." not in sql
    assert "pg_catalog." not in sql
    assert "information_schema." not in sql


def test_ddl_uses_varchar_checks_not_pg_enum():
    sql = MIGRATIONS[0].sql
    assert "CREATE TYPE" not in sql
    assert "AS ENUM" not in sql


def test_ring_identities_columns():
    block = _table_block("ring_identities", MIGRATIONS[0].sql)
    for column in (
        "id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
        "serial_number VARCHAR(255) NOT NULL",
        "ring_mac VARCHAR(32) NOT NULL",
        "ring_name VARCHAR(128) NOT NULL",
        "product VARCHAR(32) NOT NULL",
        "first_seen_at TIMESTAMPTZ NOT NULL",
        "last_seen_at TIMESTAMPTZ NOT NULL",
    ):
        assert column in block
    assert "firmware_version" not in block


def test_ring_identities_serial_number_unique():
    block = _table_block("ring_identities", MIGRATIONS[0].sql)
    assert "CONSTRAINT uq_ring_identities_serial_number UNIQUE (serial_number)" in block


def test_active_rings_columns_and_constraints():
    block = _table_block("active_rings", MIGRATIONS[0].sql)
    for column in (
        "ring_id BIGINT NOT NULL",
        "machine_name VARCHAR(255) NOT NULL",
        "slot_key VARCHAR(16) NOT NULL",
        "serial_number VARCHAR(255) NOT NULL",
        "state VARCHAR(32) NOT NULL DEFAULT 'OBSERVED'",
        "state_changed_at TIMESTAMPTZ NOT NULL",
        "first_seen_at TIMESTAMPTZ NOT NULL",
        "last_seen_at TIMESTAMPTZ NOT NULL",
        "removal_confirmations INTEGER NOT NULL DEFAULT 0",
        "firmware_version VARCHAR(100) NULL",
        "end_reason VARCHAR(32) NULL",
        "finalized_at TIMESTAMPTZ NULL",
    ):
        assert column in block
    assert "CONSTRAINT uq_active_rings_machine_slot UNIQUE (machine_name, slot_key)" in block
    assert "CONSTRAINT uq_active_rings_ring_id UNIQUE (ring_id)" in block
    assert "CONSTRAINT ck_active_rings_state CHECK" in block
    assert "CONSTRAINT ck_active_rings_end_reason CHECK" in block


def test_active_rings_has_no_ring_name_or_ring_mac():
    block = _table_block("active_rings", MIGRATIONS[0].sql)
    assert "ring_name" not in block
    assert "ring_mac" not in block
    assert "product" not in block


def test_ring_events_columns():
    block = _table_block("ring_events", MIGRATIONS[0].sql)
    for column in (
        "ring_id BIGINT NOT NULL",
        "machine_name VARCHAR(255) NOT NULL",
        "slot_key VARCHAR(16) NOT NULL",
        "event_type VARCHAR(32) NOT NULL",
        "occurred_at TIMESTAMPTZ NOT NULL",
        "payload JSONB NULL",
        "collector_version VARCHAR(32) NOT NULL",
        "source VARCHAR(32) NOT NULL DEFAULT 'collector'",
    ):
        assert column in block
    assert "CONSTRAINT ck_ring_events_type CHECK" in block


def test_ring_history_columns():
    block = _table_block("ring_history", MIGRATIONS[0].sql)
    for column in (
        "ring_id BIGINT NOT NULL",
        "machine_name VARCHAR(255) NOT NULL",
        "slot_key VARCHAR(16) NOT NULL",
        "serial_number VARCHAR(255) NOT NULL",
        "state_history JSONB NOT NULL",
        "decision_summary JSONB NULL",
        "finalized_at TIMESTAMPTZ NOT NULL",
        "end_reason VARCHAR(32) NOT NULL",
        "collector_version VARCHAR(32) NOT NULL",
    ):
        assert column in block
    assert "CONSTRAINT ck_ring_history_end_reason CHECK" in block


def test_ring_history_has_no_ring_name_or_ring_mac():
    block = _table_block("ring_history", MIGRATIONS[0].sql)
    assert "ring_name" not in block
    assert "ring_mac" not in block
    assert "product" not in block


def test_machine_checkpoint_columns():
    block = _table_block("machine_checkpoint", MIGRATIONS[0].sql)
    assert "machine_name VARCHAR(255) PRIMARY KEY" in block
    for column in (
        "last_rings_seen_at TIMESTAMPTZ NULL",
        "last_bdr_seen_at TIMESTAMPTZ NULL",
        "last_processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        "is_offline BOOLEAN NOT NULL DEFAULT FALSE",
        "last_offline_at TIMESTAMPTZ NULL",
        "payload_checksum VARCHAR(128) NULL",
    ):
        assert column in block


def test_ring_id_is_the_only_foreign_key():
    sql = MIGRATIONS[0].sql
    fks = re.findall(r"CONSTRAINT fk_\w+ FOREIGN KEY", sql)
    assert len(fks) == 3
    assert "FOREIGN KEY (serial_number)" not in sql
    assert sql.count("REFERENCES ring_identities (id)") == 3


def test_frozen_enum_values_appear_in_checks():
    sql = MIGRATIONS[0].sql
    for value in EVENT_TYPES:
        assert f"'{value}'" in sql
    for value in LIFECYCLE_STATES:
        assert f"'{value}'" in sql
    for value in END_REASONS:
        assert f"'{value}'" in sql


def test_validate_schema_name_accepts_valid_names():
    for name in ("bic", "bic_scratch_a1b2c3", "schema2"):
        assert validate_schema_name(name) == name


def test_validate_schema_name_rejects_reserved_and_invalid():
    for name in (
        "public",
        "pg_catalog",
        "information_schema",
        "Bad-Name",
        "Has Space",
        "9schema",
        "MixedCase",
        "",
    ):
        with pytest.raises(ValueError):
            validate_schema_name(name)


def test_migration_is_dataclass():
    migration = Migration(version=2, description="next", sql="SELECT 1;")
    assert migration.version == 2
    assert migration.checksum == migration_checksum("SELECT 1;")
