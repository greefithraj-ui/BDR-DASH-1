"""Unit tests for bic.reader pure logic (Sprint 2, Task 2). No database required."""

import pytest

from bic.config import FRESHNESS_WINDOW_SECONDS
from bic.reader import (
    DEFAULT_BDR_TABLE,
    DEFAULT_RINGS_TABLE,
    SlotStatus,
    SourceState,
    build_machine_observation,
    extract_slots,
    is_fresh,
    is_occupied_serial,
    validate_table_ref,
)
from tests.fixture_loader import load_fixture


def _fresh_state(present=True, parse_error=None):
    return SourceState(
        present=present,
        downloaded_at=None,
        age_seconds=5.0,
        fresh=present,
        parse_error=parse_error,
    )


def _stale_state(present=True):
    return SourceState(present=present, age_seconds=300.0, fresh=False)


def test_default_tables_are_the_approved_live_tables():
    assert DEFAULT_RINGS_TABLE == "public.live_rings_raw"
    assert DEFAULT_BDR_TABLE == "public.live_bdr_raw"


def test_slot_status_values_frozen():
    assert tuple(s.value for s in SlotStatus) == (
        "MATCH",
        "MISMATCH",
        "BDR_ONLY",
        "RINGS_ONLY",
    )


def test_validate_table_ref_accepts_approved_public_tables():
    assert validate_table_ref("public.live_rings_raw") == "public.live_rings_raw"
    assert validate_table_ref("public.live_bdr_raw") == "public.live_bdr_raw"


def test_validate_table_ref_rejects_unsafe_refs():
    for ref in (
        "live_rings_raw",
        "public",
        "public.live_rings_raw; DROP TABLE x",
        "public.TABLE",
        "public.tab le",
        "9schema.x",
        "a.b.c",
        "public-1.x",
    ):
        with pytest.raises(ValueError):
            validate_table_ref(ref)


def test_is_fresh_rules():
    assert is_fresh(0.0, 60.0)
    assert is_fresh(59.9, 60.0)
    assert not is_fresh(60.1, 60.0)
    assert not is_fresh(None, 60.0)
    assert not is_fresh(5.0, None)


def test_freshness_threshold_defaults_to_frozen_spec():
    assert FRESHNESS_WINDOW_SECONDS == 60


def test_is_occupied_serial_rules():
    assert is_occupied_serial("RP-CH3-P18-WD-PG07-0005555")
    assert not is_occupied_serial("--")
    assert not is_occupied_serial("N/A")
    assert not is_occupied_serial("")
    assert not is_occupied_serial("   ")
    assert not is_occupied_serial(None)
    assert not is_occupied_serial(12345)


def test_extract_slots_nested_bdr_shape():
    payload = load_fixture("machine_active").bdr
    slots = extract_slots(payload)
    assert set(slots) == {"1", "2", "3", "4"}


def test_extract_slots_flat_rings_shape():
    payload = load_fixture("machine_active").rings
    assert extract_slots(payload) == payload


def test_extract_slots_strips_session_metadata():
    payload = {"session_id": "abc", "1": {"serial_number": "X"}}
    assert extract_slots(payload) == {"1": {"serial_number": "X"}}


def test_extract_slots_empty_payloads():
    assert extract_slots({}) == {}
    assert extract_slots({"saved_at": "2026-01-01", "slots": {}}) == {}
    assert extract_slots(None) == {}
    assert extract_slots([]) == {}


def test_machine_active_all_slots_match():
    fx = load_fixture("machine_active")
    obs = build_machine_observation(
        "aqc-03", fx.bdr, fx.rings, _fresh_state(), _fresh_state()
    )
    assert obs.machine_name == "aqc-03"
    assert len(obs.slots) == 4
    assert all(slot.status is SlotStatus.MATCH for slot in obs.slots)
    assert obs.has_mismatch is False
    assert obs.fresh is True
    assert obs.slot_map["1"].serial_number == "RP-CH3-P18-WD-PG07-0005555"
    assert obs.slot_map["1"].ring_mac == "AA:11:22:33:44:55"
    assert obs.slot_map["1"].ring_name == "UH_AA1122334455"
    assert obs.slot_map["1"].product == "PRO"
    assert obs.slot_map["1"].firmware_version == "05.24.34.52"


def test_one_source_mismatch_flags_rings_only_slot():
    fx = load_fixture("one_source_mismatch")
    obs = build_machine_observation(
        "aqc-03", fx.bdr, fx.rings, _fresh_state(), _fresh_state()
    )
    assert [slot.slot_key for slot in obs.slots] == ["1", "2", "3", "5"]
    assert obs.slot_map["1"].status is SlotStatus.MATCH
    assert obs.slot_map["5"].status is SlotStatus.RINGS_ONLY
    assert obs.slot_map["5"].serial_bdr is None
    assert obs.slot_map["5"].serial_rings == "RP-CH3-P18-WD-PA09-0008515"
    assert obs.has_mismatch is True


def test_serial_conflict_is_mismatch():
    bdr = {"slots": {"1": {"serial_number": "SERIAL-A", "ring_name": "R1"}}}
    rings = {"1": {"serial_number": "SERIAL-B", "ring_name": "R1"}}
    obs = build_machine_observation("aqc-03", bdr, rings, _fresh_state(), _fresh_state())
    slot = obs.slot_map["1"]
    assert slot.status is SlotStatus.MISMATCH
    assert slot.serial_bdr == "SERIAL-A"
    assert slot.serial_rings == "SERIAL-B"
    assert slot.serial_number == "SERIAL-B"
    assert obs.has_mismatch is True


def test_bdr_only_slot():
    bdr = {"slots": {"1": {"serial_number": "SERIAL-A"}}}
    obs = build_machine_observation("aqc-03", bdr, {}, _fresh_state(), _fresh_state())
    assert obs.slot_map["1"].status is SlotStatus.BDR_ONLY
    assert obs.has_mismatch is True


def test_rings_only_slot():
    rings = {"1": {"serial_number": "SERIAL-A"}}
    obs = build_machine_observation("aqc-03", {}, rings, _fresh_state(), _fresh_state())
    assert obs.slot_map["1"].status is SlotStatus.RINGS_ONLY
    assert obs.has_mismatch is True


def test_bdr_absent_entirely():
    obs = build_machine_observation("aqc-03", None, {"1": {"serial_number": "X"}}, SourceState(present=False), _fresh_state())
    assert obs.bdr.present is False
    assert obs.rings.present is True
    assert obs.fresh is True
    assert obs.slot_map["1"].status is SlotStatus.RINGS_ONLY


def test_placeholder_serial_skipped():
    bdr = {
        "slots": {
            "1": {"serial_number": "--"},
            "2": {"serial_number": "SERIAL-2"},
        }
    }
    rings = {"1": {"serial_number": "SERIAL-1"}}
    obs = build_machine_observation("aqc-03", bdr, rings, _fresh_state(), _fresh_state())
    assert set(obs.slot_map) == {"1", "2"}
    assert obs.slot_map["1"].status is SlotStatus.RINGS_ONLY
    assert obs.slot_map["2"].status is SlotStatus.BDR_ONLY


def test_empty_machine_has_no_slots():
    fx = load_fixture("machine_empty")
    obs = build_machine_observation("aqc-03", fx.bdr, fx.rings, _fresh_state(), _fresh_state())
    assert obs.slots == ()
    assert obs.has_mismatch is False
    assert obs.fresh is True


def test_machine_freshness_from_source_states():
    obs = build_machine_observation(
        "aqc-03",
        {"slots": {}},
        {"slots": {}},
        _stale_state(),
        _fresh_state(),
    )
    assert obs.fresh is True
    both_stale = build_machine_observation(
        "aqc-03", {"slots": {}}, {"slots": {}}, _stale_state(), _stale_state()
    )
    assert both_stale.fresh is False


def test_parse_error_is_surfaceable_on_source_state():
    obs = build_machine_observation(
        "aqc-03",
        None,
        {},
        SourceState(present=True, age_seconds=5.0, fresh=True, parse_error="invalid JSON: x"),
        _fresh_state(),
    )
    assert obs.bdr.parse_error is not None
    assert obs.fresh is True
