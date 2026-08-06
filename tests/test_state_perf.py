"""Performance bounds for the Collector State Engine (Sprint 2, Task 5).

Synthetic first-observation pass: 100 machines x 10 slots each = 1,000 new
rings. Measures the 5 KPIs for the Task 5 Performance Report -- query count,
rows read, rows written, peak memory, and processing time. Bounds are generous
for CI-class hardware.
"""

import time
import tracemalloc

from bic.diff import SmartUpdateEngine
from bic.reader import (
    MachineObservation,
    ObservationBatch,
    SlotObservation,
    SlotStatus,
    SourceState,
)
from bic.state import CollectorStateEngine

from datetime import datetime, timedelta, timezone

SESSION = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
DIFF = SmartUpdateEngine()


def _bulk_slot(machine, key):
    serial = f"SN-{machine}-{key:03d}"
    return SlotObservation(
        machine_name=machine,
        slot_key=str(key),
        status=SlotStatus.MATCH,
        serial_bdr=serial,
        serial_rings=serial,
        ring_mac=f"AA:BB:CC:{key:02d}:11:22",
        ring_name=f"RingA-{key}",
        product="PRO",
        firmware_version="1.0",
        bdr_payload={"serial_number": serial},
        rings_payload={"serial_number": serial},
    )


def _bulk_batch(machine_count, slot_count, at):
    machines = tuple(
        MachineObservation(
            machine_name=f"aqc-{index:03d}",
            bdr=SourceState(present=True, age_seconds=5.0, fresh=True),
            rings=SourceState(present=True, age_seconds=5.0, fresh=True),
            slots=tuple(
                _bulk_slot(f"aqc-{index:03d}", key) for key in range(slot_count)
            ),
        )
        for index in range(machine_count)
    )
    return ObservationBatch(machines=machines, generated_at=at)


def test_state_engine_performance_within_bounds(scratch_schema):
    machine_count = 100
    slot_count = 10
    empty = ObservationBatch(machines=(), generated_at=SESSION)
    batch = _bulk_batch(machine_count, slot_count, SESSION)
    diff = DIFF.diff(empty, batch)

    engine = CollectorStateEngine(scratch_schema)
    tracemalloc.start()
    start = time.perf_counter()
    result = engine.apply(diff, batch)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    print(
        f"\nstate perf: machines={result.machine_count} "
        f"rings={result.rows_inserted} queries={result.query_count} "
        f"rows_read={result.rows_read} rows_written={result.rows_written} "
        f"time={elapsed_ms:.1f}ms peak_alloc={peak_mb:.1f}MB"
    )

    assert result.machine_count == machine_count
    assert result.rows_inserted == machine_count * slot_count
    assert result.has_conflicts is False
    assert result.query_count <= machine_count * 6
    assert result.rows_read == 0
    assert result.rows_written == 2 * machine_count * slot_count
    assert elapsed_ms < 15000, f"state apply too slow: {elapsed_ms:.1f}ms"
    assert peak_mb < 300, f"state apply allocated too much: {peak_mb:.1f}MB"
