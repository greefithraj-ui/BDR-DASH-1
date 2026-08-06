"""Collector State Engine (Sprint 2, Task 5).

The first STATEFUL component of the Battery Intelligence Collector. It consumes
a DiffResult together with the current ObservationBatch and maintains the
``active_rings`` table -- the collector's sole state owner for the lifecycle
``OBSERVED -> TRACKING -> PENDING_REMOVAL -> FINALIZED``.

Task 5 scope is deliberately narrow:

* It maintains ONLY ``active_rings`` plus the FK-required ``ring_identities``
  anchor rows (``active_rings.ring_id`` references ``ring_identities.id`` and is
  the ``lifecycle_id`` of every tracked ring).
* It NEVER confirms removals, NEVER writes ``ring_history``, NEVER writes
  ``ring_events``, NEVER writes ``machine_checkpoint``, and NEVER finalizes a
  session. ``PENDING_REMOVAL`` and ``FINALIZED`` are defined lifecycle states
  that this task must not enter -- the engine asserts that every write it plans
  is ``OBSERVED`` or ``TRACKING`` only.

Determinism: the engine never reads the wall clock. Every timestamp written is
taken verbatim from ``current_batch.generated_at``, so identical inputs applied
against an identical database produce identical writes and an identical result.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Mapping, Sequence

try:
    import psycopg2

    HAS_PSYCOPG2 = True
except ImportError:  # pragma: no cover - only reached when psycopg2 is absent
    psycopg2 = None
    HAS_PSYCOPG2 = False

from bic.db import BicDatabase
from bic.diff import ChangeType, DiffResult
from bic.reader import MachineObservation, ObservationBatch
from bic.schema import LIFECYCLE_STATES


class RingLifecycleState(Enum):
    """Frozen collector lifecycle states (mirrors bic.schema.LIFECYCLE_STATES)."""

    OBSERVED = "OBSERVED"
    TRACKING = "TRACKING"
    PENDING_REMOVAL = "PENDING_REMOVAL"
    FINALIZED = "FINALIZED"


_WRITABLE_STATES = frozenset(
    {RingLifecycleState.OBSERVED.value, RingLifecycleState.TRACKING.value}
)

assert {state.value for state in RingLifecycleState} == set(LIFECYCLE_STATES)


# ── Object model (immutable snapshots of collector state) ───────────────────


@dataclass(frozen=True)
class RowState:
    """One ``active_rings`` row as read from the database."""

    id: int
    ring_id: int
    machine_name: str
    slot_key: str
    serial_number: str
    lifecycle_state: str
    state_changed_at: datetime
    first_seen_at: datetime
    last_seen_at: datetime
    removal_confirmations: int
    removal_first_absent_at: datetime | None
    firmware_version: str | None
    end_reason: str | None
    finalized_at: datetime | None


@dataclass(frozen=True)
class RingTrack:
    """Post-apply in-memory view of one tracked ring."""

    serial_number: str
    slot_key: str
    ring_id: int
    lifecycle_state: str
    firmware_version: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    state_changed_at: datetime


@dataclass(frozen=True)
class MachineTrack:
    """All tracked rings of one machine, sorted by slot key."""

    machine_name: str
    rings: tuple[RingTrack, ...] = field(default_factory=tuple)

    @property
    def by_slot(self) -> dict[str, RingTrack]:
        return {ring.slot_key: ring for ring in self.rings}

    @property
    def by_serial(self) -> dict[str, RingTrack]:
        return {ring.serial_number: ring for ring in self.rings}


@dataclass(frozen=True)
class CollectorState:
    """The engine's internal collector state after one apply pass."""

    session: datetime | None = None
    machines: tuple[MachineTrack, ...] = field(default_factory=tuple)

    @property
    def by_machine(self) -> dict[str, MachineTrack]:
        return {machine.machine_name: machine for machine in self.machines}


# ── Write plan (pure, deterministic) ────────────────────────────────────────


@dataclass(frozen=True)
class InsertOp:
    ring_id: int
    serial_number: str
    slot_key: str
    lifecycle_state: str
    firmware_version: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    state_changed_at: datetime


@dataclass(frozen=True)
class UpdateOp:
    row_id: int
    ring_id: int
    serial_number: str
    slot_key: str
    lifecycle_state: str
    firmware_version: str | None
    last_seen_at: datetime
    state_changed_at: datetime


@dataclass(frozen=True)
class DeleteOp:
    row_id: int


@dataclass(frozen=True)
class MachinePlan:
    """Deterministic write plan and resulting in-memory machine track."""

    machine_name: str
    inserts: tuple[InsertOp, ...] = field(default_factory=tuple)
    updates: tuple[UpdateOp, ...] = field(default_factory=tuple)
    deletes: tuple[DeleteOp, ...] = field(default_factory=tuple)
    conflicts: tuple[str, ...] = field(default_factory=tuple)
    result: MachineTrack | None = None

    @property
    def rows_written(self) -> int:
        return len(self.inserts) + len(self.updates) + len(self.deletes)


def occupied_slots(observation: MachineObservation | None) -> dict[str, str]:
    """slot_key -> serial for occupied slots; first-wins by sorted slot key.

    A serial that appears in more than one slot keeps the lowest slot key, which
    matches the Smart Update Engine's ``_serial_map`` first-wins rule so both
    layers agree on ring identity.
    """
    slots: dict[str, str] = {}
    serial_to_slot: dict[str, str] = {}
    if observation is None:
        return slots
    for slot_key in sorted(observation.slot_map):
        serial = observation.slot_map[slot_key].serial_number
        if serial is None:
            continue
        if serial in serial_to_slot:
            continue
        serial_to_slot[serial] = slot_key
        slots[slot_key] = serial
    return slots


def reconcile_machine(
    machine_name: str,
    observation: MachineObservation | None,
    rows: Mapping[str, RowState],
    ring_ids: Mapping[str, int],
    new_serials: frozenset[str],
    session: datetime,
) -> MachinePlan:
    """Pure reconciliation of one machine's active_rings (Task 5 rules).

    ``rows`` maps slot_key -> current active_rings row for the machine,
    ``ring_ids`` maps serial_number -> ring_identities.id for every trackable
    serial present in the current observation, ``new_serials`` is the set of
    serials the diff reported as NEW_RING this cycle, and ``session`` is the
    observation timestamp that stamps every write (never the wall clock).
    """
    slots = occupied_slots(observation)
    serial_to_slot = {serial: slot_key for slot_key, serial in slots.items()}

    rows_by_serial: dict[str, RowState] = {}
    for slot_key in sorted(rows):
        row = rows[slot_key]
        rows_by_serial.setdefault(row.serial_number, row)

    deletes: list[DeleteOp] = []
    kept_rows: list[RowState] = []
    for row in rows.values():
        target_slot = serial_to_slot.get(row.serial_number)
        if target_slot is not None and target_slot != row.slot_key:
            deletes.append(DeleteOp(row.id))
        elif slots.get(row.slot_key) not in (None, row.serial_number):
            deletes.append(DeleteOp(row.id))
        else:
            kept_rows.append(row)

    inserts: list[InsertOp] = []
    updates: list[UpdateOp] = []
    conflicts: list[str] = []
    result_rings: list[RingTrack] = []

    for slot_key in sorted(slots):
        serial = slots[slot_key]
        slot = observation.slot_map[slot_key]
        ring_id = ring_ids.get(serial)
        if ring_id is None:
            conflicts.append(
                f"slot {slot_key}: serial {serial} missing identity fields; not tracked"
            )
            continue
        firmware = slot.firmware_version
        row = rows_by_serial.get(serial)
        if row is None:
            inserts.append(
                InsertOp(
                    ring_id=ring_id,
                    serial_number=serial,
                    slot_key=slot_key,
                    lifecycle_state=RingLifecycleState.OBSERVED.value,
                    firmware_version=firmware,
                    first_seen_at=session,
                    last_seen_at=session,
                    state_changed_at=session,
                )
            )
            result_rings.append(
                RingTrack(
                    serial,
                    slot_key,
                    ring_id,
                    RingLifecycleState.OBSERVED.value,
                    firmware,
                    session,
                    session,
                    session,
                )
            )
        elif row.slot_key == slot_key:
            state, state_changed = _next_lifecycle(
                row.lifecycle_state,
                row.state_changed_at,
                is_new=serial in new_serials,
                session=session,
            )
            updates.append(
                UpdateOp(
                    row_id=row.id,
                    ring_id=row.ring_id,
                    serial_number=serial,
                    slot_key=slot_key,
                    lifecycle_state=state,
                    firmware_version=firmware,
                    last_seen_at=session,
                    state_changed_at=state_changed,
                )
            )
            result_rings.append(
                RingTrack(
                    serial,
                    slot_key,
                    row.ring_id,
                    state,
                    firmware,
                    row.first_seen_at,
                    session,
                    state_changed,
                )
            )
        else:
            state, state_changed = _next_lifecycle(
                row.lifecycle_state,
                row.state_changed_at,
                is_new=serial in new_serials,
                session=session,
            )
            inserts.append(
                InsertOp(
                    ring_id=row.ring_id,
                    serial_number=serial,
                    slot_key=slot_key,
                    lifecycle_state=state,
                    firmware_version=firmware,
                    first_seen_at=row.first_seen_at,
                    last_seen_at=session,
                    state_changed_at=state_changed,
                )
            )
            result_rings.append(
                RingTrack(
                    serial,
                    slot_key,
                    row.ring_id,
                    state,
                    firmware,
                    row.first_seen_at,
                    session,
                    state_changed,
                )
            )

    for row in kept_rows:
        if row.serial_number not in serial_to_slot:
            result_rings.append(
                RingTrack(
                    row.serial_number,
                    row.slot_key,
                    row.ring_id,
                    row.lifecycle_state,
                    row.firmware_version,
                    row.first_seen_at,
                    row.last_seen_at,
                    row.state_changed_at,
                )
            )

    result_rings.sort(key=lambda ring: ring.slot_key)
    plan = MachinePlan(
        machine_name=machine_name,
        inserts=tuple(inserts),
        updates=tuple(updates),
        deletes=tuple(deletes),
        conflicts=tuple(conflicts),
        result=MachineTrack(machine_name, tuple(result_rings)),
    )
    _assert_writable_states(plan)
    return plan


def _next_lifecycle(
    current_state: str,
    previous_state_changed_at: datetime,
    *,
    is_new: bool,
    session: datetime,
) -> tuple[str, datetime]:
    """Task 5 lifecycle transition for a serial that was already tracked.

    * Reappearance (NEW_RING) resets to OBSERVED.
    * Continuous observation promotes OBSERVED -> TRACKING.
    * TRACKING stays TRACKING; the state timestamp only moves on a transition.
    """
    if is_new:
        return RingLifecycleState.OBSERVED.value, session
    if current_state == RingLifecycleState.OBSERVED.value:
        return RingLifecycleState.TRACKING.value, session
    return current_state, previous_state_changed_at


def _assert_writable_states(plan: MachinePlan) -> None:
    for op in (*plan.inserts, *plan.updates):
        if op.lifecycle_state not in _WRITABLE_STATES:
            raise AssertionError(
                f"state engine must not write {op.lifecycle_state!r} "
                f"(Task 5 never enters PENDING_REMOVAL/FINALIZED)"
            )


# ── Apply result ────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class MachineApplyStats:
    machine_name: str
    rows_inserted: int
    rows_updated: int
    rows_deleted: int
    identity_writes: int
    queries: int
    rows_read: int
    rows_written: int
    conflicts: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)


@dataclass(frozen=True)
class CollectorApplyResult:
    session: datetime | None
    state: CollectorState
    stats: tuple[MachineApplyStats, ...] = field(default_factory=tuple)

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
    def rows_inserted(self) -> int:
        return sum(stat.rows_inserted for stat in self.stats)

    @property
    def rows_updated(self) -> int:
        return sum(stat.rows_updated for stat in self.stats)

    @property
    def rows_deleted(self) -> int:
        return sum(stat.rows_deleted for stat in self.stats)

    @property
    def identity_writes(self) -> int:
        return sum(stat.identity_writes for stat in self.stats)

    @property
    def conflict_count(self) -> int:
        return sum(stat.conflict_count for stat in self.stats)

    @property
    def has_conflicts(self) -> bool:
        return self.conflict_count > 0

    @property
    def by_machine(self) -> dict[str, MachineApplyStats]:
        return {stat.machine_name: stat for stat in self.stats}


# ── Input validation (pure) ─────────────────────────────────────────────────


def validate_apply_inputs(
    diff_result: DiffResult, current_batch: ObservationBatch
) -> datetime:
    """Return the deterministic session timestamp or raise on bad inputs.

    The engine must receive a tz-aware session timestamp derived from its input
    batch so every write is fully determined by the inputs (no wall clock).
    """
    if not isinstance(diff_result, DiffResult):
        raise TypeError(
            f"diff_result must be a DiffResult, got {type(diff_result).__name__}"
        )
    if not isinstance(current_batch, ObservationBatch):
        raise TypeError(
            f"current_batch must be an ObservationBatch, got {type(current_batch).__name__}"
        )
    session = current_batch.generated_at
    if session is None:
        raise ValueError(
            "current_batch.generated_at is required for deterministic state writes"
        )
    if session.tzinfo is None:
        raise ValueError(
            "current_batch.generated_at must be timezone-aware for deterministic state writes"
        )
    return session


# ── SQL ─────────────────────────────────────────────────────────────────────

_SELECT_ACTIVE_SQL = """
SELECT id, ring_id, machine_name, slot_key, serial_number, state,
       state_changed_at, first_seen_at, last_seen_at, removal_confirmations,
       removal_first_absent_at, firmware_version, end_reason, finalized_at
FROM active_rings
WHERE machine_name = %s
ORDER BY slot_key
"""

_SELECT_IDENTITIES_SQL = """
SELECT id, serial_number, ring_mac, ring_name, product
FROM ring_identities
WHERE serial_number = ANY(%s)
ORDER BY serial_number
"""

_IDENTITY_UPSERT_SQL = """
INSERT INTO ring_identities
    (serial_number, ring_mac, ring_name, product, first_seen_at, last_seen_at,
     created_at, updated_at)
VALUES %s
ON CONFLICT (serial_number) DO UPDATE SET
    last_seen_at = EXCLUDED.last_seen_at,
    updated_at = EXCLUDED.updated_at
RETURNING id, serial_number
"""

_INSERT_ACTIVE_SQL = """
INSERT INTO active_rings
    (ring_id, machine_name, slot_key, serial_number, state, state_changed_at,
     first_seen_at, last_seen_at, removal_confirmations, removal_first_absent_at,
     firmware_version, end_reason, finalized_at, updated_at)
VALUES %s
"""

_UPDATE_ACTIVE_SQL = """
UPDATE active_rings AS ar
SET state = v.state,
    state_changed_at = v.state_changed_at,
    last_seen_at = v.last_seen_at,
    firmware_version = v.firmware_version,
    removal_confirmations = 0,
    removal_first_absent_at = NULL,
    updated_at = v.updated_at
FROM (VALUES %s) AS v(row_id, state, state_changed_at, last_seen_at,
                      firmware_version, updated_at)
WHERE ar.id = v.row_id
"""

_DELETE_ACTIVE_SQL = "DELETE FROM active_rings WHERE id = ANY(%s)"


def _multi_values_params(rows: Sequence[tuple]) -> tuple[str, list]:
    """Build ``(%s,...),(%s,...)`` placeholders and the flattened params."""
    width = len(rows[0])
    placeholders = ", ".join(
        f"({', '.join(['%s'] * width)})" for _ in rows
    )
    params = [value for row in rows for value in row]
    return placeholders, params


# ── Engine ──────────────────────────────────────────────────────────────────


class CollectorStateEngine:
    """Reconciles the current observation against ``active_rings``.

    Tracks the current session, machine, slot, and lifecycle state as it applies,
    exposes the internal ``CollectorState`` after each pass, and writes only to
    ``active_rings`` (plus FK-required ``ring_identities`` anchors).
    """

    def __init__(self, db: BicDatabase) -> None:
        if not HAS_PSYCOPG2:
            raise RuntimeError(
                "psycopg2-binary is not installed; CollectorStateEngine requires it"
            )
        self._db = db
        self.current_session: ObservationBatch | None = None
        self.current_machine: str | None = None
        self.current_slot: str | None = None
        self.current_state: str | None = None
        self.last_state: CollectorState | None = None
        self.last_result: CollectorApplyResult | None = None

    def apply(
        self, diff_result: DiffResult, current_batch: ObservationBatch
    ) -> CollectorApplyResult:
        """Consume a diff + current batch and maintain ``active_rings``."""
        session = validate_apply_inputs(diff_result, current_batch)
        self.current_session = current_batch
        self.current_machine = None
        self.current_slot = None
        self.current_state = None

        conn = self._db.get_connection()
        try:
            machines: list[MachineTrack] = []
            stats: list[MachineApplyStats] = []
            for machine_name in sorted(current_batch.by_machine):
                self.current_machine = machine_name
                self.current_slot = None
                self.current_state = None
                try:
                    plan, stat = self._apply_machine(
                        conn,
                        machine_name,
                        current_batch.by_machine[machine_name],
                        diff_result,
                        session,
                    )
                except psycopg2.Error as exc:  # noqa: BLE001 - per-machine isolation
                    conn.rollback()
                    stat = MachineApplyStats(
                        machine_name=machine_name,
                        rows_inserted=0,
                        rows_updated=0,
                        rows_deleted=0,
                        identity_writes=0,
                        queries=0,
                        rows_read=0,
                        rows_written=0,
                        conflicts=(f"database error: {exc}",),
                    )
                    plan = None
                stats.append(stat)
                if plan is not None:
                    machines.append(plan.result)
                for ring in (plan.result.rings if plan is not None else ()):
                    self.current_slot = ring.slot_key
                    self.current_state = ring.lifecycle_state
        finally:
            conn.close()

        self.last_state = CollectorState(
            session=session, machines=tuple(machines)
        )
        self.last_result = CollectorApplyResult(
            session=session, state=self.last_state, stats=tuple(stats)
        )
        return self.last_result

    def _apply_machine(
        self,
        conn,
        machine_name: str,
        observation: MachineObservation,
        diff_result: DiffResult,
        session: datetime,
    ) -> tuple[MachinePlan, MachineApplyStats]:
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

            slots = occupied_slots(observation)
            present_serials = set(slots.values())

            if not present_serials:
                conn.commit()
                track = _unchanged_track(machine_name, rows_by_slot)
                plan = MachinePlan(
                    machine_name=machine_name,
                    result=track,
                )
                stat = MachineApplyStats(
                    machine_name=machine_name,
                    rows_inserted=0,
                    rows_updated=0,
                    rows_deleted=0,
                    identity_writes=0,
                    queries=queries,
                    rows_read=rows_read,
                    rows_written=0,
                    conflicts=tuple(plan.conflicts),
                )
                return plan, stat

            cur.execute(_SELECT_IDENTITIES_SQL, (list(present_serials),))
            queries += 1
            identity_rows = cur.fetchall()
            rows_read += len(identity_rows)
            existing_identity = {row[1]: row for row in identity_rows}

            upsert_rows: list[tuple] = []
            ring_ids: dict[str, int] = {}
            for slot_key in sorted(slots):
                serial = slots[slot_key]
                slot = observation.slot_map[slot_key]
                existing = existing_identity.get(serial)
                ring_mac = slot.ring_mac or (existing[2] if existing else None)
                ring_name = slot.ring_name or (existing[3] if existing else None)
                product = slot.product or (existing[4] if existing else None)
                if ring_mac is None or ring_name is None or product is None:
                    continue
                upsert_rows.append(
                    (serial, ring_mac, ring_name, product, session, session,
                     session, session)
                )

            if upsert_rows:
                placeholders, params = _multi_values_params(upsert_rows)
                cur.execute(
                    _IDENTITY_UPSERT_SQL.replace("VALUES %s", f"VALUES {placeholders}"),
                    params,
                )
                queries += 1
                rows_written += len(upsert_rows)
                ring_ids = {serial: row_id for row_id, serial in cur.fetchall()}

            machine_changes = diff_result.by_machine.get(machine_name)
            new_serials = frozenset(
                change.serial_number
                for change in machine_changes
                if change.change_type is ChangeType.NEW_RING
            ) if machine_changes else frozenset()

            plan = reconcile_machine(
                machine_name, observation, rows_by_slot, ring_ids, new_serials, session
            )

            if plan.deletes:
                cur.execute(
                    _DELETE_ACTIVE_SQL,
                    ([delete.row_id for delete in plan.deletes],),
                )
                queries += 1
                rows_written += len(plan.deletes)
            if plan.inserts:
                insert_rows = [
                    (
                        op.ring_id,
                        machine_name,
                        op.slot_key,
                        op.serial_number,
                        op.lifecycle_state,
                        op.state_changed_at,
                        op.first_seen_at,
                        op.last_seen_at,
                        0,
                        None,
                        op.firmware_version,
                        None,
                        None,
                        session,
                    )
                    for op in plan.inserts
                ]
                placeholders, params = _multi_values_params(insert_rows)
                cur.execute(
                    _INSERT_ACTIVE_SQL.replace("VALUES %s", f"VALUES {placeholders}"),
                    params,
                )
                queries += 1
                rows_written += len(plan.inserts)
            if plan.updates:
                update_rows = [
                    (
                        op.row_id,
                        op.lifecycle_state,
                        op.state_changed_at,
                        op.last_seen_at,
                        op.firmware_version,
                        session,
                    )
                    for op in plan.updates
                ]
                placeholders, params = _multi_values_params(update_rows)
                cur.execute(
                    _UPDATE_ACTIVE_SQL.replace("VALUES %s", f"VALUES {placeholders}"),
                    params,
                )
                queries += 1
                rows_written += len(plan.updates)

            conn.commit()

        stat = MachineApplyStats(
            machine_name=machine_name,
            rows_inserted=len(plan.inserts),
            rows_updated=len(plan.updates),
            rows_deleted=len(plan.deletes),
            identity_writes=len(upsert_rows),
            queries=queries,
            rows_read=rows_read,
            rows_written=rows_written,
            conflicts=tuple(plan.conflicts),
        )
        return plan, stat

    def _lock_key(self) -> int:
        digest = hashlib.sha256(
            f"bic:collector-state:{self._db.config.schema}".encode("utf-8")
        ).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)


def _unchanged_track(machine_name: str, rows: Mapping[str, RowState]) -> MachineTrack:
    rings = tuple(
        sorted(
            (
                RingTrack(
                    row.serial_number,
                    row.slot_key,
                    row.ring_id,
                    row.lifecycle_state,
                    row.firmware_version,
                    row.first_seen_at,
                    row.last_seen_at,
                    row.state_changed_at,
                )
                for row in rows.values()
            ),
            key=lambda ring: ring.slot_key,
        )
    )
    return MachineTrack(machine_name, rings)
