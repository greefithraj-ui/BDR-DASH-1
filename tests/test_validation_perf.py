"""Performance bounds for the Validation Engine (Sprint 2, Task 3).

Synthetic batch of 500 machines x 20 slots = 10,000 slot observations. Bounds
are intentionally generous so the test is stable on CI-class hardware; the
measured numbers feed the Sprint 2 Task 3 Performance Report.
"""

import time
import tracemalloc

from bic.reader import MachineObservation, ObservationBatch, SlotObservation, SlotStatus, SourceState
from bic.validation import ValidationEngine


def _bulk_slot(machine, key):
    serial = f"SN-{key}"
    bdr = {
        "serial_number": serial,
        "ring_mac": "AA:BB",
        "ring_name": "RingA",
        "product": "PRO",
        "state": "BDR_RUNNING",
    }
    rings = {
        "serial_number": serial,
        "ring_mac": "AA:BB",
        "ring_name": "RingA",
        "product": "PRO",
        "state": "BDR_RUNNING",
        "step_statuses": {"BDR_TEST": "IN_PROGRESS"},
    }
    return SlotObservation(
        machine_name=machine,
        slot_key=str(key),
        status=SlotStatus.MATCH,
        serial_bdr=serial,
        serial_rings=serial,
        ring_mac="AA:BB",
        ring_name="RingA",
        product="PRO",
        firmware_version="1.0",
        bdr_payload=bdr,
        rings_payload=rings,
    )


def _bulk_machine(machine, slot_count):
    state = SourceState(present=True, age_seconds=5.0, fresh=True)
    slots = tuple(_bulk_slot(machine, key) for key in range(slot_count))
    return MachineObservation(
        machine_name=machine, bdr=state, rings=state, slots=slots
    )


def test_validation_performance_within_bounds():
    machines = tuple(_bulk_machine(f"aqc-{index:03d}", 20) for index in range(500))
    batch = ObservationBatch(machines=machines)

    engine = ValidationEngine()
    tracemalloc.start()
    start = time.perf_counter()
    result = engine.validate(batch)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    print(
        f"\nvalidation perf: machines={result.machine_count} "
        f"slots={result.slot_count} time={elapsed_ms:.1f}ms "
        f"peak_alloc={peak_mb:.1f}MB"
    )

    assert result.valid is True
    assert result.machine_count == 500
    assert result.slot_count == 10_000
    assert result.error_count == 0
    assert result.warning_count == 0
    assert elapsed_ms < 5000, f"validation too slow: {elapsed_ms:.1f}ms"
    assert peak_mb < 200, f"validation allocated too much: {peak_mb:.1f}MB"
