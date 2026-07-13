"""Side-by-side comparison: old three-tier merge vs ring_status for real serials.

Usage:
    python compare_ring_status.py           # pick 8 serials automatically
    python compare_ring_status.py RA-CH2-IN2-W1-RT06-454 RA-CH2-IR3-W1-RT07-X47 ...
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from postgres_db import get_connection, init_db
from postgres_db import search_archive_in_pg
from api import _search_ring_status_for_serials, _parse_old_data_serials

import psycopg2.extras

# ── Fields to compare ────────────────────────────────────────────────────────
COMPARE_FIELDS = [
    "serial_number", "machine", "state", "avg_bdr", "cycle",
    "phase", "saved_at", "firmware_version", "ring_mac",
    "battery_current",
]


def get_sample_serials(n=8):
    """Pull n real serials from ring_status."""
    pg = get_connection()
    try:
        with pg.cursor() as cur:
            cur.execute("""
                SELECT serial_number
                FROM   ring_status
                ORDER  BY saved_at DESC
                LIMIT  %s
            """, (n,))
            rows = cur.fetchall()
    finally:
        pg.close()
    return [r[0] for r in rows]


def normalise(entry):
    """Pick only the comparable fields from an entry dict."""
    return {k: entry.get(k) for k in COMPARE_FIELDS}


def main():
    serials = sys.argv[1:] if len(sys.argv) > 1 else get_sample_serials(8)
    if not serials:
        print("No serials found.")
        return

    print(f"\n{'='*90}")
    print(f"  Comparing OLD (three-tier merge) vs NEW (ring_status) for {len(serials)} serial(s)")
    print(f"{'='*90}\n")

    for serial in serials:
        parsed = _parse_old_data_serials([serial])
        key = parsed[0]["key"] if parsed else serial.lower()

        # -- Old path --
        old_map = search_archive_in_pg([key])
        old_entries = old_map.get(key, [])

        # -- New path --
        new_map = _search_ring_status_for_serials([key])
        new_entries = new_map.get(key, [])

        print(f"-- {serial} --")
        print(f"   OLD path: {len(old_entries)} row(s)   |   NEW path: {len(new_entries)} row(s)")

        if not old_entries and not new_entries:
            print("   (no data in either path)\n")
            continue

        # Collect all machines seen across both paths
        all_machines = sorted({
            e.get("machine", "") for e in old_entries + new_entries
        })

        for machine in all_machines:
            old_for_m = [e for e in old_entries if e.get("machine", "") == machine]
            new_for_m = [e for e in new_entries if e.get("machine", "") == machine]

            # Use the first row per machine (latest snapshot) for comparison
            old_row = old_for_m[0] if old_for_m else {}
            new_row = new_for_m[0] if new_for_m else {}

            old_n = normalise(old_row)
            new_n = normalise(new_row)

            # Header
            print(f"\n   Machine: {machine or '(none)'}")
            print(f"   {'Field':<22} {'OLD':<30} {'NEW':<30} {'Match?':<8}")
            print(f"   {'-'*22} {'-'*30} {'-'*30} {'-'*8}")

            for field in COMPARE_FIELDS:
                ov = old_n.get(field, "")
                nv = new_n.get(field, "")

                # Truncate long strings for display
                ov_s = str(ov) if ov is not None else "(null)"
                nv_s = str(nv) if nv is not None else "(null)"
                if len(ov_s) > 28:
                    ov_s = ov_s[:25] + "..."
                if len(nv_s) > 28:
                    nv_s = nv_s[:25] + "..."

                # Compare (treat None and empty string as equivalent)
                o_cmp = ov if ov is not None else ""
                n_cmp = nv if nv is not None else ""

                # Treat int/float equality as equivalent (e.g. 85 == 85.0)
                try:
                    if float(o_cmp) == float(n_cmp):
                        match = "OK"
                    else:
                        match = "DIFF"
                except (TypeError, ValueError):
                    match = "OK" if str(o_cmp) == str(n_cmp) else "DIFF"

                print(f"   {field:<22} {ov_s:<30} {nv_s:<30} {match:<8}")

        print()


if __name__ == "__main__":
    init_db()
    main()
