"""Lock the documented facts of the BIC golden fixture corpus (Sprint 1, T1.4).

Every assertion here corresponds to a row of tests/fixtures/README.md, so a
fixture cannot silently drift from its stated purpose.
"""

from datetime import datetime

from tests.fixture_loader import load_fixture, list_fixtures

FRESH_SAVED_AT = "2026-08-01T10:00:00.000000+05:30"
STALE_SAVED_AT = "2026-08-01T08:00:00.000000+05:30"

FRESH_FIXTURES = (
    "machine_active",
    "machine_empty",
    "ring_passed",
    "ring_failed",
    "ring_assigned",
    "ring_bdr_running",
    "replacement",
    "removal_pending",
    "one_source_mismatch",
)

OFFLINE_FIXTURES = ("machine_offline", "removal_offline")

EXPECTED_FIXTURES = FRESH_FIXTURES + OFFLINE_FIXTURES + ("machine_empty_bdr_absent",)


def ring_serials(fx):
    return {slot: entry["serial_number"] for slot, entry in fx.rings.items()}


def bdr_serials(fx):
    return {
        slot: entry["serial_number"] for slot, entry in fx.bdr["slots"].items()
    }


def ring_states(fx):
    return {slot: entry["state"] for slot, entry in fx.rings.items()}


def test_corpus_contains_every_documented_fixture():
    assert list_fixtures() == tuple(sorted(EXPECTED_FIXTURES))


def test_every_fixture_loads_with_rings_payload():
    for name in EXPECTED_FIXTURES:
        fx = load_fixture(name)
        assert fx.name == name
        assert isinstance(fx.rings, dict)


def test_machine_empty_bdr_absent_has_no_bdr_payload():
    assert load_fixture("machine_empty_bdr_absent").bdr is None


def test_bdr_payload_shape_and_iso_saved_at():
    for name in EXPECTED_FIXTURES:
        fx = load_fixture(name)
        if fx.bdr is None:
            continue
        assert isinstance(fx.bdr["saved_at"], str)
        parsed = datetime.fromisoformat(fx.bdr["saved_at"])
        assert parsed.tzinfo is not None
        assert isinstance(fx.bdr["slots"], dict)


def test_fresh_fixtures_use_documented_saved_at():
    for name in FRESH_FIXTURES:
        assert load_fixture(name).bdr["saved_at"] == FRESH_SAVED_AT


def test_offline_fixtures_use_stale_saved_at():
    for name in OFFLINE_FIXTURES:
        assert load_fixture(name).bdr["saved_at"] == STALE_SAVED_AT


def test_every_occupied_ring_has_full_identity_fields():
    for name in EXPECTED_FIXTURES:
        for slot, entry in load_fixture(name).rings.items():
            for field in (
                "serial_number",
                "product",
                "ring_mac",
                "ring_name",
                "state",
            ):
                assert field in entry, f"{name}/{slot} missing {field}"


def test_bdr_slots_agree_with_rings_on_identity():
    for name in EXPECTED_FIXTURES:
        fx = load_fixture(name)
        if fx.bdr is None:
            continue
        for slot, serial in bdr_serials(fx).items():
            assert slot in fx.rings, f"{name}: bdr slot {slot} missing from rings"
            assert (
                fx.rings[slot]["serial_number"] == serial
            ), f"{name}: serial mismatch on slot {slot}"


def test_machine_active_all_running():
    fx = load_fixture("machine_active")
    assert set(fx.rings) == {"1", "2", "3", "4"}
    assert set(ring_states(fx).values()) == {"BDR_RUNNING"}


def test_machine_empty_both_payloads_empty():
    fx = load_fixture("machine_empty")
    assert fx.rings == {}
    assert fx.bdr["slots"] == {}


def test_ring_passed_slots_passed():
    fx = load_fixture("ring_passed")
    assert ring_states(fx)["2"] == "PASSED"
    assert ring_states(fx)["7"] == "PASSED"
    assert ring_states(fx)["11"] == "BDR_RUNNING"


def test_ring_failed_slot_failed():
    fx = load_fixture("ring_failed")
    assert ring_states(fx)["4"] == "FAILED"
    assert fx.rings["4"]["error"] is not None
    assert fx.rings["4"]["step_statuses"]["BDR_TEST"] == "FAILED"
    assert ring_states(fx)["6"] == "BDR_RUNNING"


def test_ring_assigned_slot_queued():
    fx = load_fixture("ring_assigned")
    assert ring_states(fx)["9"] == "ASSIGNED"
    assert fx.rings["9"]["queued_at"] is not None
    assert fx.rings["9"]["step_statuses"]["BDR_TEST"] == "QUEUED"
    assert ring_states(fx)["10"] == "BDR_RUNNING"


def test_ring_bdr_running_dead_slot():
    fx = load_fixture("ring_bdr_running")
    assert set(fx.rings) == {"1", "5", "8", "20", "30"}
    assert set(ring_states(fx).values()) == {"BDR_RUNNING"}
    assert fx.rings["1"]["dead_state"] == "BATTERY_DEAD"
    assert fx.rings["1"]["dead_confirm_passes"] == 1
    assert fx.rings["30"]["discharge_connect_failures"] == 1


def test_replacement_holds_documented_new_serial():
    fx = load_fixture("replacement")
    assert fx.rings["1"]["serial_number"] == "RP-CH3-P18-WD-PA10-0009999"
    assert fx.bdr["slots"]["1"]["serial_number"] == "RP-CH3-P18-WD-PA10-0009999"


def test_removal_pending_slot_absent_from_both_sources():
    fx = load_fixture("removal_pending")
    assert set(fx.rings) == {"1", "2"}
    assert set(fx.bdr["slots"]) == {"1", "2"}
    assert ring_serials(fx) == bdr_serials(fx)


def test_one_source_mismatch_slot_rings_only():
    fx = load_fixture("one_source_mismatch")
    assert "5" in fx.rings
    assert "5" not in fx.bdr["slots"]
    assert set(fx.bdr["slots"]) == {"1", "2", "3"}


def test_machine_offline_slots_present_but_stale():
    fx = load_fixture("machine_offline")
    assert set(fx.rings) == {"1", "2"}
    assert fx.bdr["saved_at"] == STALE_SAVED_AT


def test_removal_offline_slot_absent_and_stale():
    fx = load_fixture("removal_offline")
    assert set(fx.rings) == {"1", "2"}
    assert set(fx.bdr["slots"]) == {"1", "2"}
    assert fx.bdr["saved_at"] == STALE_SAVED_AT
