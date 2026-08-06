"""Unit tests for bic.state (Sprint 2, Task 5). No database required.

Covers the immutable object model, the Collector lifecycle state model, the
state transition rules, the pure reconciliation plan (determinism/idempotency),
and the apply-input contract.
"""

from datetime import datetime, timezone

import pytest

from bic.diff import DiffResult
from bic.reader import (
    MachineObservation,
    ObservationBatch,
    SlotObservation,
    SlotStatus,
    SourceState,
)
from bic.schema import LIFECYCLE_STATES
from bic.state import (
    CollectorState,
    InsertOp,
    MachineApplyStats,
    MachinePlan,
    MachineTrack,
    RingLifecycleState,
    RingTrack,
    RowState,
    occupied_slots,
    reconcile_machine,
    validate_apply_inputs,
)

SESSION = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 7, 31, 8, 0, 0, tzinfo=timezone.utc)


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


def _machine(slots=(), name="aqc-03"):
    return MachineObservation(
        machine_name=name,
        bdr=_state(),
        rings=_state(),
        slots=tuple(slots),
    )


def _row(row_id=1, serial="SN-1", slot="1", state="OBSERVED", ring_id=1,
         first_seen=SESSION, last_seen=SESSION, state_changed=SESSION,
         firmware="1.0"):
    return RowState(
        id=row_id,
        ring_id=ring_id,
        machine_name="aqc-03",
        slot_key=slot,
        serial_number=serial,
        lifecycle_state=state,
        state_changed_at=state_changed,
        first_seen_at=first_seen,
        last_seen_at=last_seen,
        removal_confirmations=0,
        removal_first_absent_at=None,
        firmware_version=firmware,
        end_reason=None,
        finalized_at=None,
    )


def _rows(*row_states):
    return {row.slot_key: row for row in row_states}


def _ring_ids(*serials):
    return {serial: index + 1 for index, serial in enumerate(serials)}


def _reconcile(observation, rows=(), ring_ids=(), new_serials=()):
    return reconcile_machine(
        "aqc-03",
        observation,
        _rows(*rows),
        _ring_ids(*ring_ids),
        frozenset(new_serials),
        SESSION,
    )


# ── State model ─────────────────────────────────────────────────────────────


def test_state_enum_mirrors_schema():
    assert {s.value for s in RingLifecycleState} == set(LIFECYCLE_STATES)
    assert RingLifecycleState.PENDING_REMOVAL.value == "PENDING_REMOVAL"
    assert RingLifecycleState.FINALIZED.value == "FINALIZED"


def test_track_helpers():
    track = MachineTrack(
        "aqc-03",
        (RingTrack("SN-1", "1", 1, "TRACKING", "1.0", SESSION, SESSION, SESSION),),
    )
    assert track.by_slot["1"].serial_number == "SN-1"
    assert track.by_serial["SN-1"].slot_key == "1"
    state = CollectorState(session=SESSION, machines=(track,))
    assert state.by_machine["aqc-03"] is track


# ── Transition rules ────────────────────────────────────────────────────────


def test_first_observation_creates_observed_rings():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        ring_ids=("SN-1",),
        new_serials=("SN-1",),
    )
    assert len(plan.inserts) == 1
    insert = plan.inserts[0]
    assert insert.lifecycle_state == "OBSERVED"
    assert insert.serial_number == "SN-1"
    assert insert.slot_key == "1"
    assert insert.first_seen_at == SESSION
    assert insert.last_seen_at == SESSION
    assert insert.state_changed_at == SESSION
    assert plan.deletes == ()
    assert plan.updates == ()


def test_continuous_observation_promotes_observed_to_tracking():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        rows=(_row(state="OBSERVED"),),
        ring_ids=("SN-1",),
    )
    assert len(plan.updates) == 1
    update = plan.updates[0]
    assert update.lifecycle_state == "TRACKING"
    assert update.state_changed_at == SESSION
    assert plan.inserts == ()
    assert plan.deletes == ()


def test_tracking_stays_tracking_and_preserves_state_changed_at():
    state_changed = T1
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        rows=(_row(state="TRACKING", state_changed=state_changed),),
        ring_ids=("SN-1",),
    )
    update = plan.updates[0]
    assert update.lifecycle_state == "TRACKING"
    assert update.state_changed_at == state_changed


def test_reappearance_resets_to_observed_in_place():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        rows=(_row(state="TRACKING"),),
        ring_ids=("SN-1",),
        new_serials=("SN-1",),
    )
    update = plan.updates[0]
    assert update.lifecycle_state == "OBSERVED"
    assert update.state_changed_at == SESSION


def test_reappearance_at_new_slot_resets_to_observed_and_moves():
    plan = _reconcile(
        _machine(slots=(_slot(key="2", serial="SN-1"),)),
        rows=(_row(slot="1", serial="SN-1", state="TRACKING"),),
        ring_ids=("SN-1",),
        new_serials=("SN-1",),
    )
    assert len(plan.deletes) == 1
    assert len(plan.inserts) == 1
    insert = plan.inserts[0]
    assert insert.slot_key == "2"
    assert insert.lifecycle_state == "OBSERVED"
    assert insert.first_seen_at == SESSION


def test_slot_move_carries_lifecycle_and_first_seen():
    plan = _reconcile(
        _machine(slots=(_slot(key="2", serial="SN-1"),)),
        rows=(_row(slot="1", serial="SN-1", state="TRACKING", first_seen=T1,
                   state_changed=T1),),
        ring_ids=("SN-1",),
    )
    assert len(plan.deletes) == 1
    assert len(plan.inserts) == 1
    insert = plan.inserts[0]
    assert insert.slot_key == "2"
    assert insert.lifecycle_state == "TRACKING"
    assert insert.first_seen_at == T1
    assert insert.last_seen_at == SESSION
    assert insert.state_changed_at == T1


def test_swap_moves_both_rings():
    plan = _reconcile(
        _machine(
            slots=(_slot(key="2", serial="SN-A"), _slot(key="1", serial="SN-B"))
        ),
        rows=(
            _row(row_id=1, serial="SN-A", slot="1", state="TRACKING", ring_id=10),
            _row(row_id=2, serial="SN-B", slot="2", state="TRACKING", ring_id=20),
        ),
        ring_ids=("SN-A", "SN-B"),
    )
    assert len(plan.deletes) == 2
    assert len(plan.inserts) == 2
    by_slot = {op.slot_key: op for op in plan.inserts}
    assert by_slot["1"].serial_number == "SN-B"
    assert by_slot["2"].serial_number == "SN-A"
    assert by_slot["1"].ring_id == 20
    assert by_slot["2"].ring_id == 10


def test_slot_takeover_vacates_absent_incumbent():
    plan = _reconcile(
        _machine(slots=(_slot(key="3", serial="SN-Y"),)),
        rows=(_row(row_id=9, serial="SN-X", slot="3", state="TRACKING", ring_id=30),),
        ring_ids=("SN-Y",),
        new_serials=("SN-Y",),
    )
    assert [d.row_id for d in plan.deletes] == [9]
    assert len(plan.inserts) == 1
    assert plan.inserts[0].serial_number == "SN-Y"
    assert plan.inserts[0].slot_key == "3"


def test_absent_serial_with_free_slot_is_kept():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        rows=(
            _row(row_id=1, serial="SN-1", slot="1", state="TRACKING"),
            _row(row_id=2, serial="SN-X", slot="5", state="TRACKING"),
        ),
        ring_ids=("SN-1",),
    )
    assert plan.inserts == ()
    assert plan.deletes == ()
    assert len(plan.updates) == 1
    kept = plan.result.by_serial["SN-X"]
    assert kept.slot_key == "5"
    assert kept.lifecycle_state == "TRACKING"


def test_machine_absent_produces_no_ops():
    plan = _reconcile(
        None,
        rows=(_row(serial="SN-X", slot="3", state="TRACKING"),),
    )
    assert plan.inserts == ()
    assert plan.updates == ()
    assert plan.deletes == ()
    assert len(plan.result.rings) == 1


def test_empty_observation_keeps_rows_unchanged():
    plan = _reconcile(
        _machine(slots=()),
        rows=(_row(serial="SN-X", slot="3", state="TRACKING"),),
    )
    assert plan.inserts == ()
    assert plan.deletes == ()
    assert plan.result.by_serial["SN-X"].lifecycle_state == "TRACKING"


# ── Edge cases ──────────────────────────────────────────────────────────────


def test_duplicate_serial_across_slots_first_wins():
    plan = _reconcile(
        _machine(
            slots=(_slot(key="2", serial="SN-DUP"), _slot(key="1", serial="SN-DUP"))
        ),
        ring_ids=("SN-DUP",),
        new_serials=("SN-DUP",),
    )
    assert len(plan.inserts) == 1
    assert plan.inserts[0].slot_key == "1"


def test_occupied_slots_first_wins_matches_diff():
    assert occupied_slots(
        _machine(
            slots=(_slot(key="2", serial="SN-DUP"), _slot(key="1", serial="SN-DUP"))
        )
    ) == {"1": "SN-DUP"}


def test_missing_identity_serial_is_skipped_with_conflict():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        ring_ids=("SN-2",),
        new_serials=("SN-1",),
    )
    assert plan.inserts == ()
    assert plan.conflicts
    assert "SN-1" in plan.conflicts[0]
    assert plan.result is not None
    assert plan.result.rings == ()


def test_firmware_updated_from_observation():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1", firmware="2.0"),)),
        rows=(_row(firmware="1.0"),),
        ring_ids=("SN-1",),
    )
    assert plan.updates[0].firmware_version == "2.0"
    assert plan.result.by_serial["SN-1"].firmware_version == "2.0"


def test_plan_never_writes_pending_removal_or_finalized():
    scenarios = (
        (_machine(slots=(_slot(key="1", serial="SN-1"),)), (), ("SN-1",), ("SN-1",)),
        (_machine(slots=(_slot(key="2", serial="SN-1"),)), (_row(state="TRACKING"),), ("SN-1",), ()),
        (_machine(slots=(_slot(key="1", serial="SN-1"),)), (_row(state="OBSERVED"),), ("SN-1",), ()),
    )
    for observation, rows, ring_ids, new_serials in scenarios:
        plan = _reconcile(observation, rows, ring_ids, new_serials)
        for op in (*plan.inserts, *plan.updates):
            assert op.lifecycle_state in ("OBSERVED", "TRACKING")


def test_machine_apply_stats_aggregation():
    stats = (
        MachineApplyStats("aqc-01", 2, 1, 0, 2, 6, 4, 5),
        MachineApplyStats("aqc-02", 0, 0, 0, 0, 3, 0, 0),
    )
    assert sum(stat.rows_written for stat in stats) == 5
    assert sum(stat.queries for stat in stats) == 9


# ── Determinism & idempotency ───────────────────────────────────────────────


def test_same_inputs_produce_identical_plan():
    observation = _machine(
        slots=(_slot(key="1", serial="SN-1", firmware="1.0"), _slot(key="2", serial="SN-2"))
    )
    first = _reconcile(observation, (_row(state="TRACKING"),), ("SN-1", "SN-2"))
    second = _reconcile(observation, (_row(state="TRACKING"),), ("SN-1", "SN-2"))
    assert first == second
    assert first.result == second.result


def test_reapply_is_end_state_idempotent():
    observation = _machine(slots=(_slot(key="1", serial="SN-1"),))
    first = _reconcile(observation, (), ("SN-1",), ("SN-1",))
    rows = {ring.slot_key: _row(row_id=ring.ring_id, serial=ring.serial_number,
                               slot=ring.slot_key, state=ring.lifecycle_state,
                               ring_id=ring.ring_id)
            for ring in first.result.rings}
    second = reconcile_machine(
        "aqc-03", observation, rows, _ring_ids("SN-1"), frozenset({"SN-1"}), SESSION
    )
    assert second.result == first.result


def test_reapply_promoted_state_is_idempotent():
    observation = _machine(slots=(_slot(key="1", serial="SN-1"),))
    first = _reconcile(observation, (_row(state="OBSERVED"),), ("SN-1",))
    assert first.result.by_serial["SN-1"].lifecycle_state == "TRACKING"
    rows = {ring.slot_key: _row(row_id=ring.ring_id, serial=ring.serial_number,
                               slot=ring.slot_key, state=ring.lifecycle_state,
                               ring_id=ring.ring_id)
            for ring in first.result.rings}
    second = reconcile_machine(
        "aqc-03", observation, rows, _ring_ids("SN-1"), frozenset(), SESSION
    )
    assert second.result == first.result


# ── Apply input contract ────────────────────────────────────────────────────


def test_validate_apply_inputs_returns_tz_aware_session():
    batch = ObservationBatch(
        machines=(), generated_at=SESSION
    )
    session = validate_apply_inputs(DiffResult(), batch)
    assert session == SESSION
    assert session.tzinfo is not None


def test_validate_apply_inputs_rejects_wrong_types():
    batch = ObservationBatch(machines=(), generated_at=SESSION)
    with pytest.raises(TypeError):
        validate_apply_inputs(batch, batch)
    with pytest.raises(TypeError):
        validate_apply_inputs(DiffResult(), SESSION)


def test_validate_apply_inputs_rejects_missing_or_naive_session():
    with pytest.raises(ValueError):
        validate_apply_inputs(DiffResult(), ObservationBatch(machines=(), generated_at=None))
    with pytest.raises(ValueError):
        validate_apply_inputs(
            DiffResult(),
            ObservationBatch(machines=(), generated_at=datetime(2026, 8, 1, 10, 0)),
        )
