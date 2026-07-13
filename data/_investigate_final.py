"""Final targeted investigation."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from postgres_db import get_connection, init_db
import psycopg2.extras

GROUND_TRUTH = "RA-CH2-LFK-W1-MG07-0000106"
TARGET = "RA-CH3-HF3-WB-AS09-0000111"


def query_archive_entries_all(serial_lower):
    """Get ALL rows from archive_entries for this serial, grouped by machine."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT 
                    content->>'machine' as machine,
                    content->>'saved_at' as saved_at,
                    content->>'state' as state,
                    content->>'slot' as slot,
                    content->>'avg_bdr' as avg_bdr,
                    content->>'cycle' as cycle,
                    content->>'file_path' as file_path
                FROM archive_entries
                WHERE serial_lower = %s
                ORDER BY content->>'machine', content->>'saved_at' DESC
            """, (serial_lower,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def main():
    init_db()

    for serial, label in [(GROUND_TRUTH, "GROUND TRUTH"), (TARGET, "TARGET")]:
        sl = serial.lower()
        print(f"\n{'='*90}")
        print(f"  {label}: {serial}")
        print(f"{'='*90}")

        rows = query_archive_entries_all(sl)
        print(f"  Total archive_entries rows: {len(rows)}")

        # Group by machine
        machines = {}
        for r in rows:
            m = r["machine"]
            if m not in machines:
                machines[m] = []
            machines[m].append(r)

        print(f"  Machines found: {sorted(machines.keys())}")
        for m in sorted(machines.keys()):
            mrows = machines[m]
            print(f"\n    {m}: {len(mrows)} row(s)")
            # Show latest and earliest
            print(f"      Latest: saved_at={mrows[0]['saved_at']}  state={mrows[0]['state']}  "
                  f"avg_bdr={mrows[0]['avg_bdr']}  cycle={mrows[0]['cycle']}")
            if len(mrows) > 1:
                print(f"      Earliest: saved_at={mrows[-1]['saved_at']}  state={mrows[-1]['state']}")
            # Show file_path for latest
            fp = mrows[0].get("file_path", "")
            if fp:
                print(f"      file_path: {fp}")

    # Also check: does the ground truth serial appear in ring_status at all?
    print(f"\n{'='*90}")
    print(f"  RING_STATUS CHECK")
    print(f"{'='*90}")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM ring_status WHERE serial_number = %s", (GROUND_TRUTH,))
            rs_rows = cur.fetchall()
            print(f"  ring_status for {GROUND_TRUTH}: {len(rs_rows)} rows")
            for r in rs_rows:
                print(f"    {dict(zip([d[0] for d in cur.description], r))}")
    finally:
        conn.close()

    # Check: what's the earliest file_path in archive_entries for the ground truth?
    print(f"\n{'='*90}")
    print(f"  FILE PATHS for {GROUND_TRUTH}")
    print(f"{'='*90}")
    gt_rows = query_archive_entries_all(GROUND_TRUTH.lower())
    for r in gt_rows:
        print(f"  machine={r['machine']}  saved_at={r['saved_at']}  file_path={r.get('file_path','(empty)')}")

    # Check: what did the backfill actually process? Show machines with ring_status data
    print(f"\n{'='*90}")
    print(f"  ALL ring_status machines")
    print(f"{'='*90}")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT machine FROM ring_status ORDER BY machine")
            all_machines = [r[0] for r in cur.fetchall()]
            print(f"  ring_status has data for {len(all_machines)} machines: {all_machines}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
