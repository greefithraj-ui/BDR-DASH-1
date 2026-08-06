"""Observation Validation Engine (Sprint 2, Task 3).

Sits immediately after the Live Data Reader. Validates every machine and slot
observation, detects malformed observations, invalid state combinations and
identity inconsistencies, and marks observations valid/invalid by producing
ValidationResult objects.

Pure in-memory: never modifies observations, never writes to PostgreSQL, never
creates collector state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from bic.reader import (
    MachineObservation,
    ObservationBatch,
    SlotObservation,
    SlotStatus,
)

IDENTITY_FIELDS = ("ring_mac", "ring_name", "product")

KNOWN_RING_STATES = frozenset({"ASSIGNED", "BDR_RUNNING", "PASSED", "FAILED"})
KNOWN_BDR_TEST_STEPS = frozenset({"QUEUED", "IN_PROGRESS", "PASSED", "FAILED", "COMPLETED"})
EXPECTED_STATE_STEP = {
    "ASSIGNED": "QUEUED",
    "BDR_RUNNING": "IN_PROGRESS",
    "PASSED": "COMPLETED",
    "FAILED": "FAILED",
}


class Severity(Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


class ValidationCode(Enum):
    """Every rule the engine can fire. ERROR codes invalidate the observation."""

    MACHINE_STALE = "MACHINE_STALE"
    SOURCE_PARSE_ERROR = "SOURCE_PARSE_ERROR"
    SOURCE_MISSING = "SOURCE_MISSING"
    SLOT_SERIAL_MISMATCH = "SLOT_SERIAL_MISMATCH"
    SLOT_ONE_SOURCE_ONLY = "SLOT_ONE_SOURCE_ONLY"
    IDENTITY_FIELD_MISSING = "IDENTITY_FIELD_MISSING"
    IDENTITY_FIELD_MISMATCH = "IDENTITY_FIELD_MISMATCH"
    INVALID_SLOT_STATE = "INVALID_SLOT_STATE"
    INVALID_STATE_COMBINATION = "INVALID_STATE_COMBINATION"


@dataclass(frozen=True)
class ValidationIssue:
    """One fired rule. slot_key is set for slot-scoped issues."""

    code: ValidationCode
    severity: Severity
    message: str
    slot_key: str | None = None


@dataclass(frozen=True)
class SlotValidationResult:
    slot_key: str
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity is Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity is Severity.WARNING)


@dataclass(frozen=True)
class MachineValidationResult:
    machine_name: str
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)
    slots: tuple[SlotValidationResult, ...] = field(default_factory=tuple)

    @property
    def slot_count(self) -> int:
        return len(self.slots)

    @property
    def error_count(self) -> int:
        machine_errors = sum(
            1 for issue in self.issues if issue.severity is Severity.ERROR
        )
        return machine_errors + sum(slot.error_count for slot in self.slots)

    @property
    def warning_count(self) -> int:
        machine_warnings = sum(
            1 for issue in self.issues if issue.severity is Severity.WARNING
        )
        return machine_warnings + sum(slot.warning_count for slot in self.slots)

    @property
    def slot_map(self) -> dict[str, SlotValidationResult]:
        return {slot.slot_key: slot for slot in self.slots}


@dataclass(frozen=True)
class ValidationResult:
    """Batch-level validation outcome; observations are never modified."""

    valid: bool
    machines: tuple[MachineValidationResult, ...] = field(default_factory=tuple)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def machine_count(self) -> int:
        return len(self.machines)

    @property
    def slot_count(self) -> int:
        return sum(machine.slot_count for machine in self.machines)

    @property
    def error_count(self) -> int:
        return sum(machine.error_count for machine in self.machines)

    @property
    def warning_count(self) -> int:
        return sum(machine.warning_count for machine in self.machines)

    @property
    def by_machine(self) -> dict[str, MachineValidationResult]:
        return {machine.machine_name: machine for machine in self.machines}


def _issue(
    code: ValidationCode,
    severity: Severity,
    message: str,
    slot_key: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(code=code, severity=severity, message=message, slot_key=slot_key)


def _has_errors(issues: tuple[ValidationIssue, ...]) -> bool:
    return any(issue.severity is Severity.ERROR for issue in issues)


def _state_and_step(slot: SlotObservation) -> tuple[str | None, str | None]:
    rings = slot.rings_payload or {}
    bdr = slot.bdr_payload or {}
    state = rings.get("state") or bdr.get("state")
    steps = rings.get("step_statuses")
    step = steps.get("BDR_TEST") if isinstance(steps, dict) else None
    return state, step


def machine_issues(observation: MachineObservation) -> tuple[ValidationIssue, ...]:
    """Machine-level rules: freshness, parse errors, and missing sources."""
    issues: list[ValidationIssue] = []

    if not observation.fresh:
        issues.append(
            _issue(
                ValidationCode.MACHINE_STALE,
                Severity.ERROR,
                "machine not fresh "
                f"(bdr_fresh={observation.bdr.fresh}, rings_fresh={observation.rings.fresh})",
            )
        )

    for name, source in (("bdr", observation.bdr), ("rings", observation.rings)):
        if source.present and source.parse_error:
            issues.append(
                _issue(
                    ValidationCode.SOURCE_PARSE_ERROR,
                    Severity.ERROR,
                    f"{name} source unparseable: {source.parse_error}",
                )
            )
        elif not source.present:
            issues.append(
                _issue(
                    ValidationCode.SOURCE_MISSING,
                    Severity.WARNING,
                    f"{name} source has no live-table row",
                )
            )

    return tuple(issues)


def slot_issues(slot: SlotObservation) -> tuple[ValidationIssue, ...]:
    """Slot-level rules: cross-source status, identity, and state consistency."""
    issues: list[ValidationIssue] = []

    if slot.status is SlotStatus.MISMATCH:
        issues.append(
            _issue(
                ValidationCode.SLOT_SERIAL_MISMATCH,
                Severity.ERROR,
                f"serial differs across sources: bdr={slot.serial_bdr!r} "
                f"rings={slot.serial_rings!r}",
                slot.slot_key,
            )
        )
    elif slot.status in (SlotStatus.BDR_ONLY, SlotStatus.RINGS_ONLY):
        issues.append(
            _issue(
                ValidationCode.SLOT_ONE_SOURCE_ONLY,
                Severity.WARNING,
                f"present in {slot.status.name} source only",
                slot.slot_key,
            )
        )

    missing = [f for f in IDENTITY_FIELDS if getattr(slot, f) is None]
    if missing:
        issues.append(
            _issue(
                ValidationCode.IDENTITY_FIELD_MISSING,
                Severity.ERROR,
                f"missing identity fields: {', '.join(missing)}",
                slot.slot_key,
            )
        )

    if slot.bdr_payload and slot.rings_payload:
        for name in IDENTITY_FIELDS:
            bdr_value = slot.bdr_payload.get(name)
            rings_value = slot.rings_payload.get(name)
            if bdr_value is not None and rings_value is not None and bdr_value != rings_value:
                issues.append(
                    _issue(
                        ValidationCode.IDENTITY_FIELD_MISMATCH,
                        Severity.ERROR,
                        f"{name} differs: bdr={bdr_value!r} rings={rings_value!r}",
                        slot.slot_key,
                    )
                )

    state, step = _state_and_step(slot)
    if state is not None and state not in KNOWN_RING_STATES:
        issues.append(
            _issue(
                ValidationCode.INVALID_SLOT_STATE,
                Severity.ERROR,
                f"unknown ring state {state!r}",
                slot.slot_key,
            )
        )
    elif step is not None:
        if step not in KNOWN_BDR_TEST_STEPS:
            issues.append(
                _issue(
                    ValidationCode.INVALID_SLOT_STATE,
                    Severity.ERROR,
                    f"unknown BDR_TEST step {step!r}",
                    slot.slot_key,
                )
            )
        elif EXPECTED_STATE_STEP.get(state) != step:
            issues.append(
                _issue(
                    ValidationCode.INVALID_STATE_COMBINATION,
                    Severity.ERROR,
                    f"state {state!r} incompatible with BDR_TEST step {step!r}",
                    slot.slot_key,
                )
            )

    return tuple(issues)


class ValidationEngine:
    """Stateless engine validating reader output; produces ValidationResults."""

    def validate(self, batch: ObservationBatch) -> ValidationResult:
        results = tuple(self.validate_machine(observation) for observation in batch.machines)
        return ValidationResult(
            valid=all(result.valid for result in results),
            machines=results,
        )

    def validate_machine(
        self, observation: MachineObservation
    ) -> MachineValidationResult:
        machine_issue_tuple = machine_issues(observation)
        slot_results = tuple(
            self.validate_slot(slot) for slot in observation.slots
        )
        valid = not _has_errors(machine_issue_tuple) and all(
            slot.valid for slot in slot_results
        )
        return MachineValidationResult(
            machine_name=observation.machine_name,
            valid=valid,
            issues=machine_issue_tuple,
            slots=slot_results,
        )

    def validate_slot(self, slot: SlotObservation) -> SlotValidationResult:
        issue_tuple = slot_issues(slot)
        return SlotValidationResult(
            slot_key=slot.slot_key,
            valid=not _has_errors(issue_tuple),
            issues=issue_tuple,
        )
