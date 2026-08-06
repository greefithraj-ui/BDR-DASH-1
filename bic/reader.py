"""Live Data Reader (Sprint 2, Task 2).

Reads ONLY the approved PostgreSQL live tables (public.live_rings_raw and
public.live_bdr_raw), joins them into an in-memory observation model, validates
freshness, and detects cross-source mismatches. Pure read-only: nothing is ever
written to BIC tables or updated in this module.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from bic.config import FRESHNESS_WINDOW_SECONDS
from bic.db import BicDatabase

DEFAULT_RINGS_TABLE = "public.live_rings_raw"
DEFAULT_BDR_TABLE = "public.live_bdr_raw"

_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_NON_SLOT_KEYS = frozenset(
    {"saved_at", "session_id", "_meta", "machine_name", "timestamp", "downloaded_at"}
)
_EMPTY_SERIALS = frozenset(("--", "N/A"))


class SlotStatus(Enum):
    """Cross-source agreement for one machine slot.

    BDR_ONLY / RINGS_ONLY are data-quality mismatches per the Architecture
    Specification (one-source-only), not just MISMATCH.
    """

    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    BDR_ONLY = "BDR_ONLY"
    RINGS_ONLY = "RINGS_ONLY"


@dataclass(frozen=True)
class SourceState:
    """Health of one source table row for a machine."""

    present: bool
    downloaded_at: datetime | None = None
    age_seconds: float | None = None
    fresh: bool = False
    parse_error: str | None = None


@dataclass(frozen=True)
class SlotObservation:
    """One machine+slot joined across the two live sources."""

    machine_name: str
    slot_key: str
    status: SlotStatus
    serial_bdr: str | None
    serial_rings: str | None
    ring_mac: str | None
    ring_name: str | None
    product: str | None
    firmware_version: str | None
    bdr_payload: dict | None
    rings_payload: dict | None

    @property
    def serial_number(self) -> str | None:
        """Resolved serial: rings side wins when present, else bdr side."""
        return self.serial_rings if self.serial_rings is not None else self.serial_bdr


@dataclass(frozen=True)
class MachineObservation:
    """Joined in-memory observation for one machine."""

    machine_name: str
    bdr: SourceState
    rings: SourceState
    slots: tuple[SlotObservation, ...] = field(default_factory=tuple)

    @property
    def fresh(self) -> bool:
        """A machine is fresh when at least one source is fresh."""
        return self.bdr.fresh or self.rings.fresh

    @property
    def has_mismatch(self) -> bool:
        """True when any slot is not a clean cross-source MATCH."""
        return any(slot.status is not SlotStatus.MATCH for slot in self.slots)

    @property
    def slot_map(self) -> dict[str, SlotObservation]:
        return {slot.slot_key: slot for slot in self.slots}


@dataclass(frozen=True)
class ObservationBatch:
    """All machine observations from one read pass."""

    machines: tuple[MachineObservation, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __iter__(self):
        return iter(self.machines)

    def __len__(self) -> int:
        return len(self.machines)

    @property
    def by_machine(self) -> dict[str, MachineObservation]:
        return {machine.machine_name: machine for machine in self.machines}


@dataclass(frozen=True)
class _SourceRow:
    machine_name: str
    content: str | None
    downloaded_at: datetime | None
    age_seconds: float | None


# ── Pure helpers (no database access) ────────────────────────────────────────


def is_fresh(age_seconds: float | None, threshold: float | None) -> bool:
    """Freshness rule: a payload is fresh when its age is within the threshold."""
    return age_seconds is not None and threshold is not None and age_seconds <= threshold


def is_occupied_serial(serial) -> bool:
    """A slot is occupied when its serial is a real value, not a placeholder."""
    if not isinstance(serial, str):
        return False
    value = serial.strip()
    return bool(value) and value not in _EMPTY_SERIALS


def extract_slots(payload: dict) -> dict:
    """Normalize a raw payload into {slot_key: slot_payload}.

    Handles the two live-table shapes: BDR payloads nest under "slots" while
    RINGS payloads are flat slot maps (optionally carrying session metadata).
    """
    if not isinstance(payload, dict):
        return {}
    slots = payload.get("slots")
    if isinstance(slots, dict):
        return slots
    return {key: value for key, value in payload.items() if key not in _NON_SLOT_KEYS}


def _occupied_slots(payload: dict | None) -> dict:
    if not payload:
        return {}
    slots = extract_slots(payload)
    return {
        key: entry
        for key, entry in slots.items()
        if isinstance(entry, dict) and is_occupied_serial(entry.get("serial_number"))
    }


def _pick(bdr_slot, rings_slot, field: str):
    for slot in (bdr_slot, rings_slot):
        if isinstance(slot, dict) and slot.get(field) is not None:
            return slot.get(field)
    return None


def _build_slot_observation(
    machine_name: str, slot_key: str, bdr_slot, rings_slot
) -> SlotObservation:
    serial_bdr = bdr_slot.get("serial_number") if isinstance(bdr_slot, dict) else None
    serial_rings = rings_slot.get("serial_number") if isinstance(rings_slot, dict) else None

    if bdr_slot is not None and rings_slot is not None:
        status = (
            SlotStatus.MATCH
            if serial_bdr == serial_rings
            else SlotStatus.MISMATCH
        )
    elif bdr_slot is not None:
        status = SlotStatus.BDR_ONLY
    else:
        status = SlotStatus.RINGS_ONLY

    return SlotObservation(
        machine_name=machine_name,
        slot_key=slot_key,
        status=status,
        serial_bdr=serial_bdr,
        serial_rings=serial_rings,
        ring_mac=_pick(bdr_slot, rings_slot, "ring_mac"),
        ring_name=_pick(bdr_slot, rings_slot, "ring_name"),
        product=_pick(bdr_slot, rings_slot, "product"),
        firmware_version=_pick(bdr_slot, rings_slot, "firmware_version"),
        bdr_payload=bdr_slot if isinstance(bdr_slot, dict) else None,
        rings_payload=rings_slot if isinstance(rings_slot, dict) else None,
    )


def build_machine_observation(
    machine_name: str,
    bdr_payload: dict | None,
    rings_payload: dict | None,
    bdr_state: SourceState,
    rings_state: SourceState,
) -> MachineObservation:
    """Join two parsed payloads into one machine observation.

    Pure function; both payloads must already be parsed JSON objects (None when
    the source was absent or unparseable). Occupied-only slots are matched by
    slot key across the two sources.
    """
    bdr_slots = _occupied_slots(bdr_payload)
    rings_slots = _occupied_slots(rings_payload)
    slot_keys = sorted(set(bdr_slots) | set(rings_slots))
    slots = tuple(
        _build_slot_observation(machine_name, key, bdr_slots.get(key), rings_slots.get(key))
        for key in slot_keys
    )
    return MachineObservation(
        machine_name=machine_name,
        bdr=bdr_state,
        rings=rings_state,
        slots=slots,
    )


def _reader_select_sql(table: str, machine_name: str | None = None) -> str:
    """Read-only query against one live table, ages computed on the server clock."""
    sql = (
        "SELECT machine_name, content, downloaded_at, "
        "EXTRACT(EPOCH FROM (NOW() - downloaded_at)) AS age_seconds "
        f"FROM {table}"
    )
    if machine_name is not None:
        sql += " WHERE machine_name = %s"
    return sql + " ORDER BY machine_name"


def validate_table_ref(table: str) -> str:
    """Return the table ref if it is a safe schema.table identifier.

    Accepts `public` (the approved live tables live there); only blocks
    SQL injection via strict identifier rules.
    """
    parts = table.split(".")
    if len(parts) != 2:
        raise ValueError(f"table must be schema.table, got {table!r}")
    schema, name = parts
    if not _IDENTIFIER_RE.fullmatch(schema):
        raise ValueError(f"invalid schema in table ref: {table!r}")
    if not _IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"invalid table name in table ref: {table!r}")
    return f"{schema}.{name}"


def _parse_content(content: str | None) -> tuple[dict | None, str | None]:
    if content is None:
        return None, None
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError) as exc:
        return None, f"invalid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "content is not a JSON object"
    return data, None


def _make_source_state(
    row: _SourceRow | None, parse_error: str | None, threshold: float
) -> SourceState:
    if row is None:
        return SourceState(present=False, parse_error=parse_error)
    return SourceState(
        present=True,
        downloaded_at=row.downloaded_at,
        age_seconds=row.age_seconds,
        fresh=is_fresh(row.age_seconds, threshold),
        parse_error=parse_error,
    )


class LiveDataReader:
    """Reads the two approved live tables and joins them into observations."""

    def __init__(
        self,
        db: BicDatabase,
        *,
        freshness_threshold: float | None = None,
        rings_table: str = DEFAULT_RINGS_TABLE,
        bdr_table: str = DEFAULT_BDR_TABLE,
    ) -> None:
        if freshness_threshold is not None and freshness_threshold <= 0:
            raise ValueError("freshness_threshold must be positive")
        self._db = db
        self.freshness_threshold = (
            FRESHNESS_WINDOW_SECONDS
            if freshness_threshold is None
            else float(freshness_threshold)
        )
        self.rings_table = validate_table_ref(rings_table)
        self.bdr_table = validate_table_ref(bdr_table)

    def read_all(self) -> ObservationBatch:
        """Read every machine present in either live table and join them."""
        rings = self._read_source_rows(self.rings_table)
        bdr = self._read_source_rows(self.bdr_table)
        machine_names = sorted(set(rings) | set(bdr))
        observations = tuple(
            self._to_machine_observation(name, bdr.get(name), rings.get(name))
            for name in machine_names
        )
        return ObservationBatch(machines=observations)

    def read_machine(self, machine_name: str) -> MachineObservation | None:
        """Read one machine; None when it has no row in either live table."""
        rings = self._read_source_rows(self.rings_table, machine_name)
        bdr = self._read_source_rows(self.bdr_table, machine_name)
        rings_row = rings.get(machine_name)
        bdr_row = bdr.get(machine_name)
        if rings_row is None and bdr_row is None:
            return None
        return self._to_machine_observation(machine_name, bdr_row, rings_row)

    def _read_source_rows(
        self, table: str, machine_name: str | None = None
    ) -> dict[str, _SourceRow]:
        conn = self._db.get_connection()
        try:
            with conn.cursor() as cur:
                params = (machine_name,) if machine_name is not None else None
                cur.execute(_reader_select_sql(table, machine_name), params)
                rows = {
                    row[0]: _SourceRow(
                        machine_name=row[0],
                        content=row[1],
                        downloaded_at=row[2],
                        age_seconds=float(row[3]) if row[3] is not None else None,
                    )
                    for row in cur.fetchall()
                }
            return rows
        finally:
            conn.close()

    def _to_machine_observation(
        self, machine_name: str, bdr_row: _SourceRow | None, rings_row: _SourceRow | None
    ) -> MachineObservation:
        bdr_payload, bdr_error = _parse_content(bdr_row.content) if bdr_row else (None, None)
        rings_payload, rings_error = (
            _parse_content(rings_row.content) if rings_row else (None, None)
        )
        bdr_state = _make_source_state(bdr_row, bdr_error, self.freshness_threshold)
        rings_state = _make_source_state(rings_row, rings_error, self.freshness_threshold)
        return build_machine_observation(
            machine_name, bdr_payload, rings_payload, bdr_state, rings_state
        )
