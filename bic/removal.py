"""Removal Candidate Engine (Sprint 2, Task 6).

Detects removal candidates in ``active_rings`` and maintains the pending-removal
state of the lifecycle ``OBSERVED -> TRACKING -> PENDING_REMOVAL -> FINALIZED``.

Task 6 scope is deliberately narrow:

* It counts consecutive absent observations for every tracked ring whose serial
  is absent from the current observation. The first absence records
  ``removal_first_absent_at`` and sets ``removal_confirmations = 1``; every
  following absence increments the counter; the third consecutive absence
  (``REMOVAL_CONFIRMATIONS``) promotes the ring to ``PENDING_REMOVAL``.
* A machine that is offline or stale (``MachineObservation.fresh`` is False)
  suspends confirmation: no increment, no reset, counters freeze.
* A ring that reappears cancels its candidate: ``removal_confirmations`` is
  reset to 0 and ``removal_first_absent_at`` to NULL, and a ``PENDING_REMOVAL``
  ring returns to ``OBSERVED``.
* It updates ONLY ``active_rings``. It NEVER writes ``ring_events``,
  ``ring_history``, ``machine_checkpoint``, or ``ring_identities``, NEVER
  finalizes a removal (no ``FINALIZED``, no ``end_reason``, no ``finalized_at``),
  and NEVER classifies an immediate serial replacement.

The 120-second grace period (``REMOVAL_GRACE_SECONDS``) is the guard for the
later finalization task, not for pending-state maintenance: this engine only
counts confirmations, records ``removal_first_absent_at`` (the candidate
timestamp a finalizer can compare against the grace window), and enters
``PENDING_REMOVAL`` at the third consecutive absence.

Absence is derived from the current ObservationBatch (authoritative) together
with the ``active_rings`` rows. The diff's REMOVED_RING_CANDIDATE only fires on
the first absent cycle (a multi-cycle-absent ring is in neither batch), so it is
not used for counting; the DiffResult is still required as an input so both
engines share the same apply contract and session validation.

The engine shares the Collector State Engine's advisory-lock key so a removal
pass and a state pass can never race on the same machine.

Determinism: like the Collector State Engine, this engine never reads the wall
clock. Every timestamp written is taken verbatim from
``current_batch.generated_at``. The confirmation counter counts APPLIES: each
distinct observation advances the counter, so reapplying the same batch is not
a supported operation -- the pipeline never replays a batch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

try:
    import psycopg2

    HAS_PSYCOPG2 = True
except ImportError:  # pragma: no cover - only reached when psycopg2 is absent
    psycopg2 = None
    HAS_PSYCOPG2 = False

from bic.config import REMOVAL_CONFIRMATIONS
from bic.db import BicDatabase
from bic.diff import DiffResult
from bic.reader import MachineObservation, ObservationBatch
from bic.state import (
    RingLifecycleState,
    RowState,
    _SELECT_ACTIVE_SQL,
    _multi_values_params,
    occupied_slots,
    validate_apply_inputs,
)


# ── Object model ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RemovalOp:
    """One active_rings update carrying the removal-tracking fields."""

    row_id: int
    serial_number: str
    slot_key: str
    lifecycle_state: str
    state_changed_at: datetime
    removal_confirmations: int
    removal_first_absent_at: datetime | None


@dataclass(frozen=True)
class MachineRemovalPlan:
    """Pure reconciliation result for one machine's removal candidates."""

    machine_name: str
    updates: tuple[RemovalOp, ...] = field(default_factory=tuple)
    suspended: bool = False
    candidates_started: int = 0
    candidates_confirmed: int = 0
    cancellations: int = 0


@dataclass(frozen=True)
class RemovalMachineStats:
    """Per-machine accounting for one removal apply pass."""

    machine_name: str
    rows_updated: int
    candidates_started: int
    candidates_confirmed: int
    cancellations: int
    suspended: bool
    queries: int
    rows_read: int
    rows_written: int
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


@dataclass(frozen=True)
class RemovalApplyResult:
    """Aggregate result of one removal apply pass."""

    session: datetime | None
    stats: tuple[RemovalMachineStats, ...] = field(default_factory=tuple)

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
    def rows_updated(self) -> int:
        return sum(stat.rows_updated for stat in self.stats)

    @property
    def candidates_started(self) -> int:
        return sum(stat.candidates_started for stat in self.stats)

    @property
    def candidates_confirmed(self) -> int:
        return sum(stat.candidates_confirmed for stat in self.stats)

    @property
    def cancellations(self) -> int:
        return sum(stat.cancellations for stat in self.stats)

    @property
    def suspended_machines(self) -> int:
        return sum(1 for stat in self.stats if stat.suspended)

    @property
    def has_errors(self) -> bool:
        return any(stat.has_errors for stat in self.stats)

    @property
    def by_machine(self) -> dict[str, RemovalMachineStats]:
        return {stat.machine_name: stat for stat in self.stats}


# ── Pure reconciliation (no database access) ────────────────────────────────


def validate_confirmations(value: int | None) -> int:
    """Return the confirmation threshold or raise on invalid values."""
    if value is None:
        return REMOVAL_CONFIRMATIONS
    if not isinstance(value, int) or value < 1:
        raise ValueError("confirmations must be a positive integer")
    return value


def reconcile_removals(
    machine_name: str,
    observation: MachineObservation | None,
    rows: Mapping[str, RowState],
    session: datetime,
    confirmations: int,
) -> MachineRemovalPlan:
    """Compute removal-tracking updates for one machine's active_rings.

    ``rows`` maps slot_key -> current active_rings row for the machine,
    ``session`` is the deterministic observation timestamp that stamps every
    write, and ``confirmations`` is the number of consecutive absent
    observations that promotes a ring to PENDING_REMOVAL.

    An offline or stale machine suspends the whole pass: no increment, no reset.
    """
    if observation is None or not observation.fresh:
        return MachineRemovalPlan(machine_name=machine_name, suspended=True)

    present_serials = set(occupied_slots(observation).values())

    updates: list[RemovalOp] = []
    started = 0
    confirmed = 0
    cancelled = 0

    for slot_key in sorted(rows):
        row = rows[slot_key]

        if row.serial_number in present_serials:
            if (
                row.removal_confirmations != 0
                or row.removal_first_absent_at is not None
            ):
                cancelled += 1
                if row.lifecycle_state == RingLifecycleState.PENDING_REMOVAL.value:
                    updates.append(
                        RemovalOp(
                            row_id=row.id,
                            serial_number=row.serial_number,
                            slot_key=row.slot_key,
                            lifecycle_state=RingLifecycleState.OBSERVED.value,
                            state_changed_at=session,
                            removal_confirmations=0,
                            removal_first_absent_at=None,
                        )
                    )
                else:
                    updates.append(
                        RemovalOp(
                            row_id=row.id,
                            serial_number=row.serial_number,
                            slot_key=row.slot_key,
                            lifecycle_state=row.lifecycle_state,
                            state_changed_at=row.state_changed_at,
                            removal_confirmations=0,
                            removal_first_absent_at=None,
                        )
                    )
            continue

        if row.lifecycle_state == RingLifecycleState.PENDING_REMOVAL.value:
            continue

        if row.removal_first_absent_at is None:
            new_confirmations = 1
            first_absent = session
            started += 1
        else:
            new_confirmations = min(row.removal_confirmations + 1, confirmations)
            first_absent = row.removal_first_absent_at

        if new_confirmations >= confirmations:
            state = RingLifecycleState.PENDING_REMOVAL.value
            state_changed = session
            confirmed += 1
        else:
            state = row.lifecycle_state
            state_changed = row.state_changed_at

        updates.append(
            RemovalOp(
                row_id=row.id,
                serial_number=row.serial_number,
                slot_key=row.slot_key,
                lifecycle_state=state,
                state_changed_at=state_changed,
                removal_confirmations=new_confirmations,
                removal_first_absent_at=first_absent,
            )
        )

    return MachineRemovalPlan(
        machine_name=machine_name,
        updates=tuple(updates),
        suspended=False,
        candidates_started=started,
        candidates_confirmed=confirmed,
        cancellations=cancelled,
    )


# ── SQL ─────────────────────────────────────────────────────────────────────

_UPDATE_REMOVAL_SQL = """
UPDATE active_rings AS ar
SET state = v.state,
    state_changed_at = v.state_changed_at,
    removal_confirmations = v.removal_confirmations,
    removal_first_absent_at = v.removal_first_absent_at,
    updated_at = v.updated_at
FROM (VALUES %s) AS v(row_id, state, state_changed_at, removal_confirmations,
                      removal_first_absent_at, updated_at)
WHERE ar.id = v.row_id
"""


# ── Engine ──────────────────────────────────────────────────────────────────


class RemovalCandidateEngine:
    """Counts consecutive absences and maintains PENDING_REMOVAL in active_rings.

    Mirrors the Collector State Engine's apply contract: consume a
    DiffResult together with the current ObservationBatch, process each machine
    in its own transaction under the shared advisory lock, and update ONLY the
    removal-tracking columns of ``active_rings``.
    """

    def __init__(
        self, db: BicDatabase, *, confirmations: int | None = None
    ) -> None:
        if not HAS_PSYCOPG2:
            raise RuntimeError(
                "psycopg2-binary is not installed; RemovalCandidateEngine "
                "requires it"
            )
        self._db = db
        self._confirmations = validate_confirmations(confirmations)
        self.current_session: ObservationBatch | None = None
        self.last_result: RemovalApplyResult | None = None

    def apply(
        self, diff_result: DiffResult, current_batch: ObservationBatch
    ) -> RemovalApplyResult:
        """Consume a diff + current batch and maintain removal candidate state."""
        session = validate_apply_inputs(diff_result, current_batch)
        self.current_session = current_batch

        conn = self._db.get_connection()
        try:
            stats: list[RemovalMachineStats] = []
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
                    stat = RemovalMachineStats(
                        machine_name=machine_name,
                        rows_updated=0,
                        candidates_started=0,
                        candidates_confirmed=0,
                        cancellations=0,
                        suspended=False,
                        queries=0,
                        rows_read=0,
                        rows_written=0,
                        errors=(f"database error: {exc}",),
                    )
                stats.append(stat)
        finally:
            conn.close()

        self.last_result = RemovalApplyResult(
            session=session, stats=tuple(stats)
        )
        return self.last_result

    def _apply_machine(
        self,
        conn,
        machine_name: str,
        observation: MachineObservation,
        session: datetime,
    ) -> RemovalMachineStats:
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

            plan = reconcile_removals(
                machine_name, observation, rows_by_slot, session, self._confirmations
            )

            if plan.updates:
                update_rows = [
                    (
                        op.row_id,
                        op.lifecycle_state,
                        op.state_changed_at,
                        op.removal_confirmations,
                        op.removal_first_absent_at,
                        session,
                    )
                    for op in plan.updates
                ]
                placeholders, params = _multi_values_params(update_rows)
                cur.execute(
                    _UPDATE_REMOVAL_SQL.replace("VALUES %s", f"VALUES {placeholders}"),
                    params,
                )
                queries += 1
                rows_written += len(plan.updates)

            conn.commit()

        return RemovalMachineStats(
            machine_name=machine_name,
            rows_updated=len(plan.updates),
            candidates_started=plan.candidates_started,
            candidates_confirmed=plan.candidates_confirmed,
            cancellations=plan.cancellations,
            suspended=plan.suspended,
            queries=queries,
            rows_read=rows_read,
            rows_written=rows_written,
        )

    def _lock_key(self) -> int:
        # MUST match CollectorStateEngine._lock_key so a removal pass and a state
        # pass serialize on the same advisory lock for the same schema.
        digest = hashlib.sha256(
            f"bic:collector-state:{self._db.config.schema}".encode("utf-8")
        ).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)
