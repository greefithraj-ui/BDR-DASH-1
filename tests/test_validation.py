"""Unit tests for bic.validation (Sprint 2, Task 3). No database required."""

import pytest

from bic.reader import (
    MachineObservation,
    ObservationBatch,
    SlotObservation,
    SlotStatus,
    SourceState,
    build_machine_observation,
)
from bic.validation import (
    Severity,
    ValidationCode,
    ValidationEngine,
    machine_issues,
    slot_issues,
)
from tests.fixture_loader import load_fixture


def _state(present=True, fresh=True, parse_error=None):
    return SourceState(
        present=present,
        age_seconds=5.0 if fresh else 300.0,
        fresh=fresh,
        parse_error=parse_error,
    )


def _make_payloads(status, serial, ring_mac, ring_name, product, state, step):
    serial_bdr = serial if status in (SlotStatus.MATCH, SlotStatus.MISMATCH, SlotStatus.BDR_ONLY) else None
    serial_rings = serial if status in (SlotStatus.MATCH, SlotStatus.MISMATCH, SlotStatus.RINGS_ONLY) else None
    bdr_payload = None
    if status in (SlotStatus.MATCH, SlotStatus.MISMATCH, SlotStatus.BDR_ONLY):
        bdr_payload = {
            "serial_number": serial,
            "ring_mac": ring_mac,
            "ring_name": ring_name,
            "product": product,
            "state": state,
        }
    rings_payload = None
    if status in (SlotStatus.MATCH, SlotStatus.MISMATCH, SlotStatus.RINGS_ONLY):
        rings_payload = {
            "serial_number": serial if status is not SlotStatus.MISMATCH else serial + "-X",
            "ring_mac": ring_mac,
            "ring_name": ring_name,
            "product": product,
            "state": state,
            "step_statuses": {"BDR_TEST": step},
        }
        serial_rings = rings_payload["serial_number"]
    return bdr_payload, rings_payload, serial_bdr, serial_rings


def _slot(
    key="1",
    status=SlotStatus.MATCH,
    serial="SN-1",
    ring_mac="AA:BB",
    ring_name="RingA",
    product="PRO",
    state="BDR_RUNNING",
    step="IN_PROGRESS",
):
    bdr_payload, rings_payload, serial_bdr, serial_rings = _make_payloads(
        status, serial, ring_mac, ring_name, product, state, step
    )
    return SlotObservation(
        machine_name="aqc-03",
        slot_key=key,
        status=status,
        serial_bdr=serial_bdr,
        serial_rings=serial_rings,
        ring_mac=ring_mac,
        ring_name=ring_name,
        product=product,
        firmware_version="1.0",
        bdr_payload=bdr_payload,
        rings_payload=rings_payload,
    )


def _machine(bdr_state=None, rings_state=None, slots=()):
    return MachineObservation(
        machine_name="aqc-03",
        bdr=bdr_state if bdr_state is not None else _state(),
        rings=rings_state if rings_state is not None else _state(),
        slots=tuple(slots),
    )


def _find(result, code):
    machines = getattr(result, "machines", None)
    if machines is None:
        for issue in result.issues:
            if issue.code is code:
                return issue
        for slot in getattr(result, "slots", ()):
            for issue in slot.issues:
                if issue.code is code:
                    return issue
        return None
    for machine in machines:
        for issue in machine.issues:
            if issue.code is code:
                return issue
        for slot in machine.slots:
            for issue in slot.issues:
                if issue.code is code:
                    return issue
    return None


def test_valid_machine_and_slot_pass():
    engine = ValidationEngine()
    batch = ObservationBatch(machines=(_machine(slots=(_slot(),)),))
    result = engine.validate(batch)
    assert result.valid is True
    assert result.machine_count == 1
    assert result.slot_count == 1
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.machines[0].valid is True
    assert result.machines[0].slots[0].valid is True


def test_machine_stale_is_error():
    result = ValidationEngine().validate_machine(
        _machine(bdr_state=_state(fresh=False), rings_state=_state(fresh=False))
    )
    assert result.valid is False
    issue = _find(result, ValidationCode.MACHINE_STALE)
    assert issue is not None
    assert issue.severity is Severity.ERROR


def test_source_parse_error_is_error():
    result = ValidationEngine().validate_machine(
        _machine(bdr_state=_state(parse_error="invalid JSON: x"))
    )
    assert result.valid is False
    assert _find(result, ValidationCode.SOURCE_PARSE_ERROR) is not None


def test_source_missing_is_warning_only():
    result = ValidationEngine().validate_machine(
        _machine(rings_state=_state(present=False))
    )
    assert result.valid is True
    issue = _find(result, ValidationCode.SOURCE_MISSING)
    assert issue is not None
    assert issue.severity is Severity.WARNING


def test_serial_mismatch_is_error():
    result = ValidationEngine().validate_machine(
        _machine(slots=(_slot(status=SlotStatus.MISMATCH),))
    )
    assert result.valid is False
    issue = _find(result, ValidationCode.SLOT_SERIAL_MISMATCH)
    assert issue is not None
    assert issue.severity is Severity.ERROR
    assert issue.slot_key == "1"


def test_one_source_only_is_warning():
    result = ValidationEngine().validate_machine(
        _machine(slots=(_slot(status=SlotStatus.RINGS_ONLY),))
    )
    assert result.valid is True
    issue = _find(result, ValidationCode.SLOT_ONE_SOURCE_ONLY)
    assert issue is not None
    assert issue.severity is Severity.WARNING
    assert issue.slot_key == "1"


def test_identity_field_missing_is_error():
    slot = _slot()
    slot = SlotObservation(
        machine_name=slot.machine_name,
        slot_key=slot.slot_key,
        status=slot.status,
        serial_bdr=slot.serial_bdr,
        serial_rings=slot.serial_rings,
        ring_mac=None,
        ring_name=slot.ring_name,
        product=slot.product,
        firmware_version="1.0",
        bdr_payload=slot.bdr_payload,
        rings_payload=slot.rings_payload,
    )
    result = ValidationEngine().validate_slot(slot)
    assert result.valid is False
    assert _find(result, ValidationCode.IDENTITY_FIELD_MISSING) is not None


def test_identity_field_mismatch_is_error():
    bdr = {
        "serial_number": "SN-1",
        "ring_mac": "AA",
        "ring_name": "RingA",
        "product": "PRO",
        "state": "BDR_RUNNING",
    }
    rings = {
        "serial_number": "SN-1",
        "ring_mac": "AA",
        "ring_name": "RingB",
        "product": "PRO",
        "state": "BDR_RUNNING",
        "step_statuses": {"BDR_TEST": "IN_PROGRESS"},
    }
    slot = SlotObservation(
        machine_name="aqc-03",
        slot_key="1",
        status=SlotStatus.MATCH,
        serial_bdr="SN-1",
        serial_rings="SN-1",
        ring_mac="AA",
        ring_name="RingA",
        product="PRO",
        firmware_version="1.0",
        bdr_payload=bdr,
        rings_payload=rings,
    )
    result = ValidationEngine().validate_slot(slot)
    assert result.valid is False
    issue = _find(result, ValidationCode.IDENTITY_FIELD_MISMATCH)
    assert issue is not None
    assert issue.severity is Severity.ERROR


def test_unknown_slot_state_is_error():
    slot = _slot(state="BOGUS")
    result = ValidationEngine().validate_slot(slot)
    assert result.valid is False
    assert _find(result, ValidationCode.INVALID_SLOT_STATE) is not None


def test_unknown_step_is_error():
    slot = _slot(state="BDR_RUNNING", step="WEIRD")
    result = ValidationEngine().validate_slot(slot)
    assert result.valid is False
    assert _find(result, ValidationCode.INVALID_SLOT_STATE) is not None


def test_invalid_state_combination_is_error():
    slot = _slot(state="PASSED", step="IN_PROGRESS")
    result = ValidationEngine().validate_slot(slot)
    assert result.valid is False
    issue = _find(result, ValidationCode.INVALID_STATE_COMBINATION)
    assert issue is not None
    assert issue.severity is Severity.ERROR


@pytest.mark.parametrize(
    ("state", "step"),
    [
        ("ASSIGNED", "QUEUED"),
        ("BDR_RUNNING", "IN_PROGRESS"),
        ("PASSED", "COMPLETED"),
        ("FAILED", "FAILED"),
    ],
)
def test_valid_state_combinations_pass(state, step):
    result = ValidationEngine().validate_slot(_slot(state=state, step=step))
    assert result.valid is True
    assert _find(result, ValidationCode.INVALID_STATE_COMBINATION) is None


def test_observations_are_never_modified():
    engine = ValidationEngine()
    slots = (_slot(key="1"), _slot(key="2", status=SlotStatus.MISMATCH))
    observation = _machine(slots=slots)
    batch = ObservationBatch(machines=(observation,))
    before = repr(observation)
    engine.validate(batch)
    assert repr(observation) == before


def test_aggregate_counts_across_batch():
    machine_a = _machine(slots=(_slot(key="1"),))
    machine_b = _machine(
        bdr_state=_state(fresh=False),
        rings_state=_state(fresh=False),
        slots=(_slot(key="2", status=SlotStatus.MISMATCH), _slot(key="3", status=SlotStatus.RINGS_ONLY)),
    )
    batch = ObservationBatch(machines=(machine_a, machine_b))
    result = ValidationEngine().validate(batch)
    assert result.valid is False
    assert result.machine_count == 2
    assert result.slot_count == 3
    assert result.error_count == 2  # MACHINE_STALE + SLOT_SERIAL_MISMATCH
    assert result.warning_count == 1  # SLOT_ONE_SOURCE_ONLY
    assert result.by_machine["aqc-03"].valid is False
    assert result.machines[0].slots[0].valid is True


def test_validate_slot_public_api():
    slot = _slot()
    result = ValidationEngine().validate_slot(slot)
    assert result.slot_key == "1"
    assert isinstance(result.issues, tuple)


def test_golden_fixture_machine_active_valid():
    fx = load_fixture("machine_active")
    obs = build_machine_observation("aqc-03", fx.bdr, fx.rings, _state(), _state())
    result = ValidationEngine().validate_machine(obs)
    assert result.valid is True
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.slot_count == 4


def test_golden_fixture_one_source_mismatch_warns():
    fx = load_fixture("one_source_mismatch")
    obs = build_machine_observation("aqc-03", fx.bdr, fx.rings, _state(), _state())
    result = ValidationEngine().validate_machine(obs)
    assert result.valid is True
    issue = _find(result, ValidationCode.SLOT_ONE_SOURCE_ONLY)
    assert issue is not None
    assert issue.slot_key == "5"
    assert result.warning_count >= 1


def test_golden_fixture_offline_machine_stale():
    fx = load_fixture("machine_offline")
    obs = build_machine_observation(
        "aqc-03", fx.bdr, fx.rings, _state(fresh=False), _state(fresh=False)
    )
    result = ValidationEngine().validate_machine(obs)
    assert result.valid is False
    assert _find(result, ValidationCode.MACHINE_STALE) is not None


@pytest.mark.parametrize("fixture_name", ["ring_passed", "ring_failed", "ring_assigned"])
def test_golden_state_fixtures_have_valid_state_combinations(fixture_name):
    fx = load_fixture(fixture_name)
    obs = build_machine_observation("aqc-03", fx.bdr, fx.rings, _state(), _state())
    result = ValidationEngine().validate_machine(obs)
    assert _find(result, ValidationCode.INVALID_SLOT_STATE) is None
    assert _find(result, ValidationCode.INVALID_STATE_COMBINATION) is None


def test_machine_issues_and_slot_issues_are_public():
    obs = _machine(rings_state=_state(present=False))
    assert any(i.code is ValidationCode.SOURCE_MISSING for i in machine_issues(obs))
    assert slot_issues(_slot(status=SlotStatus.MISMATCH))
