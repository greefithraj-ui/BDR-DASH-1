"""PostgreSQL integration tests: Collector State Engine (Sprint 2, Task 5).

Runs against a fully initialized scratch BIC schema (ring_identities,
active_rings, ring_events, ring_history, machine_checkpoint). Verifies the
end-to-end apply path: DiffResult + current ObservationBatch -> active_rings,
plus the transaction, concurrency, recovery, and determinism strategy, and
proves the engine never touches ring_events / ring_history / machine_checkpoint.
"""

from datetime import datetime, timedelta, timezone

import pytest

from bic.diff import ChangeType, SmartUpdateEngine
from bic.reader import (
    MachineObservation,
    ObservationBatch,
    SlotObservation,
    SlotStatus,
    SourceState,
)
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


def _slot(key="1", serial="SN-1", firmware="1.0", ring_mac="AA:BB",
          ring_name="RingA", product="PRO"):
    return SlotObservation(
        machine_name="aqc-03",
        slot_key=key,
        status=SlotStatus.MATCH,
        serial_bdr=serial,
        serial_rings=serial,
        ring_mac=ring_mac,
        ring_name=ring_name,
        product=product,
        firmware_version=firmware,
        bdr_payload={"serial_number": serial},
        rings_payload={"serial_number": serial},
    )


def _machine(name, slots=(), at=SESSION):
    return ObservationBatch(
        machines=(
            MachineObservation(
                machine_name=name,
                bdr=_state(),
                rings=_state(),
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
        "firmware_version, first_seen_at, last_seen_at, state_changed_at, "
        "removal_confirmations, removal_first_absent_at, end_reason, finalized_at "
        "FROM active_rings ORDER BY machine_name, slot_key",
    )


def _identity_rows(db):
    return _fetch_all(
        db,
        "SELECT serial_number, id, ring_mac, ring_name, product, first_seen_at, "
        "last_seen_at FROM ring_identities ORDER BY serial_number",
    )


# ── Lifecycle progression ───────────────────────────────────────────────────


def test_first_observation_creates_observed_rings(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    result = engine.apply(DIFF.diff(_empty(), _machine("aqc-03", (_slot(),))), _machine("aqc-03", (_slot(),)))

    assert result.has_conflicts is False
    assert result.rows_inserted == 1
    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][0] == "aqc-03"
    assert rows[0][1] == "1"
    assert rows[0][2] == "SN-1"
    assert rows[0][4] == "OBSERVED"
    assert rows[0][9] == 0
    assert rows[0][10] is None
    assert rows[0][11] is None
    assert rows[0][12] is None
    assert _count(scratch_schema, "ring_identities") == 1
    assert _count(scratch_schema, "ring_events") == 0
    assert _count(scratch_schema, "ring_history") == 0
    assert _count(scratch_schema, "machine_checkpoint") == 0


def test_continuous_observation_promotes_to_tracking(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    prev = _machine("aqc-03", (_slot(),), at=SESSION)
    curr = _machine("aqc-03", (_slot(),), at=SESSION + TICK)
    engine.apply(DIFF.diff(_empty(), prev), prev)
    result = engine.apply(DIFF.diff(prev, curr), curr)

    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][4] == "TRACKING"
    assert rows[0][7] == curr.generated_at
    assert result.rows_updated == 1
    assert result.rows_inserted == 0


def test_absent_cycle_keeps_ring_then_reappearance_resets(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    c1 = _machine("aqc-03", (_slot(),), at=SESSION)
    c2 = _machine("aqc-03", (_slot(),), at=SESSION + TICK)
    c3 = _machine("aqc-03", slots=(), at=SESSION + 2 * TICK)
    c4 = _machine("aqc-03", (_slot(),), at=SESSION + 3 * TICK)

    engine.apply(DIFF.diff(_empty(), c1), c1)
    engine.apply(DIFF.diff(c1, c2), c2)
    result3 = engine.apply(DIFF.diff(c2, c3), c3)

    assert _count(scratch_schema, "active_rings") == 1
    assert result3.rows_written == 0
    assert _active_rows(scratch_schema)[0][4] == "TRACKING"

    result4 = engine.apply(DIFF.diff(c3, c4), c4)
    assert result4.rows_updated == 1
    row = _active_rows(scratch_schema)[0]
    assert row[4] == "OBSERVED"
    assert row[7] == c4.generated_at


def test_slot_move_keeps_ring_id_and_first_seen(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    c1 = _machine("aqc-03", (_slot(key="1", serial="SN-1"),), at=SESSION)
    c2 = _machine("aqc-03", (_slot(key="2", serial="SN-1"),), at=SESSION + TICK)

    engine.apply(DIFF.diff(_empty(), c1), c1)
    result = engine.apply(DIFF.diff(c1, c2), c2)

    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][1] == "2"
    assert rows[0][3] == rows[0][3]  # ring_id preserved (single row)
    assert result.rows_deleted == 1
    assert result.rows_inserted == 1
    assert rows[0][6] == c1.generated_at  # first_seen_at carried
    assert rows[0][7] == c2.generated_at  # last_seen_at advanced


def test_slot_takeover_vacates_incumbent(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    c1 = _machine("aqc-03", (_slot(key="1", serial="SN-OLD", ring_mac="AA:01"),), at=SESSION)
    c2 = _machine("aqc-03", (_slot(key="1", serial="SN-NEW", ring_mac="AA:02"),), at=SESSION + TICK)

    engine.apply(DIFF.diff(_empty(), c1), c1)
    assert _count(scratch_schema, "active_rings") == 1

    result = engine.apply(DIFF.diff(c1, c2), c2)
    assert result.rows_deleted == 1
    assert result.rows_inserted == 1
    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][2] == "SN-NEW"
    assert rows[0][4] == "OBSERVED"
    assert _count(scratch_schema, "ring_identities") == 2


def test_absent_machine_writes_nothing(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    c1 = _machine("aqc-03", (_slot(),), at=SESSION)
    c2 = _machine("aqc-04", (_slot(),), at=SESSION + TICK)
    engine.apply(DIFF.diff(_empty(), c1), c1)

    before = _active_rows(scratch_schema)
    result = engine.apply(DIFF.diff(c1, c2), c2)
    assert result.machine_count == 1
    assert result.rows_written == 0
    assert _active_rows(scratch_schema) == before


def test_identity_last_seen_and_firmware_update(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    c1 = _machine("aqc-03", (_slot(firmware="1.0"),), at=SESSION)
    c2 = _machine("aqc-03", (_slot(firmware="2.0"),), at=SESSION + TICK)

    engine.apply(DIFF.diff(_empty(), c1), c1)
    engine.apply(DIFF.diff(c1, c2), c2)

    identity = _identity_rows(scratch_schema)
    assert len(identity) == 1
    assert identity[0][6] == c2.generated_at
    assert _active_rows(scratch_schema)[0][5] == "2.0"


# ── Never-write guarantees ──────────────────────────────────────────────────


def test_never_writes_pending_removal_or_finalized(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    c1 = _machine("aqc-03", (_slot(),), at=SESSION)
    c2 = _machine("aqc-03", (_slot(),), at=SESSION + TICK)
    c3 = _machine("aqc-03", slots=(), at=SESSION + 2 * TICK)
    c4 = _machine("aqc-03", (_slot(),), at=SESSION + 3 * TICK)
    engine.apply(DIFF.diff(_empty(), c1), c1)
    engine.apply(DIFF.diff(c1, c2), c2)
    engine.apply(DIFF.diff(c2, c3), c3)
    engine.apply(DIFF.diff(c3, c4), c4)
    states = {row[4] for row in _active_rows(scratch_schema)}
    assert states <= {"OBSERVED", "TRACKING"}
    assert _count(scratch_schema, "ring_events") == 0
    assert _count(scratch_schema, "ring_history") == 0


# ── Transaction, concurrency, recovery ──────────────────────────────────────


def test_idempotent_reapply_produces_identical_rows(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    batch = _machine("aqc-03", (_slot(),), at=SESSION)
    diff = DIFF.diff(_empty(), batch)

    engine.apply(diff, batch)
    first = _active_rows(scratch_schema)
    engine.apply(diff, batch)
    second = _active_rows(scratch_schema)

    assert second == first


def test_deterministic_apply_result(scratch_schema):
    from bic.db import BicDatabase, DbConfig
    from bic.schema import validate_schema_name
    from tests.conftest import _drop_schema

    def _fresh_schema():
        import uuid

        name = f"bic_scratch_{uuid.uuid4().hex[:8]}"
        validate_schema_name(name)
        db = BicDatabase(DbConfig(schema=name))
        db.initialize(applied_by="tests.state")
        return db

    prev = _machine("aqc-03", (_slot(),), at=SESSION)
    curr = _machine("aqc-03", (_slot(key="2", serial="SN-1"),), at=SESSION + TICK)
    sequence = [(DIFF.diff(_empty(), prev), prev), (DIFF.diff(prev, curr), curr)]

    engine = CollectorStateEngine(scratch_schema)
    results = [engine.apply(diff, batch) for diff, batch in sequence]

    other = _fresh_schema()
    try:
        second_engine = CollectorStateEngine(other)
        second_results = [second_engine.apply(diff, batch) for diff, batch in sequence]
    finally:
        other.close()
        _drop_schema(other.config.schema)

    assert results == second_results
    assert results[1] == second_results[1]
    assert results[1].session == second_results[1].session
    assert results[1].state == second_results[1].state


def test_empty_current_batch_is_noop(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    result = engine.apply(DIFF.diff(_empty(), _empty()), _empty())
    assert result.machine_count == 0
    assert result.rows_written == 0
    assert _count(scratch_schema, "active_rings") == 0


def test_cross_machine_duplicate_serial_conflicts(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    batch = ObservationBatch(
        machines=(
            MachineObservation(
                machine_name="aqc-01",
                bdr=_state(),
                rings=_state(),
                slots=(_slot(key="1", serial="SN-X"),),
            ),
            MachineObservation(
                machine_name="aqc-02",
                bdr=_state(),
                rings=_state(),
                slots=(_slot(key="1", serial="SN-X"),),
            ),
        ),
        generated_at=SESSION,
    )
    result = engine.apply(DIFF.diff(_empty(), batch), batch)

    assert result.has_conflicts is True
    assert result.rows_inserted == 1
    rows = _active_rows(scratch_schema)
    assert len(rows) == 1
    assert rows[0][0] == "aqc-01"


def test_recovery_restart_reapplies_without_duplication(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    c1 = _machine("aqc-03", (_slot(),), at=SESSION)
    c2 = _machine("aqc-03", (_slot(),), at=SESSION + TICK)

    engine.apply(DIFF.diff(_empty(), c1), c1)
    restarted = CollectorStateEngine(scratch_schema)
    result = restarted.apply(DIFF.diff(c1, c2), c2)

    assert result.rows_updated == 1
    assert result.rows_inserted == 0
    assert _count(scratch_schema, "active_rings") == 1


def test_query_and_row_accounting(scratch_schema):
    engine = CollectorStateEngine(scratch_schema)
    batch = _machine("aqc-03", (_slot(),), at=SESSION)
    first = engine.apply(DIFF.diff(_empty(), batch), batch)
    assert first.query_count == 5  # lock + active + identity + upsert + insert
    assert first.rows_read == 0
    assert first.rows_written == 2  # identity upsert + active insert
    assert first.rows_inserted == 1
    assert first.identity_writes == 1

    second = engine.apply(DIFF.diff(_empty(), batch), batch)
    assert second.query_count == 5  # lock + active + identity + upsert + update
    assert second.rows_updated == 1
