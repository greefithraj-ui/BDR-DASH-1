"""PostgreSQL integration tests: Removal Finalization Engine (Sprint 2, Task 7).

Runs against a fully initialized scratch BIC schema. Verifies the end-to-end
pipeline -- Collector State Engine + Removal Candidate Engine + Removal
Finalization Engine -- moves confirmed removals out of active_rings into
ring_history with a FINALIZED ring_events record in one transaction, enforces
both the confirmation count and the 120-second grace period against the
observation stream, preserves lifecycle integrity, stays idempotent, and never
classifies replacements or writes anything outside the approved tables.
"""

from datetime import datetime, timedelta, timezone

from bic.diff import SmartUpdateEngine
from bic.finalize import (
    COLLECTOR_VERSION,
    FINALIZATION_END_REASON,
    FINALIZATION_EVENT_TYPE,
    RemovalFinalizationEngine,
)
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
        "SELECT machine_name, slot_key, serial_number, state, "
        "removal_confirmations, removal_first_absent_at "
        "FROM active_rings ORDER BY machine_name, slot_key",
    )


def _history_rows(db):
    return _fetch_all(
        db,
        "SELECT ring_id, machine_name, slot_key, serial_number, "
        "state_history, decision_summary, first_seen_at, last_seen_at, "
        "finalized_at, end_reason, firmware_version, collector_version, "
        "archived_at FROM ring_history ORDER BY machine_name, slot_key",
    )


def _event_rows(db):
    return _fetch_all(
        db,
        "SELECT ring_id, machine_name, slot_key, event_type, occurred_at, "
        "recorded_at, payload, reason, collector_version, source "
        "FROM ring_events ORDER BY machine_name, slot_key, occurred_at",
    )


def _run_pipeline(db, sequence, confirmations=None, grace=None):
    """Apply [(diff, batch), ...] through state + removal + finalize engines."""
    state_engine = CollectorStateEngine(db)
    removal_engine = RemovalCandidateEngine(db, confirmations=confirmations)
    finalize_engine = RemovalFinalizationEngine(
        db, confirmations=confirmations, grace=grace
    )
    for diff_result, batch in sequence:
        state_engine.apply(diff_result, batch)
        removal_engine.apply(diff_result, batch)
        finalize_engine.apply(diff_result, batch)
    return finalize_engine


def _seed_pending_row(db, name="aqc-03", slot="1", serial="SN-1",
                      first_absent=SESSION, counter=3, ring_mac="AA:BB",
                      state="PENDING_REMOVAL"):
    """Insert one ring_identity + pending active_rings row directly."""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO ring_identities "
                "(serial_number, ring_mac, ring_name, product, first_seen_at, "
                "last_seen_at, created_at, updated_at) "
                "VALUES (%s, %s, %s, 'PRO', %s, %s, %s, %s) RETURNING id",
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


# ── Full pipeline lifecycle ─────────────────────────────────────────────────


def test_full_lifecycle_finalizes_into_history_with_event(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)
    fin = _batch("aqc-03", slots=(), at=a1.generated_at
                 + timedelta(seconds=121))

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
    ])
    assert _active_rows(scratch_schema)[0][3] == "PENDING_REMOVAL"

    _run_pipeline(scratch_schema, [(DIFF.diff(a3, fin), fin)])

    assert _active_rows(scratch_schema) == []
    history = _history_rows(scratch_schema)
    assert len(history) == 1
    row = history[0]
    assert row[9] == FINALIZATION_END_REASON
    assert row[10] == "1.0"
    assert row[11] == COLLECTOR_VERSION
    assert row[12] == fin.generated_at  # archived_at is deterministic
    assert row[4] == [
        {"state": "OBSERVED", "changed_at": c1.generated_at.isoformat()},
        {"state": "PENDING_REMOVAL", "changed_at": a3.generated_at.isoformat()},
    ]
    summary = row[5]
    assert summary["end_reason"] == "REMOVED"
    assert summary["grace_seconds"] == 120
    assert summary["first_absent_at"] == a1.generated_at.isoformat()
    assert summary["finalized_at"] == fin.generated_at.isoformat()

    events = _event_rows(scratch_schema)
    assert len(events) == 1
    event = events[0]
    assert event[3] == FINALIZATION_EVENT_TYPE
    assert event[4] == fin.generated_at  # occurred_at
    assert event[5] == fin.generated_at  # recorded_at
    assert event[7] == "REMOVED"
    assert event[8] == COLLECTOR_VERSION
    assert event[9] == "collector"


def test_grace_period_blocks_finalization_until_elapsed(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)
    before_grace = _batch("aqc-03", slots=(), at=a1.generated_at
                          + timedelta(seconds=119))

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
        (DIFF.diff(a3, before_grace), before_grace),
    ])

    assert len(_active_rows(scratch_schema)) == 1
    assert _count(scratch_schema, "ring_history") == 0
    assert _count(scratch_schema, "ring_events") == 0


def test_grace_elapsed_and_confirmed_in_same_observation(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + timedelta(seconds=1))
    a1 = _batch("aqc-03", slots=(), at=SESSION + timedelta(seconds=2))
    a2 = _batch("aqc-03", slots=(), at=SESSION + timedelta(seconds=61))
    a3 = _batch("aqc-03", slots=(), at=SESSION + timedelta(seconds=122))

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
    ])

    # first absent = a1 (+2s); grace 120s -> eligible at +122s == a3, the same
    # observation that reaches confirmation count 3.
    assert _active_rows(scratch_schema) == []
    assert _count(scratch_schema, "ring_history") == 1
    assert _count(scratch_schema, "ring_events") == 1


# ── Grace / confirmation gates with seeded rows ─────────────────────────────


def test_seeded_pending_finalizes_after_grace(scratch_schema):
    _seed_pending_row(scratch_schema, first_absent=SESSION)
    engine = RemovalFinalizationEngine(scratch_schema)
    at = SESSION + timedelta(seconds=121)
    fin = _batch("aqc-03", slots=(), at=at)
    result = engine.apply(DIFF.diff(_empty(), fin), fin)

    assert result.rows_finalized == 1
    assert _active_rows(scratch_schema) == []
    assert _count(scratch_schema, "ring_history") == 1
    assert _count(scratch_schema, "ring_events") == 1


def test_insufficient_confirmations_not_finalized(scratch_schema):
    _seed_pending_row(scratch_schema, first_absent=SESSION, counter=2)
    engine = RemovalFinalizationEngine(scratch_schema)
    at = SESSION + timedelta(seconds=121)
    result = engine.apply(DIFF.diff(_empty(), _batch("aqc-03", slots=(), at=at)),
                          _batch("aqc-03", slots=(), at=at))
    assert result.rows_finalized == 0
    assert len(_active_rows(scratch_schema)) == 1
    assert _count(scratch_schema, "ring_history") == 0


def test_offline_machine_suspends_finalization(scratch_schema):
    _seed_pending_row(scratch_schema, first_absent=SESSION)
    engine = RemovalFinalizationEngine(scratch_schema)
    at = SESSION + timedelta(seconds=121)
    batch = _batch("aqc-03", slots=(), at=at, fresh=False)
    result = engine.apply(DIFF.diff(_empty(), batch), batch)
    assert result.suspended_machines == 1
    assert result.rows_finalized == 0
    assert len(_active_rows(scratch_schema)) == 1
    assert _count(scratch_schema, "ring_history") == 0


def test_ring_present_in_observation_is_not_finalized(scratch_schema):
    _seed_pending_row(scratch_schema, first_absent=SESSION)
    engine = RemovalFinalizationEngine(scratch_schema)
    at = SESSION + timedelta(seconds=121)
    batch = _batch("aqc-03", (_slot(),), at=at)
    result = engine.apply(DIFF.diff(_empty(), batch), batch)
    assert result.rows_finalized == 0
    assert len(_active_rows(scratch_schema)) == 1


def test_reappearance_before_finalization_cancels_in_pipeline(scratch_schema):
    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    c2 = _batch("aqc-03", (_slot(),), at=SESSION + TICK)
    a1 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 4 * TICK)
    reappear = _batch("aqc-03", (_slot(),), at=SESSION + 5 * TICK)
    after = _batch("aqc-03", (_slot(),), at=reappear.generated_at
                   + timedelta(seconds=121))

    _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
        (DIFF.diff(c2, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
        (DIFF.diff(a3, reappear), reappear),
    ])
    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][3] == "OBSERVED"

    _run_pipeline(scratch_schema, [(DIFF.diff(reappear, after), after)])
    assert len(_active_rows(scratch_schema)) == 1  # not finalized
    assert _count(scratch_schema, "ring_history") == 0


# ── Idempotency & recovery ──────────────────────────────────────────────────


def test_reapply_of_finalizing_batch_is_idempotent(scratch_schema):
    _seed_pending_row(scratch_schema, first_absent=SESSION)
    engine = RemovalFinalizationEngine(scratch_schema)
    at = SESSION + timedelta(seconds=121)
    batch = _batch("aqc-03", slots=(), at=at)
    diff = DIFF.diff(_empty(), batch)

    first = engine.apply(diff, batch)
    assert first.rows_finalized == 1
    history_before = _history_rows(scratch_schema)
    events_before = _event_rows(scratch_schema)

    second = engine.apply(diff, batch)
    assert second.rows_finalized == 0
    assert _history_rows(scratch_schema) == history_before
    assert _event_rows(scratch_schema) == events_before


def test_recovery_restart_reapplies_without_duplication(scratch_schema):
    _seed_pending_row(scratch_schema, first_absent=SESSION)
    at = SESSION + timedelta(seconds=121)
    batch = _batch("aqc-03", slots=(), at=at)

    RemovalFinalizationEngine(scratch_schema).apply(
        DIFF.diff(_empty(), batch), batch
    )
    restarted = RemovalFinalizationEngine(scratch_schema)
    result = restarted.apply(DIFF.diff(_empty(), batch), batch)

    assert result.rows_finalized == 0
    assert _count(scratch_schema, "ring_history") == 1
    assert _count(scratch_schema, "ring_events") == 1


def test_deterministic_across_schemas(scratch_schema):
    from bic.db import BicDatabase, DbConfig
    from bic.schema import validate_schema_name
    from tests.conftest import _drop_schema

    def _fresh_schema():
        import uuid

        name = f"bic_scratch_{uuid.uuid4().hex[:8]}"
        validate_schema_name(name)
        db = BicDatabase(DbConfig(schema=name))
        db.initialize(applied_by="tests.finalize")
        return db

    c1 = _batch("aqc-03", (_slot(),), at=SESSION)
    a1 = _batch("aqc-03", slots=(), at=SESSION + TICK)
    a2 = _batch("aqc-03", slots=(), at=SESSION + 2 * TICK)
    a3 = _batch("aqc-03", slots=(), at=SESSION + 3 * TICK)
    fin = _batch("aqc-03", slots=(), at=a1.generated_at + timedelta(seconds=121))
    sequence = [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, a1), a1),
        (DIFF.diff(a1, a2), a2),
        (DIFF.diff(a2, a3), a3),
        (DIFF.diff(a3, fin), fin),
    ]

    first = _run_pipeline(scratch_schema, sequence).last_result
    first_history = _history_rows(scratch_schema)
    first_events = _event_rows(scratch_schema)

    other = _fresh_schema()
    try:
        second = _run_pipeline(other, sequence).last_result
        second_history = _history_rows(other)
        second_events = _event_rows(other)
    finally:
        other.close()
        _drop_schema(other.config.schema)

    assert first == second
    assert first.rows_finalized == 1
    assert first_history == second_history
    assert first_events == second_events


# ── Accounting & guarantees ─────────────────────────────────────────────────


def test_query_and_row_accounting(scratch_schema):
    _seed_pending_row(scratch_schema, first_absent=SESSION)
    engine = RemovalFinalizationEngine(scratch_schema)
    at = SESSION + timedelta(seconds=121)
    batch = _batch("aqc-03", slots=(), at=at)
    result = engine.apply(DIFF.diff(_empty(), batch), batch)

    assert result.query_count == 5  # lock + select + history + event + delete
    assert result.rows_read == 1
    assert result.rows_written == 3  # history + event + active delete
    assert result.history_rows == 1
    assert result.event_rows == 1
    assert result.deleted_rows == 1

    noop = engine.apply(DIFF.diff(_empty(), batch), batch)
    assert noop.query_count == 2  # lock + select only
    assert noop.rows_written == 0


def test_never_classifies_replacement(scratch_schema):
    c1 = _batch("aqc-03", (_slot(key="1", serial="SN-OLD", ring_mac="AA:01"),),
                at=SESSION)
    c2 = _batch("aqc-03", (_slot(key="1", serial="SN-NEW", ring_mac="AA:02"),),
                at=SESSION + TICK)
    engine = _run_pipeline(scratch_schema, [
        (DIFF.diff(_empty(), c1), c1),
        (DIFF.diff(c1, c2), c2),
    ])
    assert engine.last_result.rows_finalized == 0
    assert _count(scratch_schema, "ring_history") == 0
    assert _count(scratch_schema, "ring_events") == 0
    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][2] == "SN-NEW"
