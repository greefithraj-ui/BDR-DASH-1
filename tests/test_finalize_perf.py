"""Performance bounds for the Removal Finalization Engine (Sprint 2, Task 7).

Synthetic pass: 100 machines x 10 slots tracked (seeded by the Collector State
Engine), taken through three consecutive absent cycles by the Removal Candidate
Engine into PENDING_REMOVAL, then one fresh empty observation past the grace
window is consumed by the Removal Finalization Engine. Measures the 5 KPIs for
the Task 7 Performance Report -- query count, rows read, rows written, peak
memory, and finalization time. Bounds are generous for CI-class hardware.
"""

import time
import tracemalloc

from datetime import datetime, timedelta, timezone

from bic.diff import SmartUpdateEngine
from bic.finalize import RemovalFinalizationEngine
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


def test_finalization_performance_within_bounds(scratch_schema):
    machine_count = 100
    slot_count = 10
    total = machine_count * slot_count

    empty = ObservationBatch(machines=(), generated_at=SESSION)
    batch = _bulk_batch(machine_count, slot_count, SESSION)
    a1 = _bulk_batch(machine_count, 0, SESSION + TICK)
    a2 = _bulk_batch(machine_count, 0, SESSION + 2 * TICK)
    a3 = _bulk_batch(machine_count, 0, SESSION + 3 * TICK)
    fin = _bulk_batch(machine_count, 0, a3.generated_at + timedelta(seconds=121))

    state_engine = CollectorStateEngine(scratch_schema)
    state_engine.apply(DIFF.diff(empty, batch), batch)

    removal_engine = RemovalCandidateEngine(scratch_schema)
    removal_engine.apply(DIFF.diff(batch, a1), a1)
    removal_engine.apply(DIFF.diff(a1, a2), a2)
    result = removal_engine.apply(DIFF.diff(a2, a3), a3)
    assert result.candidates_confirmed == total  # every ring now PENDING_REMOVAL

    finalize_engine = RemovalFinalizationEngine(scratch_schema)
    tracemalloc.start()
    start = time.perf_counter()
    result = finalize_engine.apply(DIFF.diff(a3, fin), fin)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)
    print(
        f"\nfinalize perf: machines={result.machine_count} "
        f"finalized={result.rows_finalized} queries={result.query_count} "
        f"rows_read={result.rows_read} rows_written={result.rows_written} "
        f"time={elapsed_ms:.1f}ms peak_alloc={peak_mb:.1f}MB"
    )

    assert result.machine_count == machine_count
    assert result.has_errors is False
    assert result.rows_finalized == total
    assert result.history_rows == total
    assert result.event_rows == total
    assert result.deleted_rows == total
    assert result.query_count == machine_count * 5  # lock+select+hist+event+del
    assert result.rows_read == total
    assert result.rows_written == total * 3  # history + event + active delete
    assert elapsed_ms < 15000, f"finalize apply too slow: {elapsed_ms:.1f}ms"
    assert peak_mb < 300, f"finalize apply allocated too much: {peak_mb:.1f}MB"
