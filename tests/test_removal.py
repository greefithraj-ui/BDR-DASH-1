"""Unit tests for bic.removal (Sprint 2, Task 6). No database required.

Covers the removal object model, the confirmation-counter rules (first absence,
increment, PENDING_REMOVAL promotion, offline suspension, reappearance
cancellation), the pure reconciliation plan (order, determinism, idempotent
pending state), and the confirmation-threshold contract.
"""

from datetime import datetime, timedelta, timezone

import pytest

from bic.config import REMOVAL_CONFIRMATIONS
from bic.reader import (
    MachineObservation,
    SlotObservation,
    SlotStatus,
    SourceState,
)
from bic.removal import (
    MachineRemovalPlan,
    RemovalApplyResult,
    RemovalMachineStats,
    RemovalOp,
    reconcile_removals,
)
from bic.state import RowState

SESSION = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
T1 = datetime(2026, 7, 31, 8, 0, 0, tzinfo=timezone.utc)


def _state(present=True, fresh=True):
    return SourceState(
        present=present,
        age_seconds=5.0 if fresh else 300.0,
        fresh=fresh,
    )


def _slot(key="1", serial="SN-1"):
    return SlotObservation(
        machine_name="aqc-03",
        slot_key=key,
        status=SlotStatus.MATCH,
        serial_bdr=serial,
        serial_rings=serial,
        ring_mac="AA:BB",
        ring_name="RingA",
        product="PRO",
        firmware_version="1.0",
        bdr_payload={"serial_number": serial},
        rings_payload={"serial_number": serial},
    )


def _machine(slots=(), name="aqc-03", fresh=True):
    return MachineObservation(
        machine_name=name,
        bdr=_state(fresh=fresh),
        rings=_state(fresh=fresh),
        slots=tuple(slots),
    )


def _row(row_id=1, serial="SN-1", slot="1", state="TRACKING", counter=0,
         first_absent=None, ring_id=1):
    return RowState(
        id=row_id,
        ring_id=ring_id,
        machine_name="aqc-03",
        slot_key=slot,
        serial_number=serial,
        lifecycle_state=state,
        state_changed_at=T1,
        first_seen_at=T1,
        last_seen_at=T1,
        removal_confirmations=counter,
        removal_first_absent_at=first_absent,
        firmware_version="1.0",
        end_reason=None,
        finalized_at=None,
    )


def _reconcile(observation, rows=(), session=SESSION,
               confirmations=REMOVAL_CONFIRMATIONS):
    return reconcile_removals(
        "aqc-03",
        observation,
        {row.slot_key: row for row in rows},
        session,
        confirmations,
    )


# ── Confirmation counting ───────────────────────────────────────────────────


def test_first_absence_starts_counter_and_records_timestamp():
    plan = _reconcile(
        _machine(slots=()),
        rows=(_row(state="TRACKING", counter=0, first_absent=None),),
    )
    assert plan.suspended is False
    assert len(plan.updates) == 1
    op = plan.updates[0]
    assert op.removal_confirmations == 1
    assert op.removal_first_absent_at == SESSION
    assert op.lifecycle_state == "TRACKING"
    assert op.state_changed_at == T1
    assert plan.candidates_started == 1
    assert plan.candidates_confirmed == 0


def test_second_absence_increments_and_keeps_first_absent():
    plan = _reconcile(
        _machine(slots=()),
        rows=(_row(state="TRACKING", counter=1, first_absent=T1),),
        session=SESSION + timedelta(seconds=30),
    )
    op = plan.updates[0]
    assert op.removal_confirmations == 2
    assert op.removal_first_absent_at == T1
    assert op.lifecycle_state == "TRACKING"


def test_third_absence_confirms_pending_removal():
    plan = _reconcile(
        _machine(slots=()),
        rows=(_row(state="TRACKING", counter=2, first_absent=T1),),
    )
    assert plan.candidates_confirmed == 1
    op = plan.updates[0]
    assert op.removal_confirmations == 3
    assert op.removal_first_absent_at == T1
    assert op.lifecycle_state == "PENDING_REMOVAL"
    assert op.state_changed_at == SESSION


def test_confirmations_are_capped_at_threshold():
    plan = _reconcile(
        _machine(slots=()),
        rows=(_row(state="TRACKING", counter=2, first_absent=T1),),
    )
    assert plan.updates[0].removal_confirmations == REMOVAL_CONFIRMATIONS == 3


def test_custom_confirmation_threshold_confirms_sooner():
    plan = _reconcile(
        _machine(slots=()),
        rows=(_row(state="TRACKING", counter=1, first_absent=T1),),
        confirmations=2,
    )
    assert plan.updates[0].removal_confirmations == 2
    assert plan.updates[0].lifecycle_state == "PENDING_REMOVAL"


def test_pending_removal_still_absent_is_idempotent_noop():
    plan = _reconcile(
        _machine(slots=()),
        rows=(_row(state="PENDING_REMOVAL", counter=3, first_absent=T1),),
    )
    assert plan.updates == ()
    assert plan.candidates_started == 0
    assert plan.candidates_confirmed == 0


def test_absent_observation_counts_every_tracked_ring():
    plan = _reconcile(
        _machine(slots=()),
        rows=(
            _row(row_id=1, serial="SN-A", slot="1", state="TRACKING"),
            _row(row_id=2, serial="SN-B", slot="2", state="TRACKING"),
        ),
    )
    assert len(plan.updates) == 2
    assert [op.slot_key for op in plan.updates] == ["1", "2"]
    assert all(op.removal_confirmations == 1 for op in plan.updates)


def test_updates_are_sorted_by_slot_key():
    plan = _reconcile(
        _machine(slots=()),
        rows=(
            _row(row_id=2, serial="SN-B", slot="2"),
            _row(row_id=1, serial="SN-A", slot="1"),
        ),
    )
    assert [op.row_id for op in plan.updates] == [1, 2]


# ── Reappearance cancellation ───────────────────────────────────────────────


def test_present_ring_with_clean_counters_is_noop():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        rows=(_row(state="TRACKING", counter=0, first_absent=None),),
    )
    assert plan.updates == ()
    assert plan.cancellations == 0


def test_reappearance_cancels_counter():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        rows=(_row(state="TRACKING", counter=2, first_absent=T1),),
    )
    assert plan.cancellations == 1
    op = plan.updates[0]
    assert op.removal_confirmations == 0
    assert op.removal_first_absent_at is None
    assert op.lifecycle_state == "TRACKING"
    assert op.state_changed_at == T1


def test_reappearance_of_pending_removal_resets_to_observed():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        rows=(_row(state="PENDING_REMOVAL", counter=3, first_absent=T1),),
    )
    op = plan.updates[0]
    assert op.lifecycle_state == "OBSERVED"
    assert op.state_changed_at == SESSION
    assert op.removal_confirmations == 0
    assert op.removal_first_absent_at is None


# ── Offline / stale suspension ──────────────────────────────────────────────


def test_stale_machine_suspends_even_when_rings_absent():
    plan = _reconcile(
        _machine(slots=(), fresh=False),
        rows=(_row(state="TRACKING", counter=0),),
    )
    assert plan.suspended is True
    assert plan.updates == ()


def test_stale_machine_suspends_even_when_rings_present():
    plan = _reconcile(
        _machine(slots=(_slot(key="1", serial="SN-1"),), fresh=False),
        rows=(_row(state="TRACKING", counter=2, first_absent=T1),),
    )
    assert plan.suspended is True
    assert plan.updates == ()


def test_stale_machine_does_not_reset_existing_counters():
    plan = _reconcile(
        _machine(slots=(), fresh=False),
        rows=(_row(state="TRACKING", counter=2, first_absent=T1),),
    )
    assert plan.suspended is True
    assert plan.updates == ()
    assert plan.cancellations == 0


def test_none_observation_suspends():
    plan = _reconcile(None, rows=(_row(),))
    assert plan.suspended is True
    assert plan.updates == ()


def test_machine_absent_from_batch_freeze_is_callers_concern():
    # A machine with no observation in the batch is never iterated by the engine;
    # the pure function treats a missing observation as suspension (no writes).
    assert _reconcile(None, rows=(_row(),)).updates == ()


# ── Determinism & result model ──────────────────────────────────────────────


def test_same_inputs_produce_identical_plan():
    observation = _machine(slots=())
    rows = {
        "1": _row(serial="SN-A", slot="1", state="TRACKING", counter=1, first_absent=T1),
        "2": _row(row_id=2, serial="SN-B", slot="2", state="TRACKING"),
    }
    first = reconcile_removals(
        "aqc-03", observation, rows, SESSION, REMOVAL_CONFIRMATIONS
    )
    second = reconcile_removals(
        "aqc-03", observation, rows, SESSION, REMOVAL_CONFIRMATIONS
    )
    assert first == second


def test_result_aggregation():
    result = RemovalApplyResult(
        session=SESSION,
        stats=(
            RemovalMachineStats("aqc-01", 2, 1, 1, 0, False, 3, 2, 2),
            RemovalMachineStats("aqc-02", 0, 0, 0, 0, True, 2, 1, 0),
        ),
    )
    assert result.machine_count == 2
    assert result.query_count == 5
    assert result.rows_read == 3
    assert result.rows_written == 2
    assert result.rows_updated == 2
    assert result.candidates_started == 1
    assert result.candidates_confirmed == 1
    assert result.suspended_machines == 1


def test_removal_op_never_carries_non_removal_fields():
    op = RemovalOp(
        row_id=1,
        serial_number="SN-1",
        slot_key="1",
        lifecycle_state="PENDING_REMOVAL",
        state_changed_at=SESSION,
        removal_confirmations=3,
        removal_first_absent_at=T1,
    )
    assert not hasattr(op, "last_seen_at")
    assert not hasattr(op, "end_reason")
    assert not hasattr(op, "finalized_at")


def test_engine_rejects_invalid_confirmation_threshold():
    from bic.removal import validate_confirmations

    assert validate_confirmations(None) == REMOVAL_CONFIRMATIONS
    assert validate_confirmations(2) == 2
    with pytest.raises(ValueError):
        validate_confirmations(0)
    with pytest.raises(ValueError):
        validate_confirmations(1.5)
    with pytest.raises(ValueError):
        validate_confirmations(-3)


def test_machine_removal_plan_defaults():
    plan = MachineRemovalPlan(machine_name="aqc-03")
    assert plan.updates == ()
    assert plan.suspended is False
    assert plan.candidates_started == 0
    assert plan.candidates_confirmed == 0
    assert plan.cancellations == 0
