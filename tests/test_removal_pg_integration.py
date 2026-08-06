"""PostgreSQL integration tests: Removal Candidate Engine (Sprint 2, Task 6).

Runs against a fully initialized scratch BIC schema. Verifies the end-to-end
apply path -- DiffResult + current ObservationBatch -> removal-tracking columns
of active_rings -- including the state-engine handoff, offline suspension,
reappearance cancellation, never-write guarantees, determinism, and query/row
accounting. Proves the engine never touches ring_events / ring_history /
machine_checkpoint / ring_identities and never finalizes a removal.
"""

from datetime import datetime, timedelta, timezone

from bic.diff import SmartUpdateEngine
from bic.reader import (
    MachineObservation,
    ObservationBatch,
    SlotObservation,
    SlotStatus,
    SourceState,
)
from bic.removal import RemovalCandidateEngine
from bic.state import CollectorStateEngine

SESSION = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
TICK = timedelta(seconds=30)

DIFF = SmartUpdateEngine()


def _state(present=True, fresh=True):
    return SourceState(
        present=present,
        age_seconds=5.0 if fresh else 300.0,
        fresh=fresh,
    )


def _slot(key="1", serial="SN-1", ring_mac="AA:BB"):
    return SlotObservation(
        machine_name="aqc-03",
        slot_key=key,
        status=SlotStatus.MATCH,
        serial_bdr=serial,
        serial_rings=serial,
        ring_mac=ring_mac,
        ring_name=f"Ring-{serial}",
        product="PRO",
        firmware_version="1.0",
        bdr_payload={"serial_number": serial},
        rings_payload={"serial_number": serial},
    )


def _batch(name, slots=(), at=SESSION, fresh=True):
    return ObservationBatch(
        machines=(
            MachineObservation(
                machine_name=name,
                bdr=_state(fresh=fresh),
                rings=_state(fresh=fresh),
                slots=tuple(slots),
            ),
        ),
        generated_at=at,
    )


def _empty(at=SESSION):
    return ObservationBatch(machines=(), generated_at=at)


def _fetch_all(db, sql, params=None):
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _count(db, table):
    return _fetch_all(db, f"SELECT COUNT(*) FROM {table}")[0][0]


def _active_rows(db):
    return _fetch_all(
        db,
        "SELECT machine_name, slot_key, serial_number, ring_id, state, "
        "state_changed_at, first_seen_at, last_seen_at, "
        "removal_confirmations, removal_first_absent_at, firmware_version, "
        "end_reason, finalized_at, updated_at "
        "FROM active_rings ORDER BY machine_name, slot_key",
    )


def _run_pipeline(db, sequence, confirmations=None):
    """Apply a [(diff, batch), ...] sequence through state + removal engines."""
    state_engine = CollectorStateEngine(db)
    removal_engine = RemovalCandidateEngine(db, confirmations=confirmations)
    for diff_result, batch in sequence:
        state_engine.apply(diff_result, batch)
        removal_engine.apply(diff_result, batch)
    return removal_engine


def _seed_row(db, name="aqc-03", slot="1", serial="SN-1", state="TRACKING",
              counter=0, first_absent=None, ring_mac="AA:BB"):
    """Insert one ring_identity + active_rings row directly (engine seeding)."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ring_identities "
                "(serial_number, ring_mac, ring_name, product, first_seen_at, "
                "last_seen_at, created_at, updated_at) "
                "VALUES (%s, %s, %s, 'PRO', %s, %s, %s, %s) "
                "RETURNING id",
                (serial, ring_mac, f"Ring-{serial}", SESSION, SESSION, SESSION,
                 SESSION),
            )
            ring_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO active_rings "
                "(ring_id, machine_name, slot_key, serial_number, state, "
                "state_changed_at, first_seen_at, last_seen_at, "
                "removal_confirmations, removal_first_absent_at, "
                "firmware_version, end_reason, finalized_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '1.0', "
                "NULL, NULL, %s)",
                (ring_id, name, slot, serial, state, SESSION, SESSION, SESSION,
                 counter, first_absent, SESSION),
            )
        conn.commit()
    finally:
        conn.close()
    return ring_id


# ── Confirmation progression through the pipeline ──────────────────────────


def test_three_absences_promote_to_pending_removal(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)

    engine = _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
    ])

    assert engine.last_result.has_errors is False
    row = _active_rows(scratch_schema)[0]
    assert row[4] == "PENDING_REMOVAL"
    assert row[8] == 3
    assert row[9] == SESSION + 2 * TICK  # first absent observation
    assert row[5] == SESSION + 4 * TICK  # state_changed at promotion
    assert row[11] is None
    assert row[12] is None
    assert _count(scratch_schema, "ring_identities") == 1


def test_fourth_absence_after_pending_is_idempotent(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)
    a4 = _batch("aqc-03", slots=(), at=SESSION + 5 * TICK)

    engine = _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
    ])
    before = _active_rows(scratch_schema)

    result = engine.apply(DIFF.diff(a3, a4), a4)
    assert result.rows_updated == 0
    assert result.rows_written == 0
    assert _active_rows(scratch_schema) == before


def test_reappearance_cancels_candidate(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    c3 = _batch("aqc-03", (_slot(),), at=SESSION + 4 * TICK)

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
    ])
    assert _active_rows(scratch_schema)[0][8] == 2

    engine = _run_pipeline(scratch_schema, [
        (DIFF.diff(a2, c3), c3),
    ])
    row = _active_rows(scratch_schema)[0]
    assert row[8] == 0
    assert row[9] is None
    assert row[4] == "OBSERVED"  # state engine resets on NEW_RING
    assert engine.last_result.cancellations == 0  # state engine already cleared


def test_reappearance_after_pending_restores_observed(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)
    c4 = _batch("aqc-03", (_slot(),), at=SESSION + 5 * TICK)

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
    ])
    assert _active_rows(scratch_schema)[0][4] == "PENDING_REMOVAL"

    _run_pipeline(scratch_schema, [(DIFF.diff(a3, c4), c4)])
    row = _active_rows(scratch_schema)[0]
    assert row[4] == "OBSERVED"
    assert row[8] == 0
    assert row[9] is None


# ── Offline / stale suspension ──────────────────────────────────────────────


def test_stale_machine_suspends_confirmation(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    stale = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK, fresh=False)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)

    engine = _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
    ])
    assert _active_rows(scratch_schema)[0][8] == 1

    result = engine.apply(DIFF.diff(a1, stale), stale)
    assert result.suspended_machines == 1
    assert result.rows_updated == 0
    assert _active_rows(scratch_schema)[0][8] == 1  # frozen, not reset

    engine.apply(DIFF.diff(stale, a3), a3)
    assert _active_rows(scratch_schema)[0][8] == 2  # resumed, still consecutive


def test_machine_absent_from_batch_freezes_counters(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    other = _batch("aqc-04", (_slot(key="1", serial="SN-2"),),
                   at=SESSION + 3 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
    ])
    assert _active_rows(scratch_schema)[0][8] == 1

    _run_pipeline(scratch_schema, [(DIFF.diff(a1, other), other)])
    assert _active_rows(scratch_schema)[0][8] == 1  # aqc-03 not iterated

    _run_pipeline(scratch_schema, [(DIFF.diff(other, a2), a2)])
    assert _active_rows(scratch_schema)[0][8] == 2


# ── Standalone engine (seeded rows) ─────────────────────────────────────────


def test_removal_engine_alone_confirms_seeded_candidate(scratch_schema):
    _seed_row(scratch_schema, counter=2, first_absent=SESSION + TICK)
    engine = RemovalCandidateEngine(scratch_schema)
    absent = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    result = engine.apply(DIFF.diff(_empty(), absent), absent)

    assert result.rows_updated == 1
    row = _active_rows(scratch_schema)[0]
    assert row[4] == "PENDING_REMOVAL"
    assert row[8] == 3


def test_custom_confirmation_threshold(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
    ], confirmations=2)
    assert _active_rows(scratch_schema)[0][8] == 1

    _run_pipeline(scratch_schema, [
        (DIFF.diff(a1, a2), a2),
    ], confirmations=2)
    assert _active_rows(scratch_schema)[0][4] == "PENDING_REMOVAL"
    assert _active_rows(scratch_schema)[0][8] == 2


# ── Never-write guarantees ──────────────────────────────────────────────────


def test_never_writes_other_tables(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
    ])
    assert _active_rows(scratch_schema)[0][4] == "PENDING_REMOVAL"
    assert _count(scratch_schema, "ring_events") == 0
    assert _count(scratch_schema, "ring_history") == 0
    assert _count(scratch_schema, "machine_checkpoint") == 0
    assert _count(scratch_schema, "ring_identities") == 1  # never added by removal


def test_never_finalizes_or_classifies_replacement(scratch_schema):
    c1 = _batch("aqc-03", (_slot(key="1", serial="SN-OLD", ring_mac="AA:01"),),
                at=SESSION)
    c2 = _batch("aqc-03", (_slot(key="1", serial="SN-NEW", ring_mac="AA:02"),),
                at=SESSION + TICK)

    engine = _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
    ])
    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][2] == "SN-NEW"  # immediate replacement is not a candidate
    assert rows[0][8] == 0
    assert rows[0][4] != "FINALIZED"
    assert rows[0][11] is None
    assert rows[0][12] is None
    assert engine.last_result.rows_updated == 0


# ── Determinism & accounting ────────────────────────────────────────────────


def test_deterministic_apply_across_schemas(scratch_schema):
    from bic.db import BicDatabase, DbConfig
    from bic.schema import validate_schema_name
    from tests.conftest import _drop_schema

    def _fresh_schema():
        import uuid

        name = f"bic_scratch_{uuid.uuid4().hex[:8]}"
        validate_schema_name(name)
        db = BicDatabase(DbConfig(schema=name))
        db.initialize(applied_by="tests.removal")
        return db

    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    a1 = _batch("aqc-03", slots=(), at=SESSION + TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    sequence = [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, a1), a1),
        (DIFF.diff(a1, a2), a2),
    ]

    first = _run_pipeline(scratch_schema, sequence).last_result

    other = _fresh_schema()
    try:
        second = _run_pipeline(other, sequence).last_result
    finally:
        other.close()
        _drop_schema(other.config.schema)

    assert first == second
    assert first.session == second.session


def test_query_and_row_accounting(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    _run_pipeline(scratch_schema, [(DIFF.diff(_empty(), c1), c1)])
    removal_engine = RemovalCandidateEngine(scratch_schema)

    a1 = _batch("aqc-03", slots=(), at=SESSION + TICK)
    first = removal_engine.apply(DIFF.diff(c1, a1), a1)
    assert first.query_count == 3  # lock + select + update
    assert first.rows_read == 1
    assert first.rows_written == 1
    assert first.rows_updated == 1
    assert first.candidates_started == 1

    second = removal_engine.apply(DIFF.diff(a1, a1), a1)
    assert second.query_count == 3  # lock + select + update (counter 1 -> 2)
    assert second.rows_updated == 1
    assert second.rows_read == 1
    assert second.rows_written == 1
