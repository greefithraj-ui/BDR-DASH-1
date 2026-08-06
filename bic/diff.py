"""Smart Update Engine (Sprint 2, Task 4).

Compares a previous ObservationBatch against a current one and produces
immutable Change objects describing exactly what changed. It makes no collector
decisions: no removal/replacement classification, no lifecycle transitions, and
no writes of any kind.

Determinism guarantee: the same two inputs always produce the identical
DiffResult. The engine never reads the wall clock; DiffResult.generated_at is
copied verbatim from the current ObservationBatch input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from bic.reader import MachineObservation, ObservationBatch, SlotObservation

IDENTITY_FIELDS = ("ring_mac", "ring_name", "product")


class ChangeType(Enum):
    """Primitive facts emitted by the engine; the full set from Task 4."""

    NEW_RING = "NEW_RING"
    REMOVED_RING_CANDIDATE = "REMOVED_RING_CANDIDATE"
    SERIAL_CHANGED = "SERIAL_CHANGED"
    SLOT_CHANGED = "SLOT_CHANGED"
    STATE_CHANGED = "STATE_CHANGED"
    FIRMWARE_CHANGED = "FIRMWARE_CHANGED"
    IDENTITY_CHANGED = "IDENTITY_CHANGED"


@dataclass(frozen=True)
class SlotInfo:
    """Immutable snapshot of one ring's slot state at a point in time."""

    serial_number: str
    slot_key: str
    state: str | None = None
    firmware_version: str | None = None
    ring_mac: str | None = None
    ring_name: str | None = None
    product: str | None = None


@dataclass(frozen=True)
class Change:
    """One immutable change fact. previous/current are slot snapshots."""

    change_type: ChangeType
    machine_name: str
    previous: SlotInfo | None = None
    current: SlotInfo | None = None
    changed_fields: tuple[str, ...] = field(default_factory=tuple)

    @property
    def serial_number(self) -> str | None:
        """Anchor serial: current ring when present, else the previous ring."""
        info = self.current if self.current is not None else self.previous
        return info.serial_number if info is not None else None

    @property
    def slot_key(self) -> str | None:
        """Anchor slot: current slot when present, else the previous slot."""
        info = self.current if self.current is not None else self.previous
        return info.slot_key if info is not None else None

    @property
    def previous_serial(self) -> str | None:
        return self.previous.serial_number if self.previous is not None else None

    @property
    def current_serial(self) -> str | None:
        return self.current.serial_number if self.current is not None else None

    @property
    def previous_slot_key(self) -> str | None:
        return self.previous.slot_key if self.previous is not None else None

    @property
    def current_slot_key(self) -> str | None:
        return self.current.slot_key if self.current is not None else None


@dataclass(frozen=True)
class MachineChanges:
    """All changes for one machine; stable and immutable."""

    machine_name: str
    changes: tuple[Change, ...] = field(default_factory=tuple)

    def __iter__(self):
        return iter(self.changes)

    def __len__(self) -> int:
        return len(self.changes)

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0


@dataclass(frozen=True)
class DiffResult:
    """Deterministic result of comparing two observation batches.

    generated_at is taken from the current ObservationBatch input; the engine
    never generates timestamps itself, so identical inputs yield identical
    DiffResults field-for-field.
    """

    machines: tuple[MachineChanges, ...] = field(default_factory=tuple)
    generated_at: datetime | None = None

    @property
    def machine_count(self) -> int:
        return len(self.machines)

    @property
    def change_count(self) -> int:
        return sum(len(machine.changes) for machine in self.machines)

    @property
    def has_changes(self) -> bool:
        return self.change_count > 0

    @property
    def changes(self) -> tuple[Change, ...]:
        """Flat, canonically sorted change list."""
        flat = [change for machine in self.machines for change in machine.changes]
        return tuple(
            sorted(flat, key=lambda change: (change.machine_name, _change_sort_key(change)))
        )

    @property
    def by_machine(self) -> dict[str, MachineChanges]:
        return {machine.machine_name: machine for machine in self.machines}

    def count_by_type(self) -> dict[ChangeType, int]:
        counts = {change_type: 0 for change_type in ChangeType}
        for change in self.changes:
            counts[change.change_type] += 1
        return counts


def _slot_state(slot: SlotObservation) -> str | None:
    rings = slot.rings_payload or {}
    bdr = slot.bdr_payload or {}
    state = rings.get("state")
    if state is None:
        state = bdr.get("state")
    return state


def _slot_info(slot: SlotObservation) -> SlotInfo:
    return SlotInfo(
        serial_number=slot.serial_number,
        slot_key=slot.slot_key,
        state=_slot_state(slot),
        firmware_version=slot.firmware_version,
        ring_mac=slot.ring_mac,
        ring_name=slot.ring_name,
        product=slot.product,
    )


def _serial_map(observation: MachineObservation) -> dict[str, SlotObservation]:
    """Map serial_number -> slot observation, first-wins by sorted slot key."""
    mapping: dict[str, SlotObservation] = {}
    for slot_key in sorted(observation.slot_map):
        slot = observation.slot_map[slot_key]
        if slot.serial_number is not None:
            mapping.setdefault(slot.serial_number, slot)
    return mapping


def _change_sort_key(change: Change) -> tuple:
    return (
        change.change_type.value,
        change.serial_number or "",
        change.slot_key or "",
    )


class SmartUpdateEngine:
    """Compares two ObservationBatch inputs and emits immutable Change objects."""

    def diff(
        self, previous: ObservationBatch, current: ObservationBatch
    ) -> DiffResult:
        names = sorted(set(previous.by_machine) | set(current.by_machine))
        machines = tuple(
            self.diff_machine(
                name, previous.by_machine.get(name), current.by_machine.get(name)
            )
            for name in names
        )
        return DiffResult(machines=machines, generated_at=current.generated_at)

    def diff_machine(
        self,
        machine_name: str,
        previous: MachineObservation | None,
        current: MachineObservation | None,
    ) -> MachineChanges:
        """Diff one machine; None means the machine was absent from that batch."""
        if previous is None and current is None:
            return MachineChanges(machine_name=machine_name)

        changes: list[Change] = []

        if previous is None:
            for serial in sorted(_serial_map(current)):
                changes.append(
                    Change(
                        change_type=ChangeType.NEW_RING,
                        machine_name=machine_name,
                        current=_slot_info(_serial_map(current)[serial]),
                    )
                )
            return MachineChanges(
                machine_name, tuple(sorted(changes, key=_change_sort_key))
            )

        if current is None:
            for serial in sorted(_serial_map(previous)):
                changes.append(
                    Change(
                        change_type=ChangeType.REMOVED_RING_CANDIDATE,
                        machine_name=machine_name,
                        previous=_slot_info(_serial_map(previous)[serial]),
                    )
                )
            return MachineChanges(
                machine_name, tuple(sorted(changes, key=_change_sort_key))
            )

        previous_serials = _serial_map(previous)
        current_serials = _serial_map(current)
        prev_serial_set = set(previous_serials)
        curr_serial_set = set(current_serials)

        for serial in sorted(curr_serial_set - prev_serial_set):
            changes.append(
                Change(
                    change_type=ChangeType.NEW_RING,
                    machine_name=machine_name,
                    current=_slot_info(current_serials[serial]),
                )
            )

        for serial in sorted(prev_serial_set - curr_serial_set):
            changes.append(
                Change(
                    change_type=ChangeType.REMOVED_RING_CANDIDATE,
                    machine_name=machine_name,
                    previous=_slot_info(previous_serials[serial]),
                )
            )

        for serial in sorted(prev_serial_set & curr_serial_set):
            prev_slot = previous_serials[serial]
            curr_slot = current_serials[serial]
            if prev_slot.slot_key != curr_slot.slot_key:
                changes.append(
                    Change(
                        change_type=ChangeType.SLOT_CHANGED,
                        machine_name=machine_name,
                        previous=_slot_info(prev_slot),
                        current=_slot_info(curr_slot),
                    )
                )
            if _slot_state(prev_slot) != _slot_state(curr_slot):
                changes.append(
                    Change(
                        change_type=ChangeType.STATE_CHANGED,
                        machine_name=machine_name,
                        previous=_slot_info(prev_slot),
                        current=_slot_info(curr_slot),
                    )
                )
            if prev_slot.firmware_version != curr_slot.firmware_version:
                changes.append(
                    Change(
                        change_type=ChangeType.FIRMWARE_CHANGED,
                        machine_name=machine_name,
                        previous=_slot_info(prev_slot),
                        current=_slot_info(curr_slot),
                    )
                )
            changed_fields = tuple(
                field_name
                for field_name in IDENTITY_FIELDS
                if getattr(prev_slot, field_name) != getattr(curr_slot, field_name)
            )
            if changed_fields:
                changes.append(
                    Change(
                        change_type=ChangeType.IDENTITY_CHANGED,
                        machine_name=machine_name,
                        previous=_slot_info(prev_slot),
                        current=_slot_info(curr_slot),
                        changed_fields=changed_fields,
                    )
                )

        for slot_key in sorted(set(previous.slot_map) & set(current.slot_map)):
            prev_slot = previous.slot_map[slot_key]
            curr_slot = current.slot_map[slot_key]
            if prev_slot.serial_number != curr_slot.serial_number:
                changes.append(
                    Change(
                        change_type=ChangeType.SERIAL_CHANGED,
                        machine_name=machine_name,
                        previous=_slot_info(prev_slot),
                        current=_slot_info(curr_slot),
                    )
                )

        return MachineChanges(
            machine_name, tuple(sorted(changes, key=_change_sort_key))
        )
