"""PostgreSQL integration tests for the Live Data Reader (Sprint 2, Task 2).

Runs against a scratch schema holding the two approved live-table shapes; the
real `public.live_*` tables are never touched. Verifies the join model,
freshness, cross-source mismatch detection, and that the reader is strictly
read-only.
"""

import json

try:
    import psycopg2
except ImportError:
    psycopg2 = None

import pytest

from bic.reader import (
    SlotStatus,
    LiveDataReader,
    _reader_select_sql,
)
from tests.fixture_loader import load_fixture


def _make_reader(db, schema, threshold=None):
    return LiveDataReader(
        db,
        freshness_threshold=threshold,
        rings_table=f"{schema}.live_rings_raw",
        bdr_table=f"{schema}.live_bdr_raw",
    )


def _seed(db, table, machine, payload, age_seconds):
    _seed_raw(db, table, machine, json.dumps(payload), age_seconds)


def _seed_raw(db, table, machine, content, age_seconds):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {table} (machine_name, content, downloaded_at) "
                "VALUES (%s, %s, NOW() - (%s * INTERVAL '1 second')) "
                "ON CONFLICT (machine_name) DO UPDATE SET "
                "content = EXCLUDED.content, downloaded_at = EXCLUDED.downloaded_at",
                (machine, content, age_seconds),
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


def test_join_produces_matching_observations(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    batch = _make_reader(db, schema).read_all()
    assert len(batch) == 1
    obs = batch.by_machine["aqc-03"]
    assert obs.fresh is True
    assert obs.has_mismatch is False
    assert [s.slot_key for s in obs.slots] == ["1", "2", "3", "4"]
    assert all(s.status is SlotStatus.MATCH for s in obs.slots)
    assert obs.slot_map["1"].serial_number == "RP-CH3-P18-WD-PG07-0005555"


def test_read_machine_none_when_absent(reader_db):
    db, schema = reader_db
    assert _make_reader(db, schema).read_machine("aqc-03") is None


def test_read_all_empty_when_no_rows(reader_db):
    db, schema = reader_db
    batch = _make_reader(db, schema).read_all()
    assert len(batch) == 0
    assert batch.by_machine == {}


def test_cross_source_mismatch_detected(reader_db):
    db, schema = reader_db
    fx = load_fixture("one_source_mismatch")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.has_mismatch is True
    assert set(obs.slot_map) == {"1", "2", "3", "5"}
    assert obs.slot_map["1"].status is SlotStatus.MATCH
    assert obs.slot_map["5"].status is SlotStatus.RINGS_ONLY


def test_serial_conflict_across_sources(reader_db):
    db, schema = reader_db
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", {"1": {"serial_number": "SERIAL-B"}}, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", {"slots": {"1": {"serial_number": "SERIAL-A"}}}, 5)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.slot_map["1"].status is SlotStatus.MISMATCH


def test_stale_sources_report_not_fresh(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_offline")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 3600)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 3600)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.fresh is False
    assert obs.bdr.fresh is False
    assert obs.rings.fresh is False
    assert len(obs.slots) == 2
    assert obs.has_mismatch is False


def test_machine_fresh_when_single_source_fresh(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 3600)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.fresh is True
    assert obs.rings.fresh is True
    assert obs.bdr.fresh is False


def test_bdr_only_source_observation(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.bdr.present is True
    assert obs.rings.present is False
    assert obs.has_mismatch is True
    assert all(s.status is SlotStatus.BDR_ONLY for s in obs.slots)


def test_rings_only_source_observation(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.rings.present is True
    assert obs.bdr.present is False
    assert obs.has_mismatch is True
    assert all(s.status is SlotStatus.RINGS_ONLY for s in obs.slots)


def test_empty_source_payload_produces_empty_observation(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_empty_bdr_absent")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.rings.present is True
    assert obs.bdr.present is False
    assert obs.fresh is True
    assert obs.slots == ()


def test_invalid_json_content_flagged(reader_db):
    db, schema = reader_db
    _seed_raw(db, f"{schema}.live_bdr_raw", "aqc-03", "{not-json", 5)

    obs = _make_reader(db, schema).read_machine("aqc-03")
    assert obs.bdr.present is True
    assert obs.bdr.fresh is True
    assert obs.bdr.parse_error is not None
    assert obs.rings.present is False
    assert obs.slots == ()


def test_batch_helpers(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    for machine in ("aqc-03", "aqc-47"):
        _seed(db, f"{schema}.live_rings_raw", machine, fx.rings, 5)
        _seed(db, f"{schema}.live_bdr_raw", machine, fx.bdr, 5)

    batch = _make_reader(db, schema).read_all()
    assert len(batch) == 2
    assert set(batch.by_machine) == {"aqc-03", "aqc-47"}
    assert [m.machine_name for m in batch] == ["aqc-03", "aqc-47"]


def test_reader_never_modifies_tables_or_creates_bic_objects(reader_db):
    db, schema = reader_db
    fx = load_fixture("machine_active")
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", fx.rings, 5)
    _seed(db, f"{schema}.live_bdr_raw", "aqc-03", fx.bdr, 5)

    before = _table_contents(db, schema)
    reader = _make_reader(db, schema)
    assert len(reader.read_all()) == 1
    assert reader.read_machine("aqc-03") is not None
    assert reader.read_machine("missing") is None
    after = _table_contents(db, schema)
    assert after == before
    assert _tables_in(db, schema) == ["live_bdr_raw", "live_rings_raw"]


def test_reader_queries_run_in_read_only_transaction(reader_db):
    db, schema = reader_db
    _seed(db, f"{schema}.live_rings_raw", "aqc-03", {"1": {"serial_number": "X"}}, 5)

    conn = psycopg2.connect(**db.config.connect_kwargs())
    try:
        conn.set_session(readonly=True)
        with conn.cursor() as cur:
            cur.execute(_reader_select_sql(f"{schema}.live_rings_raw"))
            assert len(cur.fetchall()) == 1
            cur.execute(_reader_select_sql(f"{schema}.live_bdr_raw", "aqc-03"), ("aqc-03",))
            assert cur.fetchall() == []
    finally:
        conn.close()
