"""Removal Finalization Engine (Sprint 2, Task 7).

Finalizes removal candidates once BOTH approved conditions are met:

* ``REMOVAL_CONFIRMATIONS`` (3) confirmed absent observations -- the ring's
  ``active_rings`` row must already be in ``PENDING_REMOVAL`` (maintained by the
  Removal Candidate Engine, Sprint 2 Task 6) with ``removal_confirmations`` at
  or above the threshold, AND
* the ``REMOVAL_GRACE_SECONDS`` (120) grace period must have elapsed since
  ``removal_first_absent_at``, measured against the observation stream's own
  timestamps (``current_batch.generated_at``) -- never the wall clock.

A finalized ring is moved OUT of ``active_rings`` into ``ring_history``
(``end_reason = 'REMOVED'``), removed from ``active_rings``, and recorded with a
``FINALIZED`` event in ``ring_events`` -- all in ONE per-machine transaction.
The ring is never classified as a replacement; replacement classification is a
later task. A machine that is offline or stale suspends finalization, and a ring
present in the current observation is never finalized.

The collector processes a MONOTONICALLY ADVANCING observation stream and is NOT
intended for duplicate-batch replay: the confirmation counters (Task 6) count
applies and the grace check compares the current observation timestamp against
the recorded first-absence timestamp. If replay support is ever required it must
be implemented as a dedicated replay adapter that feeds replayed observations
through the same pipeline, never by changing the collector semantics.

Determinism: the engine never reads the wall clock. Every timestamp written
(finalized_at, archived_at, occurred_at, recorded_at) is taken verbatim from
``current_batch.generated_at``, so identical inputs applied against an identical
database produce identical writes. Finalization is end-state idempotent: a
finalized ring's row is gone, so reapplying the same batch finalizes nothing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Mapping

try:
    import psycopg2

    HAS_PSYCOPG2 = True
except ImportError:  # pragma: no cover - only reached when psycopg2 is absent
    psycopg2 = None
    HAS_PSYCOPG2 = False

from bic.config import REMOVAL_GRACE_SECONDS
from bic.db import BicDatabase
from bic.diff import DiffResult
from bic.reader import MachineObservation, ObservationBatch
from bic.removal import validate_confirmations
from bic.schema import END_REASONS, EVENT_TYPES
from bic.state import (
    RingLifecycleState,
    RowState,
    _SELECT_ACTIVE_SQL,
    _multi_values_params,
    occupied_slots,
    validate_apply_inputs,
)

FINALIZATION_END_REASON = "REMOVED"
FINALIZATION_EVENT_TYPE = "FINALIZED"
FINALIZATION_SOURCE = "collector"
COLLECTOR_VERSION = "1.0.0"

assert FINALIZATION_END_REASON in END_REASONS
assert FINALIZATION_EVENT_TYPE in EVENT_TYPES


# ── Object model ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FinalizeOp:
    """One finalized ring: ring_history row + ring_events row + active delete."""

    row_id: int
    ring_id: int
    machine_name: str
    slot_key: str
    serial_number: str
    first_seen_at: datetime
    last_seen_at: datetime
    state_history: str
    decision_summary: str
    firmware_version: str | None
    finalized_at: datetime


@dataclass(frozen=True)
class MachineFinalizePlan:
    """Pure reconciliation result for one machine's finalizations."""

    machine_name: str
    finalized: tuple[FinalizeOp, ...] = field(default_factory=tuple)
    suspended: bool = False


@dataclass(frozen=True)
class FinalizeMachineStats:
    """Per-machine accounting for one finalization apply pass."""

    machine_name: str
    rows_finalized: int
    history_rows: int
    event_rows: int
    deleted_rows: int
    suspended: bool
    queries: int
    rows_read: int
    rows_written: int
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass(frozen=True)
class FinalizeApplyResult:
    """Aggregate result of one finalization apply pass."""

    session: datetime | None
    stats: tuple[FinalizeMachineStats, ...] = field(default_factory=tuple)

    @property
    def machine_count(self) -> int:
        return len(self.stats)

    @property
    def query_count(self) -> int:
        return sum(stat.queries for stat in self.stats)

    @property
    def rows_read(self) -> int:
        return sum(stat.rows_read for stat in self.stats)

    @property
    def rows_written(self) -> int:
        return sum(stat.rows_written for stat in self.stats)

    @property
    def rows_finalized(self) -> int:
        return sum(stat.rows_finalized for stat in self.stats)

    @property
    def history_rows(self) -> int:
        return sum(stat.history_rows for stat in self.stats)

    @property
    def event_rows(self) -> int:
        return sum(stat.event_rows for stat in self.stats)

    @property
    def deleted_rows(self) -> int:
        return sum(stat.deleted_rows for stat in self.stats)

    @property
    def suspended_machines(self) -> int:
        return sum(1 for stat in self.stats if stat.suspended)

    @property
    def has_errors(self) -> bool:
        return any(stat.has_errors for stat in self.stats)

    @property
    def by_machine(self) -> dict[str, FinalizeMachineStats]:
        return {stat.machine_name: stat for stat in self.stats}


# ── Pure reconciliation (no database access) ────────────────────────────────


def validate_grace(grace: timedelta | None) -> timedelta:
    """Return the grace window or raise on invalid values."""
    if grace is None:
        return timedelta(seconds=REMOVAL_GRACE_SECONDS)
    if not isinstance(grace, timedelta):
        raise ValueError("grace must be a timedelta")
    if grace < timedelta(0):
        raise ValueError("grace must be non-negative")
    return grace


def eligible_for_finalization(
    row: RowState,
    session: datetime,
    confirmations: int,
    grace: timedelta,
) -> bool:
    """Both approved conditions: confirmations reached AND grace elapsed."""
    if row.lifecycle_state != RingLifecycleState.PENDING_REMOVAL.value:
        return False
    if row.removal_confirmations < confirmations:
        return False
    if row.removal_first_absent_at is None:
        return False
    return session >= row.removal_first_absent_at + grace


def _json_dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _iso(value: datetime) -> str:
    """Canonical UTC ISO-8601 so JSON stays stable across DB timezones."""
    return value.astimezone(timezone.utc).isoformat()


def _build_op(
    row: RowState, session: datetime, confirmations: int, grace: timedelta
) -> FinalizeOp:
    state_history = _json_dump(
        [
            {
                "state": RingLifecycleState.OBSERVED.value,
                "changed_at": _iso(row.first_seen_at),
            },
            {
                "state": RingLifecycleState.PENDING_REMOVAL.value,
                "changed_at": _iso(row.state_changed_at),
            },
        ]
    )
    decision_summary = _json_dump(
        {
            "end_reason": FINALIZATION_END_REASON,
            "removal_confirmations": row.removal_confirmations,
            "confirmation_threshold": confirmations,
            "grace_seconds": int(grace.total_seconds()),
            "first_absent_at": _iso(row.removal_first_absent_at),
            "finalized_at": _iso(session),
        }
    )
    return FinalizeOp(
        row_id=row.id,
        ring_id=row.ring_id,
        machine_name=row.machine_name,
        slot_key=row.slot_key,
        serial_number=row.serial_number,
        first_seen_at=row.first_seen_at,
        last_seen_at=row.last_seen_at,
        state_history=state_history,
        decision_summary=decision_summary,
        firmware_version=row.firmware_version,
        finalized_at=session,
    )


def plan_finalization(
    machine_name: str,
    observation: MachineObservation | None,
    rows: Mapping[str, RowState],
    session: datetime,
    confirmations: int,
    grace: timedelta,
) -> MachineFinalizePlan:
    """Compute finalization ops for one machine's active_rings.

    A ring is finalized only when its row is ``PENDING_REMOVAL``, its
    confirmation counter is at the threshold, the grace period has elapsed since
    its first absence, AND it is still absent from the current observation.
    Offline or stale machines suspend the whole pass.
    """
    if observation is None or not observation.fresh:
        return MachineFinalizePlan(machine_name=machine_name, suspended=True)

    present_serials = set(occupied_slots(observation).values())

    ops: list[FinalizeOp] = []
    for slot_key in sorted(rows):
        row = rows[slot_key]
        if row.serial_number in present_serials:
            continue
        if not eligible_for_finalization(row, session, confirmations, grace):
            continue
        ops.append(_build_op(row, session, confirmations, grace))

    return MachineFinalizePlan(machine_name=machine_name, finalized=tuple(ops))


# ── SQL ─────────────────────────────────────────────────────────────────────

_INSERT_HISTORY_SQL = """
INSERT INTO ring_history
    (ring_id, machine_name, slot_key, serial_number, state_history,
     decision_summary, first_seen_at, last_seen_at, finalized_at,
     end_reason, firmware_version, collector_version, archived_at)
VALUES %s
"""

_INSERT_EVENT_SQL = """
INSERT INTO ring_events
    (ring_id, machine_name, slot_key, event_type, occurred_at, recorded_at,
     payload, reason, collector_version, source)
VALUES %s
"""

_DELETE_ACTIVE_SQL = "DELETE FROM active_rings WHERE id = ANY(%s)"


# ── Engine ──────────────────────────────────────────────────────────────────


class RemovalFinalizationEngine:
    """Moves confirmed removals out of active_rings into ring_history.

    Consumes a DiffResult together with the current ObservationBatch, processes
    each machine in its own transaction under the shared advisory lock, and for
    every eligible ring inserts its ring_history row, inserts its FINALIZED
    ring_events row, and deletes its active_rings row -- all-or-nothing.
    """

    def __init__(
        self,
        db: BicDatabase,
        *,
        confirmations: int | None = None,
        grace: timedelta | None = None,
    ) -> None:
        if not HAS_PSYCOPG2:
            raise RuntimeError(
                "psycopg2-binary is not installed; RemovalFinalizationEngine "
                "requires it"
            )
        self._db = db
        self._confirmations = validate_confirmations(confirmations)
        self._grace = validate_grace(grace)
        self.current_session: ObservationBatch | None = None
        self.last_result: FinalizeApplyResult | None = None

    def apply(
        self, diff_result: DiffResult, current_batch: ObservationBatch
    ) -> FinalizeApplyResult:
        """Consume a diff + current batch and finalize eligible removals."""
        session = validate_apply_inputs(diff_result, current_batch)
        self.current_session = current_batch

        conn = self._db.get_connection()
        try:
            stats: list[FinalizeMachineStats] = []
            for machine_name in sorted(current_batch.by_machine):
                try:
                    stat = self._apply_machine(
                        conn,
                        machine_name,
                        current_batch.by_machine[machine_name],
                        session,
                    )
                except psycopg2.Error as exc:  # noqa: BLE001 - per-machine isolation
                    conn.rollback()
                    stat = FinalizeMachineStats(
                        machine_name=machine_name,
                        rows_finalized=0,
                        history_rows=0,
                        event_rows=0,
                        deleted_rows=0,
                        suspended=False,
                        queries=0,
                        rows_read=0,
                        rows_written=0,
                        errors=(f"database error: {exc}",),
                    )
                stats.append(stat)
        finally:
            conn.close()

        self.last_result = FinalizeApplyResult(
            session=session, stats=tuple(stats)
        )
        return self.last_result

    def _apply_machine(
        self,
        conn,
        machine_name: str,
        observation: MachineObservation,
        session: datetime,
    ) -> FinalizeMachineStats:
        queries = 0
        rows_read = 0
        rows_written = 0

        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (self._lock_key(),))
            queries += 1

            cur.execute(_SELECT_ACTIVE_SQL, (machine_name,))
            queries += 1
            active_rows = cur.fetchall()
            rows_read += len(active_rows)
            rows_by_slot: dict[str, RowState] = {
                row[3]: RowState(*row) for row in active_rows
            }

            plan = plan_finalization(
                machine_name,
                observation,
                rows_by_slot,
                session,
                self._confirmations,
                self._grace,
            )

            if plan.finalized:
                history_rows = [
                    (
                        op.ring_id,
                        machine_name,
                        op.slot_key,
                        op.serial_number,
                        op.state_history,
                        op.decision_summary,
                        op.first_seen_at,
                        op.last_seen_at,
                        op.finalized_at,
                        FINALIZATION_END_REASON,
                        op.firmware_version,
                        COLLECTOR_VERSION,
                        op.finalized_at,
                    )
                    for op in plan.finalized
                ]
                placeholders, params = _multi_values_params(history_rows)
                cur.execute(
                    _INSERT_HISTORY_SQL.replace("VALUES %s", f"VALUES {placeholders}"),
                    params,
                )
                queries += 1
                rows_written += len(history_rows)

                event_rows = [
                    (
                        op.ring_id,
                        machine_name,
                        op.slot_key,
                        FINALIZATION_EVENT_TYPE,
                        op.finalized_at,
                        op.finalized_at,
                        op.decision_summary,
                        FINALIZATION_END_REASON,
                        COLLECTOR_VERSION,
                        FINALIZATION_SOURCE,
                    )
                    for op in plan.finalized
                ]
                placeholders, params = _multi_values_params(event_rows)
                cur.execute(
                    _INSERT_EVENT_SQL.replace("VALUES %s", f"VALUES {placeholders}"),
                    params,
                )
                queries += 1
                rows_written += len(event_rows)

                cur.execute(
                    _DELETE_ACTIVE_SQL,
                    ([op.row_id for op in plan.finalized],),
                )
                queries += 1
                rows_written += len(plan.finalized)

            conn.commit()

        return FinalizeMachineStats(
            machine_name=machine_name,
            rows_finalized=len(plan.finalized),
            history_rows=len(plan.finalized) if plan.finalized else 0,
            event_rows=len(plan.finalized) if plan.finalized else 0,
            deleted_rows=len(plan.finalized) if plan.finalized else 0,
            suspended=plan.suspended,
            queries=queries,
            rows_read=rows_read,
            rows_written=rows_written,
        )

    def _lock_key(self) -> int:
        # MUST match CollectorStateEngine._lock_key so a state pass, a removal
        # pass, and a finalization pass serialize on the same advisory lock.
        digest = hashlib.sha256(
            f"bic:collector-state:{self._db.config.schema}".encode("utf-8")
        ).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)
