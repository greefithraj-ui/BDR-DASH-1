r"""backfill_ring_status.py - Full-history backfill: walks every archive file
per machine, finds the latest snapshot per (serial, machine) pair, and
upserts into ring_status.

Walks:  D:\BDR\DESTINATION\archive\{machine}\{date}\{time}.json
For each machine folder, processes ALL files (not just the latest one).
For each distinct serial found in that machine's history, keeps only the
file with the most recent saved_at, and upserts that as the row for
that (serial, machine) pair.

Usage:
    python backfill_ring_status.py                     # all machines
    python backfill_ring_status.py --test aqc-19 aqc-44  # test on 2 machines
"""

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from postgres_db import get_connection
from ring_status import extract_slot, _parse_saved_at, upsert_ring_status_batch

ARCHIVE_ROOT = Path(r"D:\BDR\DESTINATION\archive")


def scan_machine_all_files(machine_dir):
    """Walk every JSON file under a machine directory.

    Returns dict: {serial_number: (saved_at_str, saved_at_dt, slot_num, slot_dict, file_path)}
    Only keeps the entry with the latest saved_at per serial.
    """
    time_pat = re.compile(r"^(\d{2})-(\d{2})-(\d{2})$")
    serials = {}  # serial_lower -> (saved_at_str, saved_at_dt, slot_num, slot_dict, file_path)

    for date_dir in sorted(machine_dir.iterdir()):
        if not date_dir.is_dir():
            continue
        for json_file in date_dir.glob("*.json"):
            time_str = json_file.stem
            if not time_pat.match(time_str):
                continue
            try:
                raw = json_file.read_text("utf-8", errors="replace")
                snap = json.loads(raw)
            except Exception:
                continue

            saved_at_str = snap.get("saved_at", "")
            saved_at_dt = _parse_saved_at(saved_at_str)
            slots = snap.get("slots", {})

            for slot_num, slot_dict in slots.items():
                if not isinstance(slot_dict, dict):
                    continue
                sn = (slot_dict.get("serial_number") or "").strip()
                if not sn or sn in ("--", "N/A"):
                    continue
                sn_lower = sn.lower()
                # Keep only the latest snapshot per serial
                if sn_lower not in serials or saved_at_dt > serials[sn_lower][1]:
                    serials[sn_lower] = (saved_at_str, saved_at_dt, slot_num, slot_dict, str(json_file))

    return serials


def main():
    # Parse optional --test flag for limiting to specific machines
    test_machines = None
    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        test_machines = set(sys.argv[idx + 1:])
        print("TEST MODE: processing only machines:", sorted(test_machines))

    print("Scanning archive root:", ARCHIVE_ROOT)
    if not ARCHIVE_ROOT.is_dir():
        print("Archive root does not exist!")
        return

    # Discover machine folders
    machine_dirs = []
    for d in sorted(ARCHIVE_ROOT.iterdir()):
        if not d.is_dir():
            continue
        if test_machines and d.name not in test_machines:
            continue
        machine_dirs.append(d)

    print("Found %d machine folders to process\n" % len(machine_dirs))

    # Phase 1: Scan all files, find latest per (serial, machine)
    print("=" * 70)
    print("PHASE 1: Scanning all archive files per machine...")
    print("=" * 70)
    t0 = time.time()
    total_files = 0
    all_records = []  # list of extracted records for upsert
    machine_stats = []

    for mdir in machine_dirs:
        machine_name = mdir.name
        serials = scan_machine_all_files(mdir)
        file_count = sum(1 for _ in mdir.rglob("*.json"))
        total_files += file_count

        records = []
        for sn_lower, (saved_at_str, saved_at_dt, slot_num, slot_dict, fpath) in serials.items():
            rec = extract_slot(machine_name, saved_at_dt, slot_num, slot_dict)
            if rec is not None:
                records.append(rec)

        all_records.extend(records)
        machine_stats.append((machine_name, file_count, len(serials), len(records)))
        print("  %-12s  %5d files  %4d serials  %4d records" % (
            machine_name, file_count, len(serials), len(records)))

    elapsed_scan = time.time() - t0
    print("\nPhase 1 complete: %d files scanned, %d total records in %.1fs" % (
        total_files, len(all_records), elapsed_scan))

    # Summary
    print("\n" + "=" * 70)
    print("PHASE 2: Upserting into ring_status...")
    print("=" * 70)
    t1 = time.time()

    conn = get_connection()
    try:
        upsert_ring_status_batch(conn, all_records)
        conn.commit()
        elapsed_upsert = time.time() - t1
        print("Upserted %d records in %.1fs" % (len(all_records), elapsed_upsert))
    except Exception as e:
        conn.rollback()
        print("ERROR during upsert:", e)
        raise
    finally:
        conn.close()

    total_elapsed = time.time() - t0
    print("\nBackfill complete. Total: %d files, %d records, %.1fs total" % (
        total_files, len(all_records), total_elapsed))


if __name__ == "__main__":
    main()
