"""Unit tests for bic.diff (Sprint 2, Task 4). No database required.

The Smart Update Engine compares a previous ObservationBatch against a current
one and emits immutable Change objects only. It makes no collector decisions and
writes nothing.
"""

import pytest

from bic.diff import (
    Change,
    ChangeType,
    DiffResult,
    MachineChanges,
    SlotInfo,
    SmartUpdateEngine,
)
from bic.reader import (
    MachineObservation,
    ObservationBatch,
    SlotObservation,
    SlotStatus,
    SourceState,
)

ENGINE = SmartUpdateEngine()


def _state(present=True, fresh=True):
    return SourceState(
        present=present,
        age_seconds=5.0 if fresh else 300.0,
        fresh=fresh,
    )


def _slot(
    key="1",
    serial="SN-1",
    ring_mac="AA:BB",
    ring_name="RingA",
    product="PRO",
    state="BDR_RUNNING",
    firmware="1.0",
    status=SlotStatus.MATCH,
):
    payload = {
        "serial_number": serial,
        "ring_mac": ring_mac,
        "ring_name": ring_name,
        "product": product,
        "state": state,
    }
    return SlotObservation(
        machine_name="aqc-03",
        slot_key=key,
        status=status,
        serial_bdr=serial,
        serial_rings=serial,
        ring_mac=ring_mac,
        ring_name=ring_name,
        product=product,
        firmware_version=firmware,
        bdr_payload=dict(payload),
        rings_payload=dict(payload),
    )


def _machine(slots=(), name="aqc-03"):
    return MachineObservation(
        machine_name=name,
        bdr=_state(),
        rings=_state(),
        slots=tuple(slots),
    )


def _batch(*machines):
    return ObservationBatch(machines=tuple(machines))


def _types(changes):
    return {change.change_type for change in changes}


def _by_type(changes, change_type):
    return [change for change in changes if change.change_type is change_type]


# ── No-op cases ──────────────────────────────────────────────────────────────


def test_identical_batch_has_no_changes():
    result = ENGINE.diff(_batch(_machine(slots=(_slot(),))), _batch(_machine(slots=(_slot(),))))
    assert result.has_changes is False
    assert result.change_count == 0
    assert result.machine_count == 1
    assert result.machines[0].has_changes is False


def test_empty_batches_produce_empty_result():
    result = ENGINE.diff(_batch(), _batch())
    assert result.machine_count == 0
    assert result.change_count == 0
    assert result.has_changes is False


def test_diff_machine_none_none_is_empty():
    result = ENGINE.diff_machine("aqc-03", None, None)
    assert result.machine_name == "aqc-03"
    assert result.changes == ()
    assert result.has_changes is False


# ── Ring lifecycle: NEW_RING / REMOVED_RING_CANDIDATE ───────────────────────


def test_new_ring_when_machine_first_observed():
    result = ENGINE.diff_machine(
        "aqc-03",
        None,
        _machine(slots=(_slot(key="1", serial="SN-1"), _slot(key="2", serial="SN-2"))),
    )
    assert _types(result.changes) == {ChangeType.NEW_RING}
    new_rings = _by_type(result.changes, ChangeType.NEW_RING)
    assert {change.serial_number for change in new_rings} == {"SN-1", "SN-2"}
    assert all(change.previous is None for change in new_rings)
    assert all(change.current is not None for change in new_rings)


def test_removed_ring_candidate_when_machine_gone():
    result = ENGINE.diff_machine(
        "aqc-03",
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        None,
    )
    assert _types(result.changes) == {ChangeType.REMOVED_RING_CANDIDATE}
    removed = result.changes[0]
    assert removed.serial_number == "SN-1"
    assert removed.previous is not None
    assert removed.current is None
    assert removed.previous.slot_key == "1"


def test_new_ring_for_new_serial_in_observed_machine():
    prev = _machine(slots=(_slot(key="1", serial="SN-1"),))
    curr = _machine(slots=(_slot(key="1", serial="SN-1"), _slot(key="2", serial="SN-2")))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    new_rings = _by_type(result.changes, ChangeType.NEW_RING)
    assert len(new_rings) == 1
    assert new_rings[0].serial_number == "SN-2"


def test_removed_ring_candidate_for_missing_serial():
    prev = _machine(slots=(_slot(key="1", serial="SN-1"), _slot(key="2", serial="SN-2")))
    curr = _machine(slots=(_slot(key="1", serial="SN-1"),))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    removed = _by_type(result.changes, ChangeType.REMOVED_RING_CANDIDATE)
    assert len(removed) == 1
    assert removed[0].serial_number == "SN-2"
    assert removed[0].previous.slot_key == "2"
    assert removed[0].current is None


# ── In-place field changes ───────────────────────────────────────────────────


def test_serial_changed_in_place():
    prev = _machine(slots=(_slot(key="1", serial="SN-1"),))
    curr = _machine(slots=(_slot(key="1", serial="SN-9"),))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    assert {
        ChangeType.SERIAL_CHANGED,
        ChangeType.NEW_RING,
        ChangeType.REMOVED_RING_CANDIDATE,
    } <= _types(result.changes)
    change = _by_type(result.changes, ChangeType.SERIAL_CHANGED)[0]
    assert change.previous_serial == "SN-1"
    assert change.current_serial == "SN-9"
    assert change.previous_slot_key == "1"
    assert change.current_slot_key == "1"


def test_state_changed_in_place():
    prev = _machine(slots=(_slot(state="BDR_RUNNING"),))
    curr = _machine(slots=(_slot(state="PASSED"),))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    assert _types(result.changes) == {ChangeType.STATE_CHANGED}
    change = result.changes[0]
    assert change.previous.state == "BDR_RUNNING"
    assert change.current.state == "PASSED"
    assert change.slot_key == "1"


def test_firmware_changed_in_place():
    prev = _machine(slots=(_slot(firmware="1.0"),))
    curr = _machine(slots=(_slot(firmware="2.0"),))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    assert _types(result.changes) == {ChangeType.FIRMWARE_CHANGED}
    change = result.changes[0]
    assert change.previous.firmware_version == "1.0"
    assert change.current.firmware_version == "2.0"


def test_identity_changed_reports_changed_fields():
    prev = _machine(slots=(_slot(ring_mac="AA:BB", ring_name="RingA", product="PRO"),))
    curr = _machine(slots=(_slot(ring_mac="AA:BB", ring_name="RingB", product="PRO2"),))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    identity = _by_type(result.changes, ChangeType.IDENTITY_CHANGED)
    assert len(identity) == 1
    assert set(identity[0].changed_fields) == {"ring_name", "product"}
    assert identity[0].current.ring_name == "RingB"
    assert identity[0].current.product == "PRO2"


def test_identity_change_ignores_non_identity_fields():
    prev = _machine(slots=(_slot(state="BDR_RUNNING", firmware="1.0"),))
    curr = _machine(slots=(_slot(state="PASSED", firmware="2.0"),))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    assert ChangeType.IDENTITY_CHANGED not in _types(result.changes)


# ── Slot moves ───────────────────────────────────────────────────────────────


def test_slot_changed_when_ring_moves_slots():
    prev = _machine(slots=(_slot(key="1", serial="SN-1"), _slot(key="2", serial="SN-2")))
    curr = _machine(slots=(_slot(key="2", serial="SN-1"), _slot(key="1", serial="SN-2")))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    slot_changed = _by_type(result.changes, ChangeType.SLOT_CHANGED)
    assert len(slot_changed) == 2
    moved = next(c for c in slot_changed if c.serial_number == "SN-1")
    assert moved.previous_slot_key == "1"
    assert moved.current_slot_key == "2"


def test_slot_move_coemits_state_and_firmware_when_changed():
    prev = _machine(
        slots=(_slot(key="1", serial="SN-1", state="BDR_RUNNING", firmware="1.0"),)
    )
    curr = _machine(
        slots=(_slot(key="2", serial="SN-1", state="PASSED", firmware="2.0"),)
    )
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    assert {ChangeType.SLOT_CHANGED, ChangeType.STATE_CHANGED, ChangeType.FIRMWARE_CHANGED} <= _types(
        result.changes
    )
    slot_change = _by_type(result.changes, ChangeType.SLOT_CHANGED)[0]
    assert slot_change.serial_number == "SN-1"
    assert slot_change.previous_slot_key == "1"
    assert slot_change.current_slot_key == "2"


def test_slot_swap_emits_serial_changed_for_both_slots():
    prev = _machine(slots=(_slot(key="1", serial="SN-1"), _slot(key="2", serial="SN-2")))
    curr = _machine(slots=(_slot(key="1", serial="SN-2"), _slot(key="2", serial="SN-1")))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    serial_changed = _by_type(result.changes, ChangeType.SERIAL_CHANGED)
    assert len(serial_changed) == 2


# ── Machine-absent semantics through the batch API ───────────────────────────


def test_new_machine_in_batch_yields_new_rings():
    result = ENGINE.diff(
        _batch(_machine(name="aqc-01", slots=(_slot(serial="SN-1"),))),
        _batch(
            _machine(name="aqc-01", slots=(_slot(serial="SN-1"),)),
            _machine(name="aqc-02", slots=(_slot(serial="SN-5"),)),
        ),
    )
    assert {machine.machine_name for machine in result.machines} == {"aqc-01", "aqc-02"}
    aqc02 = result.by_machine["aqc-02"]
    assert _types(aqc02.changes) == {ChangeType.NEW_RING}


def test_missing_machine_in_batch_yields_removed_candidates():
    result = ENGINE.diff(
        _batch(
            _machine(name="aqc-01", slots=(_slot(serial="SN-1"),)),
            _machine(name="aqc-02", slots=(_slot(serial="SN-5"),)),
        ),
        _batch(_machine(name="aqc-01", slots=(_slot(serial="SN-1"),))),
    )
    aqc02 = result.by_machine["aqc-02"]
    assert _types(aqc02.changes) == {ChangeType.REMOVED_RING_CANDIDATE}
    assert aqc02.changes[0].serial_number == "SN-5"


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_slot_without_serial_produces_no_change():
    no_serial = SlotObservation(
        machine_name="aqc-03",
        slot_key="1",
        status=SlotStatus.RINGS_ONLY,
        serial_bdr=None,
        serial_rings=None,
        ring_mac=None,
        ring_name=None,
        product=None,
        firmware_version=None,
        bdr_payload=None,
        rings_payload={"state": "PASSED"},
    )
    result = ENGINE.diff(
        _batch(_machine(slots=(no_serial,))),
        _batch(_machine(slots=(no_serial,))),
    )
    assert result.change_count == 0
    assert result.machine_count == 0 or result.machines[0].has_changes is False


def test_serial_map_first_wins_by_sorted_slot_key():
    prev = _machine(
        slots=(
            _slot(key="2", serial="SN-DUP"),
            _slot(key="1", serial="SN-DUP"),
            _slot(key="3", serial="SN-3"),
        )
    )
    curr = _machine(
        slots=(
            _slot(key="1", serial="SN-DUP"),
            _slot(key="3", serial="SN-3"),
        )
    )
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    removed = _by_type(result.changes, ChangeType.REMOVED_RING_CANDIDATE)
    assert len(removed) == 0
    assert ChangeType.SLOT_CHANGED not in _types(result.changes)


def test_change_snapshot_anchors():
    change = ENGINE.diff_machine(
        "aqc-03",
        _machine(slots=(_slot(key="1", serial="SN-1"),)),
        _machine(slots=(_slot(key="2", serial="SN-1"),)),
    ).changes[0]
    assert change.change_type is ChangeType.SLOT_CHANGED
    assert change.serial_number == "SN-1"
    assert change.slot_key == "2"
    assert change.previous_serial == "SN-1"
    assert change.current_serial == "SN-1"


def test_state_prefers_rings_over_bdr():
    bdr_payload = {"serial_number": "SN-1", "state": "BDR_RUNNING"}
    rings_payload = {"serial_number": "SN-1", "state": "PASSED"}
    prev = _machine(
        slots=(
            SlotObservation(
                machine_name="aqc-03",
                slot_key="1",
                status=SlotStatus.MATCH,
                serial_bdr="SN-1",
                serial_rings="SN-1",
                ring_mac="AA:BB",
                ring_name="RingA",
                product="PRO",
                firmware_version="1.0",
                bdr_payload=bdr_payload,
                rings_payload=rings_payload,
            ),
        )
    )
    curr = _machine(slots=(_slot(key="1", serial="SN-1", state="PASSED"),))
    result = ENGINE.diff_machine("aqc-03", prev, curr)
    assert result.has_changes is False


# ── Determinism & aggregation ────────────────────────────────────────────────


def test_same_inputs_produce_identical_changes():
    prev = _batch(
        _machine(name="aqc-01", slots=(_slot(key="1", serial="SN-1"),)),
        _machine(name="aqc-02", slots=(_slot(key="1", serial="SN-5"), _slot(key="2", serial="SN-6"))),
    )
    curr = _batch(
        _machine(name="aqc-01", slots=(_slot(key="1", serial="SN-1", state="PASSED"),)),
        _machine(name="aqc-02", slots=(_slot(key="2", serial="SN-5"),)),
        _machine(name="aqc-03", slots=(_slot(key="1", serial="SN-9"),)),
    )
    first = ENGINE.diff(prev, curr)
    second = ENGINE.diff(prev, curr)
    assert first == second
    assert first.machines == second.machines
    assert first.changes == second.changes
    assert first.count_by_type() == second.count_by_type()


def test_diff_is_strictly_deterministic_for_every_field():
    prev = _batch(
        _machine(name="aqc-01", slots=(_slot(key="1", serial="SN-1"),)),
        _machine(name="aqc-02", slots=(_slot(key="1", serial="SN-5"),)),
    )
    curr = _batch(
        _machine(name="aqc-01", slots=(_slot(key="2", serial="SN-1", state="PASSED"),)),
        _machine(name="aqc-02", slots=(_slot(key="1", serial="SN-5"), _slot(key="2", serial="SN-9"))),
    )
    first = ENGINE.diff(prev, curr)
    second = ENGINE.diff(prev, curr)
    assert first == second
    assert first.generated_at == second.generated_at
    assert first.generated_at == curr.generated_at
    assert first.machine_count == second.machine_count
    assert first.change_count == second.change_count


def test_diff_result_flat_changes_sorted_and_count_by_type():
    prev = _batch(
        _machine(name="aqc-01", slots=(_slot(key="1", serial="SN-1"),)),
        _machine(name="aqc-02", slots=(_slot(key="1", serial="SN-5"),)),
    )
    curr = _batch(
        _machine(name="aqc-01", slots=(_slot(key="1", serial="SN-1"), _slot(key="2", serial="SN-2"))),
        _machine(name="aqc-02", slots=(_slot(key="1", serial="SN-5", state="PASSED"),)),
    )
    result = ENGINE.diff(prev, curr)
    keys = [(change.machine_name, change.serial_number) for change in result.changes]
    assert keys == sorted(keys)
    counts = result.count_by_type()
    assert counts[ChangeType.NEW_RING] == 1
    assert counts[ChangeType.STATE_CHANGED] == 1
    assert counts[ChangeType.SLOT_CHANGED] == 0


def test_engine_does_not_mutate_inputs():
    prev = _machine(slots=(_slot(key="1", serial="SN-1"),))
    curr = _machine(slots=(_slot(key="1", serial="SN-9"),))
    ENGINE.diff(_batch(prev), _batch(curr))
    assert prev.slot_map["1"].serial_number == "SN-1"
    assert curr.slot_map["1"].serial_number == "SN-9"
