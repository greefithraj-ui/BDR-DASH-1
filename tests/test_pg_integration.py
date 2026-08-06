"""PostgreSQL integration tests for bic.schema + bic.db (Sprint 2, Task T1).

All tests run against a disposable scratch schema created and dropped by the
`scratch_db`/`scratch_schema` fixtures. They never touch the real `bic` or
`public` schemas, and they skip cleanly when PostgreSQL is unreachable (CI).
"""

try:
    import psycopg2
    import psycopg2.errors
except ImportError:
    psycopg2 = None

import pytest

from bic.schema import SCHEMA_NAME, current_schema_version, verify_checksums


def _schema_tables(db, schema: str) -> set:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE'",
                (schema,),
            )
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def _insert_identity(db, serial="SER-0001") -> int:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ring_identities "
                "(serial_number, ring_mac, ring_name, product, first_seen_at, last_seen_at) "
                "VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING id",
                (serial, "AABBCCDDEEFF", "Ring 1", "PRODUCT-X"),
            )
            ring_id = cur.fetchone()[0]
        conn.commit()
        return ring_id
    finally:
        conn.close()


def _insert_active(db, ring_id: int, machine: str, slot: str, serial: str) -> None:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO active_rings "
                "(ring_id, machine_name, slot_key, serial_number, state, "
                "state_changed_at, first_seen_at, last_seen_at) "
                "VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                (ring_id, machine, slot, serial, "OBSERVED"),
            )
        conn.commit()
    finally:
        conn.close()


def test_initialize_created_expected_objects(scratch_schema):
    tables = _schema_tables(scratch_schema, scratch_schema.config.schema)
    expected = {
        "schema_version",
        "ring_identities",
        "active_rings",
        "ring_events",
        "ring_history",
        "machine_checkpoint",
    }
    assert expected <= tables
    status = scratch_schema.schema_status()
    assert status["current_version"] == status["latest_version"] == 1
    assert status["is_current"] is True
    assert status["checksums"]
    assert all(entry["ok"] for entry in status["checksums"])


def test_reinitialize_is_idempotent(scratch_schema):
    assert scratch_schema.initialize(applied_by="tests.idempotent") == []
    assert scratch_schema.schema_status()["is_current"] is True


def test_current_version_zero_and_no_checksums_before_init(scratch_db):
    conn = scratch_db.get_connection()
    try:
        assert current_schema_version(conn, scratch_db.config.schema) == 0
        assert verify_checksums(conn, scratch_db.config.schema) == []
    finally:
        conn.close()


def test_bic_and_public_schemas_untouched(scratch_db):
    before_public = _schema_tables(scratch_db, "public")
    before_bic = _schema_tables(scratch_db, SCHEMA_NAME)

    applied = scratch_db.initialize(applied_by="tests.untouched")
    assert applied == [1]

    after_public = _schema_tables(scratch_db, "public")
    after_bic = _schema_tables(scratch_db, SCHEMA_NAME)
    assert after_public == before_public
    assert after_bic == before_bic


def test_health_reports_connected(scratch_schema):
    status = scratch_schema.health()
    assert status["connected"] is True
    assert status["error"] is None
    assert status["schema"] == scratch_schema.config.schema
    assert status["schema_version"] == 1
    assert status["is_current"] is True
    assert status["latency_ms"] is not None
    assert status["config"]["schema"] == scratch_schema.config.schema


def test_ring_events_foreign_key_enforced(scratch_schema):
    conn = scratch_schema.get_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cur.execute(
                    "INSERT INTO ring_events "
                    "(ring_id, machine_name, slot_key, event_type, occurred_at, collector_version) "
                    "VALUES (%s, %s, %s, %s, NOW(), %s)",
                    (99999999, "aqc-01", "S01", "OBSERVED", "0.1.0"),
                )
        conn.rollback()
    finally:
        conn.close()


def test_active_rings_state_check_enforced(scratch_schema):
    ring_id = _insert_identity(scratch_schema)
    conn = scratch_schema.get_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO active_rings "
                    "(ring_id, machine_name, slot_key, serial_number, state, "
                    "state_changed_at, first_seen_at, last_seen_at) "
                    "VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                    (ring_id, "aqc-01", "S01", "SER-0001", "BOGUS"),
                )
        conn.rollback()
    finally:
        conn.close()


def test_ring_events_type_check_enforced(scratch_schema):
    ring_id = _insert_identity(scratch_schema)
    conn = scratch_schema.get_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO ring_events "
                    "(ring_id, machine_name, slot_key, event_type, occurred_at, collector_version) "
                    "VALUES (%s, %s, %s, %s, NOW(), %s)",
                    (ring_id, "aqc-01", "S01", "BOGUS", "0.1.0"),
                )
        conn.rollback()
    finally:
        conn.close()


def test_ring_history_end_reason_check_enforced(scratch_schema):
    ring_id = _insert_identity(scratch_schema)
    conn = scratch_schema.get_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO ring_history "
                    "(ring_id, machine_name, slot_key, serial_number, state_history, "
                    "first_seen_at, last_seen_at, finalized_at, end_reason, collector_version) "
                    "VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW(), %s, %s)",
                    (ring_id, "aqc-01", "S01", "SER-0001", "[]", "BOGUS", "0.1.0"),
                )
        conn.rollback()
    finally:
        conn.close()


def test_serial_number_unique_enforced(scratch_schema):
    _insert_identity(scratch_schema, serial="SER-UNIQUE-1")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        _insert_identity(scratch_schema, serial="SER-UNIQUE-1")


def test_machine_slot_unique_enforced(scratch_schema):
    ring_id = _insert_identity(scratch_schema, serial="SER-MSLOT-1")
    _insert_active(scratch_schema, ring_id, "aqc-02", "S02", "SER-MSLOT-1")
    other_id = _insert_identity(scratch_schema, serial="SER-MSLOT-2")
    conn = scratch_schema.get_connection()
    try:
        with conn.cursor() as cur:
            with pytest.raises(psycopg2.errors.UniqueViolation):
                cur.execute(
                    "INSERT INTO active_rings "
                    "(ring_id, machine_name, slot_key, serial_number, state, "
                    "state_changed_at, first_seen_at, last_seen_at) "
                    "VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                    (other_id, "aqc-02", "S02", "SER-MSLOT-2", "OBSERVED"),
                )
        conn.rollback()
    finally:
        conn.close()


def test_valid_writes_pass(scratch_schema):
    ring_id = _insert_identity(scratch_schema, serial="SER-VALID-1")
    conn = scratch_schema.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO active_rings "
                "(ring_id, machine_name, slot_key, serial_number, state, "
                "state_changed_at, first_seen_at, last_seen_at) "
                "VALUES (%s, %s, %s, %s, %s, NOW(), NOW(), NOW())",
                (ring_id, "aqc-01", "S01", "SER-VALID-1", "OBSERVED"),
            )
            cur.execute(
                "INSERT INTO ring_events "
                "(ring_id, machine_name, slot_key, event_type, occurred_at, payload, collector_version) "
                "VALUES (%s, %s, %s, %s, NOW(), %s, %s)",
                (ring_id, "aqc-01", "S01", "OBSERVED", '{"bdr": 88.5}', "0.1.0"),
            )
            cur.execute(
                "INSERT INTO ring_history "
                "(ring_id, machine_name, slot_key, serial_number, state_history, decision_summary, "
                "first_seen_at, last_seen_at, finalized_at, end_reason, collector_version) "
                "VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW(), %s, %s)",
                (
                    ring_id,
                    "aqc-01",
                    "S01",
                    "SER-VALID-1",
                    "[]",
                    "{}",
                    "COMPLETED",
                    "0.1.0",
                ),
            )
            cur.execute(
                "INSERT INTO machine_checkpoint (machine_name, is_offline) "
                "VALUES (%s, %s) ON CONFLICT (machine_name) DO NOTHING",
                ("aqc-01", False),
            )
        conn.commit()
    finally:
        conn.close()
