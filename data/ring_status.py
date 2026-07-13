"""ring_status — Latest-state table for the BDR search fleet.

Replaces the slow append-only archive_entries approach with a single
upserted row per (serial_number, machine) that always holds the most
recent snapshot data.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


# ---------------------------------------------------------------------------
# STEP 1 — Schema
# ---------------------------------------------------------------------------

RING_STATUS_DDL = """
CREATE TABLE IF NOT EXISTS ring_status (
    serial_number TEXT NOT NULL,
    machine TEXT NOT NULL,
    slot INTEGER,
    ring_mac TEXT,
    ring_name TEXT,
    state TEXT NOT NULL,
    phase TEXT,
    cycle INTEGER,
    avg_bdr REAL,
    battery_current REAL,
    firmware_version TEXT,
    phase_start_time TIMESTAMPTZ,
    last_charge_change_time TIMESTAMPTZ,
    saved_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (serial_number, machine)
);
CREATE INDEX IF NOT EXISTS idx_ring_serial ON ring_status (serial_number);
"""


def init_ring_status_table(conn):
    """Create ring_status table and index if they don't exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS ring_status ("
            "serial_number TEXT NOT NULL, "
            "machine TEXT NOT NULL, "
            "slot INTEGER, "
            "ring_mac TEXT, "
            "ring_name TEXT, "
            "state TEXT NOT NULL, "
            "phase TEXT, "
            "cycle INTEGER, "
            "avg_bdr REAL, "
            "battery_current REAL, "
            "firmware_version TEXT, "
            "phase_start_time TIMESTAMPTZ, "
            "last_charge_change_time TIMESTAMPTZ, "
            "saved_at TIMESTAMPTZ NOT NULL, "
            "updated_at TIMESTAMPTZ DEFAULT now(), "
            "PRIMARY KEY (serial_number, machine)"
        ")")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ring_serial ON ring_status (serial_number)")
        # Ensure columns exist for tables created before this update
        for col, typ in [
            ("ring_name",          "TEXT"),
            ("battery_current",    "REAL"),
            ("firmware_version",   "TEXT"),
        ]:
            try:
                cur.execute(f"ALTER TABLE ring_status ADD COLUMN {col} {typ}")
            except Exception:
                pass  # column already exists


# ---------------------------------------------------------------------------
# STEP 2 — Extraction
# ---------------------------------------------------------------------------

def _epoch_to_dt(val):
    """Convert a Unix epoch float to a timezone-aware datetime, or None."""
    if val is None:
        return None
    try:
        return datetime.fromtimestamp(float(val), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def extract_slot(machine, saved_at, slot_num, slot_dict):
    """Extract the fields needed for ring_status from one slot of a snapshot.

    Returns a dict with exactly these keys:
        serial_number, machine, slot, ring_mac, ring_name, state,
        phase, cycle, avg_bdr, battery_current, firmware_version,
        phase_start_time, last_charge_change_time, saved_at

    Conditional logic:
        BDR_RUNNING  -> bdr_state is live, bdr_data is null
        PASSED/FAILED -> bdr_data is live, bdr_state is null
    """
    state = slot_dict.get("state", "")
    bdr_data = slot_dict.get("bdr_data") or {}
    bdr_state = slot_dict.get("bdr_state") or {}

    phase = None
    cycle = None
    avg_bdr = None
    phase_start_time = None
    last_charge_change_time = None

    if state == "BDR_RUNNING":
        phase = bdr_state.get("phase")
        cycle = bdr_state.get("cycle")
        avg_bdr = None  # never compute while running
        phase_start_time = _epoch_to_dt(bdr_state.get("phase_start_time"))
        last_charge_change_time = _epoch_to_dt(bdr_state.get("last_charge_change_time"))
    elif state in ("PASSED", "FAILED"):
        phase = bdr_data.get("phase_at_finalize") or bdr_state.get("phase")
        cycle = bdr_data.get("final_cycle")
        avg_bdr = bdr_data.get("avg_bdr")
        phase_start_time = _epoch_to_dt(bdr_data.get("phase_start_time"))
        last_charge_change_time = None  # not present in bdr_data

    serial_number = (slot_dict.get("serial_number") or "").strip()
    if not serial_number or serial_number in ("--", "N/A"):
        return None

    return {
        "serial_number": serial_number,
        "machine": machine,
        "slot": int(slot_num) if slot_num is not None else None,
        "ring_mac": slot_dict.get("ring_mac"),
        "ring_name": slot_dict.get("ring_name"),
        "state": state,
        "phase": phase,
        "cycle": cycle,
        "avg_bdr": avg_bdr,
        "battery_current": slot_dict.get("battery_current"),
        "firmware_version": slot_dict.get("firmware_version"),
        "phase_start_time": phase_start_time,
        "last_charge_change_time": last_charge_change_time,
        "saved_at": saved_at,
    }


def _parse_saved_at(saved_at_str):
    """Parse the saved_at ISO string from the JSON file into a datetime."""
    if not saved_at_str:
        return datetime.now(tz=timezone.utc)
    try:
        # Python 3.7+ handles timezone offsets in fromisoformat
        return datetime.fromisoformat(saved_at_str)
    except (ValueError, TypeError):
        return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# STEP 3 — Upsert with staleness guard
# ---------------------------------------------------------------------------

UPSERT_SQL = """
INSERT INTO ring_status (
    serial_number, machine, slot, ring_mac, ring_name, state,
    phase, cycle, avg_bdr, battery_current, firmware_version,
    phase_start_time, last_charge_change_time,
    saved_at, updated_at
) VALUES (
    %(serial_number)s, %(machine)s, %(slot)s, %(ring_mac)s, %(ring_name)s, %(state)s,
    %(phase)s, %(cycle)s, %(avg_bdr)s, %(battery_current)s, %(firmware_version)s,
    %(phase_start_time)s, %(last_charge_change_time)s,
    %(saved_at)s, now()
)
ON CONFLICT (serial_number, machine) DO UPDATE SET
    slot            = EXCLUDED.slot,
    ring_mac        = EXCLUDED.ring_mac,
    ring_name       = EXCLUDED.ring_name,
    state           = EXCLUDED.state,
    phase           = EXCLUDED.phase,
    cycle           = EXCLUDED.cycle,
    avg_bdr         = EXCLUDED.avg_bdr,
    battery_current = EXCLUDED.battery_current,
    firmware_version = EXCLUDED.firmware_version,
    phase_start_time          = EXCLUDED.phase_start_time,
    last_charge_change_time   = EXCLUDED.last_charge_change_time,
    saved_at        = EXCLUDED.saved_at,
    updated_at      = now()
WHERE EXCLUDED.saved_at > ring_status.saved_at
"""


def upsert_ring_status(conn, record):
    """Upsert a single record into ring_status.

    The WHERE EXCLUDED.saved_at > ring_status.saved_at clause in the
    ON CONFLICT ensures that an older (or out-of-order) snapshot can
    never overwrite a newer one.
    """
    with conn.cursor() as cur:
        cur.execute(UPSERT_SQL, record)


def upsert_ring_status_batch(conn, records):
    """Upsert multiple records in one transaction."""
    with conn.cursor() as cur:
        for record in records:
            cur.execute(UPSERT_SQL, record)


# ---------------------------------------------------------------------------
# High-level: ingest a single archive JSON file
# ---------------------------------------------------------------------------

def ingest_file_to_ring_status(conn, file_path):
    """Parse a snapshot JSON file and upsert every slot into ring_status.

    file_path can be a string or Path.  machine is derived from the
    directory layout: archive/{machine}/{date}/{time}.json

    Returns the number of rows upserted.
    """
    fp = Path(file_path)
    if not fp.is_file():
        return 0

    machine = fp.parent.parent.name  # archive/{machine}/...
    with open(fp, "r", encoding="utf-8") as f:
        snap = json.load(f)

    saved_at_str = snap.get("saved_at", "")
    saved_at = _parse_saved_at(saved_at_str)
    slots = snap.get("slots", {})

    count = 0
    records = []
    for slot_num, slot_dict in slots.items():
        if not isinstance(slot_dict, dict):
            continue
        rec = extract_slot(machine, saved_at, slot_num, slot_dict)
        if rec is not None:
            records.append(rec)

    if records:
        upsert_ring_status_batch(conn, records)
        count = len(records)

    return count
