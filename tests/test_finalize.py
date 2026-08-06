"""Unit tests for bic.finalize (Sprint 2, Task 7). No database required.

Covers the finalization eligibility rules (confirmations + grace boundaries),
the pure reconciliation plan (state-history and decision-summary JSON builders,
order, determinism, offline suspension, reappearance guard), and the config
validation contract.
"""

import json
from datetime import datetime, timedelta, timezone

import pytest

from bic.config import REMOVAL_CONFIRMATIONS, REMOVAL_GRACE_SECONDS
from bic.finalize import (
    FINALIZATION_END_REASON,
    FinalizeApplyResult,
    FinalizeMachineStats,
    MachineFinalizePlan,
    eligible_for_finalization,
    plan_finalization,
    validate_grace,
)
from bic.reader import (
    MachineObservation,
    SlotObservation,
    SlotStatus,
    SourceState,
)
from bic.state import RowState

SESSION = datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc)
FIRST_ABSENT = datetime(2026, 7, 31, 8, 0, 0, tzinfo=timezone.utc)
GRACE = timedelta(seconds=REMOVAL_GRACE_SECONDS)


def _state(present=True, fresh=True):
    return SourceState(
        present=present,
        age_seconds=5.0 if fresh else 300.0,
        fresh=fresh,
    )


def _slot(key="1", serial="SN-1"):
    return SlotObservation(
        machine_name="aqc-03",
        slot_key=key,
        status=SlotStatus.MATCH,
        serial_bdr=serial,
        serial_rings=serial,
        ring_mac="AA:BB",
        ring_name="RingA",
        product="PRO",
        firmware_version="1.0",
        bdr_payload={"serial_number": serial},
        rings_payload={"serial_number": serial},
    )


def _machine(slots=(), name="aqc-03", fresh=True):
    return MachineObservation(
        machine_name=name,
        bdr=_state(fresh=fresh),
        rings=_state(fresh=fresh),
        slots=tuple(slots),
    )


def _row(row_id=1, serial="SN-1", slot="1", state="PENDING_REMOVAL",
         counter=3, first_absent=FIRST_ABSENT, ring_id=1, state_changed=SESSION,
         first_seen=FIRST_ABSENT, last_seen=FIRST_ABSENT, firmware="1.0"):
    return RowState(
        id=row_id,
        ring_id=ring_id,
        machine_name="aqc-03",
        slot_key=slot,
        serial_number=serial,
        lifecycle_state=state,
        state_changed_at=state_changed,
        first_seen_at=first_seen,
        last_seen_at=last_seen,
        removal_confirmations=counter,
        removal_first_absent_at=first_absent,
        firmware_version=firmware,
        end_reason=None,
        finalized_at=None,
    )


def _plan(observation, rows=(), session=SESSION,
          confirmations=REMOVAL_CONFIRMATIONS, grace=GRACE):
    return plan_finalization(
        "aqc-03",
        observation,
        {row.slot_key: row for row in rows},
        session,
        confirmations,
        grace,
    )


# ── Eligibility: grace boundary ─────────────────────────────────────────────


def test_grace_not_elapsed_no_finalization():
    session = FIRST_ABSENT + timedelta(seconds=REMOVAL_GRACE_SECONDS - 1)
    assert eligible_for_finalization(_row(), session, 3, GRACE) is False
    plan = _plan(_machine(slots=()), rows=(_row(),), session=session)
    assert plan.finalized == ()


def test_grace_elapsed_finalizes():
    session = FIRST_ABSENT + GRACE
    assert eligible_for_finalization(_row(), session, 3, GRACE) is True
    plan = _plan(_machine(slots=()), rows=(_row(),), session=session)
    assert len(plan.finalized) == 1


def test_grace_exact_boundary_finalizes():
    session = FIRST_ABSENT + GRACE + timedelta(seconds=1)
    plan = _plan(_machine(slots=()), rows=(_row(),), session=session)
    assert len(plan.finalized) == 1
    assert plan.finalized[0].finalized_at == session


def test_grace_zero_finalizes_immediately():
    plan = _plan(_machine(slots=()), rows=(_row(),), session=SESSION,
                 grace=timedelta(0))
    assert len(plan.finalized) == 1


# ── Eligibility: other gates ────────────────────────────────────────────────


def test_not_pending_never_finalizes():
    row = _row(state="TRACKING", counter=3, first_absent=FIRST_ABSENT)
    assert eligible_for_finalization(row, SESSION, 3, GRACE) is False
    assert _plan(_machine(slots=()), rows=(row,)).finalized == ()


def test_insufficient_confirmations_never_finalizes():
    row = _row(state="PENDING_REMOVAL", counter=2, first_absent=FIRST_ABSENT)
    assert eligible_for_finalization(row, SESSION, 3, GRACE) is False
    assert _plan(_machine(slots=()), rows=(row,)).finalized == ()


def test_missing_first_absent_never_finalizes():
    row = _row(state="PENDING_REMOVAL", counter=3, first_absent=None)
    assert eligible_for_finalization(row, SESSION, 3, GRACE) is False
    assert _plan(_machine(slots=()), rows=(row,)).finalized == ()


def test_ring_present_in_current_observation_never_finalizes():
    row = _row(serial="SN-1")
    plan = _plan(_machine(slots=(_slot(key="1", serial="SN-1"),)), rows=(row,))
    assert plan.finalized == ()


def test_stale_machine_suspends_finalization():
    plan = _plan(_machine(slots=(), fresh=False), rows=(_row(),))
    assert plan.suspended is True
    assert plan.finalized == ()


def test_none_observation_suspends():
    plan = _plan(None, rows=(_row(),))
    assert plan.suspended is True
    assert plan.finalized == ()


def test_multiple_eligible_rings_ordered_by_slot():
    plan = _plan(
        _machine(slots=()),
        rows=(
            _row(row_id=2, serial="SN-B", slot="2"),
            _row(row_id=1, serial="SN-A", slot="1"),
        ),
    )
    assert [op.row_id for op in plan.finalized] == [1, 2]


# ── History / decision payloads ─────────────────────────────────────────────


def test_state_history_json_records_known_states():
    plan = _plan(_machine(slots=()), rows=(_row(),))
    history = json.loads(plan.finalized[0].state_history)
    assert [entry["state"] for entry in history] == ["OBSERVED", "PENDING_REMOVAL"]
    assert history[0]["changed_at"] == FIRST_ABSENT.isoformat()
    assert history[1]["changed_at"] == SESSION.isoformat()


def test_decision_summary_json_is_complete():
    plan = _plan(_machine(slots=()), rows=(_row(),), session=SESSION)
    summary = json.loads(plan.finalized[0].decision_summary)
    assert summary["end_reason"] == FINALIZATION_END_REASON
    assert summary["removal_confirmations"] == 3
    assert summary["confirmation_threshold"] == REMOVAL_CONFIRMATIONS
    assert summary["grace_seconds"] == REMOVAL_GRACE_SECONDS
    assert summary["first_absent_at"] == FIRST_ABSENT.isoformat()
    assert summary["finalized_at"] == SESSION.isoformat()


def test_json_serialization_is_stable():
    first = _plan(_machine(slots=()), rows=(_row(),))
    second = _plan(_machine(slots=()), rows=(_row(),))
    assert first == second
    assert first.finalized[0].state_history == second.finalized[0].state_history
    assert first.finalized[0].decision_summary == second.finalized[0].decision_summary


# ── Config validation ───────────────────────────────────────────────────────


def test_validate_grace_defaults_to_spec():
    assert validate_grace(None) == timedelta(seconds=REMOVAL_GRACE_SECONDS)
    assert validate_grace(timedelta(seconds=5)) == timedelta(seconds=5)


def test_validate_grace_rejects_bad_values():
    with pytest.raises(ValueError):
        validate_grace(120)
    with pytest.raises(ValueError):
        validate_grace(timedelta(seconds=-1))


# ── Result model ────────────────────────────────────────────────────────────


def test_result_aggregation():
    result = FinalizeApplyResult(
        session=SESSION,
        stats=(
            FinalizeMachineStats("aqc-01", 2, 2, 2, 2, False, 5, 2, 6),
            FinalizeMachineStats("aqc-02", 0, 0, 0, 0, True, 2, 0, 0),
        ),
    )
    assert result.machine_count == 2
    assert result.query_count == 7
    assert result.rows_read == 2
    assert result.rows_written == 6
    assert result.rows_finalized == 2
    assert result.history_rows == 2
    assert result.event_rows == 2
    assert result.deleted_rows == 2
    assert result.suspended_machines == 1


def test_machine_finalize_plan_defaults():
    plan = MachineFinalizePlan(machine_name="aqc-03")
    assert plan.finalized == ()
    assert plan.suspended is False
