"""PostgreSQL integration tests: Live Data Reader -> Validation Engine.

Runs against a scratch schema holding the approved live-table shapes; the real
`public.live_*` tables are never touched. Verifies the end-to-end pipeline and
that the engine never writes to PostgreSQL or creates collector state.
"""

import json

import pytest

from bic.reader import LiveDataReader, SlotStatus
from bic.validation import (
    Severity,
    ValidationCode,
    ValidationEngine,
)
from tests.fixture_loader import load_fixture


def _make_reader(db, schema):
    return LiveDataReader(
        db,
        rings_table=f"{schema}.live_rings_raw",
        bdr_table=f"{schema}.live_bdr_raw",
    )


def _seed(db, table, machine, payload, age_seconds):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {table} (machine_name, content, downloaded_at) "
                "VALUES (%s, %s, NOW() - (%s * INTERVAL '1 second')) "
                "ON CONFLICT (machine_name) DO UPDATE SET "
                "content = EXCLUDED.content, downloaded_at = EXCLUDED.downloaded_at",
                (machine, json.dumps(payload), age_seconds),
            )
        conn.commit()
    finally:
        conn.close()


def _table_contents(db, schema):
    result = {}
    for table in ("live_bdr_raw", "live_rings_raw"):
        conn = db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT machine_name, content, downloaded_at "
                    f"FROM {schema}.{table} ORDER BY machine_name"
                )
                result[table] = cur.fetchall()
        finally:
            conn.close()
    return result


def _tables_in(db, schema):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s AND table_type = 'BASE TABLE' "
                "ORDER BY table_name",
                (schema,),
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def test_valid_machine_active_pipeline(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    batch = _make_reader(db, schema).read_all()
    result = ValidationEngine().validate(batch)

    assert result.valid is True
    assert result.machine_count == 1
    assert result.slot_count == 4
    assert result.error_count == 0
    assert result.warning_count == 0
    machine = result.by_machine["aqc-03"]
    assert machine.valid is True
    assert all(slot.valid for slot in machine.slots)


def test_one_source_mismatch_flagged_end_to_end(reader_db):
    db, schema = reader_db
    fx = load_fixture("one_source_mismatch")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    batch = _make_reader(db, schema).read_all()
    result = ValidationEngine().validate(batch)

    assert result.valid is True
    machine = result.by_machine["aqc-03"]
    slot5 = machine.slot_map["5"]
    assert any(
        issue.code is ValidationCode.SLOT_ONE_SOURCE_ONLY for issue in slot5.issues
    )
    assert slot5.valid is True


def test_stale_machine_invalid_end_to_end(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_offline")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 3600)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 3600)

    batch = _make_reader(db, schema).read_all()
    result = ValidationEngine().validate(batch)

    assert result.valid is False
    machine = result.by_machine["aqc-03"]
    assert machine.valid is False
    assert any(issue.code is ValidationCode.MACHINE_STALE for issue in machine.issues)


def test_invalid_state_combination_end_to_end(reader_db):
    db, schema = reader_db
    rings = {
        "1": {
            "serial_number": "SN-1",
            "product": "PRO",
            "ring_mac": "AA:BB",
            "ring_name": "RingA",
            "state": "PASSED",
            "step_statuses": {"BDR_TEST": "IN_PROGRESS"},
        }
    }
    bdr = {"slots": {"1": {"serial_number": "SN-1", "ring_mac": "AA:BB", "ring_name": "RingA", "product": "PRO", "state": "PASSED"}}}
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", bdr, 5)

    batch = _make_reader(db, schema).read_all()
    result = ValidationEngine().validate(batch)

    assert result.valid is False
    slot = result.by_machine["aqc-03"].slot_map["1"]
    assert slot.valid is False
    assert any(
        issue.code is ValidationCode.INVALID_STATE_COMBINATION for issue in slot.issues
    )


def test_parse_error_invalid_end_to_end(reader_db):
    db, schema = reader_db
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", "{not-json", 5)

    batch = _make_reader(db, schema).read_all()
    result = ValidationEngine().validate(batch)

    assert result.valid is False
    machine = result.by_machine["aqc-03"]
    assert any(issue.code is ValidationCode.SOURCE_PARSE_ERROR for issue in machine.issues)


def test_bdr_only_machine_warns_but_stays_valid(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    batch = _make_reader(db, schema).read_all()
    result = ValidationEngine().validate(batch)

    assert result.valid is True
    machine = result.by_machine["aqc-03"]
    assert machine.valid is True
    codes = {issue.code for machine_r in result.machines for issue in machine_r.issues}
    assert ValidationCode.SOURCE_MISSING in codes
    slot_issues = [
        issue
        for machine_r in result.machines
        for slot in machine_r.slots
        for issue in slot.issues
    ]
    assert all(
        issue.code is ValidationCode.SLOT_ONE_SOURCE_ONLY for issue in slot_issues
    )
    assert all(issue.severity is Severity.WARNING for issue in slot_issues)


def test_engine_never_writes_to_postgres(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    before = _table_contents(db, schema)
    batch = _make_reader(db, schema).read_all()
    ValidationEngine().validate(batch)
    after = _table_contents(db, schema)

    assert after == before
    assert _tables_in(db, schema) == ["live_bdr_raw", "live_rings_raw"]


def test_slot_status_surfaces_from_reader(reader_db):
    db, schema = reader_db
    fx = load_fixture("one_source_mismatch")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    batch = _make_reader(db, schema).read_all()
    obs = batch.by_machine["aqc-03"]
    assert obs.slot_map["5"].status is SlotStatus.RINGS_ONLY
    assert obs.slot_map["1"].status is SlotStatus.MATCH
