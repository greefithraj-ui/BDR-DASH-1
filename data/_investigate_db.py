"""Part 1 & 2: ring_status + archive_entries queries (fast, DB only)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from postgres_db import get_connection, init_db, search_archive_in_pg
import psycopg2.extras

SERIAL_TARGET = "RA-CH3-HF3-WB-AS09-0000111"
GROUND_TRUTH = "RA-CH2-LFK-W1-MG07-0000106"


def rs_query(serial):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM ring_status WHERE serial_number = %s ORDER BY machine", (serial,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def ae_query(serial_lower):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (content->>'machine')
                    content->>'machine' as machine,
                    content->>'saved_at' as saved_at,
                    content->>'state' as state,
                    content->>'avg_bdr' as avg_bdr,
                    content->>'cycle' as cycle
                FROM archive_entries
                WHERE serial_lower = %s
                ORDER BY content->>'machine', content->>'saved_at' DESC
            """, (serial_lower,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def old_path(serial_key):
    pg = search_archive_in_pg([serial_key])
    return pg.get(serial_key, [])


def dual_machines_rs():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT serial_number, COUNT(DISTINCT machine) as mc
                FROM ring_status
                GROUP BY serial_number
                HAVING COUNT(DISTINCT machine) >= 2
            """)
            return [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        conn.close()


def show(serial, label):
    print(f"\n{'='*90}")
    print(f"  {label}: {serial}")
    print(f"{'='*90}")

    rs = rs_query(serial)
    rs_machines = sorted(set(r["machine"] for r in rs))
    print(f"\n  ring_status ({len(rs)} rows):")
    for r in rs:
        print(f"    machine={r['machine']}  state={r['state']}  saved_at={r['saved_at']}  "
              f"phase={r.get('phase')}  cycle={r.get('cycle')}  avg_bdr={r.get('avg_bdr')}")

    ae = ae_query(serial.lower())
    ae_machines = sorted(set(r["machine"] for r in ae))
    print(f"\n  archive_entries PG ({len(ae)} rows, latest per machine):")
    for r in ae:
        print(f"    machine={r['machine']}  saved_at={r['saved_at']}  state={r['state']}  avg_bdr={r['avg_bdr']}  cycle={r['cycle']}")

    old = old_path(serial.lower())
    old_machines = sorted(set(r.get("machine","") for r in old))
    print(f"\n  old merge path ({len(old)} rows):")
    print(f"    machines: {old_machines}")

    print(f"\n  COVERAGE:")
    print(f"    ring_status:        {rs_machines}")
    print(f"    archive_entries PG: {ae_machines}")
    print(f"    old merge path:     {old_machines}")

    return rs_machines, ae_machines, old_machines


def main():
    init_db()

    # Target serial
    rs_m, ae_m, old_m = show(SERIAL_TARGET, "TARGET")

    # Ground truth serial
    rs_m2, ae_m2, old_m2 = show(GROUND_TRUTH, "GROUND TRUTH")

    # Other dual-machine serials
    duals = dual_machines_rs()
    print(f"\n{'='*90}")
    print(f"  ALL SERIALS ON 2+ MACHINES IN ring_status: {len(duals)}")
    print(f"{'='*90}")
    for sn, mc in duals:
        print(f"  {sn}: {mc} machines")

    # Check 3 more
    for sn, _ in duals[:3]:
        show(sn, "DUAL-MACHINE CHECK")

    # Check ground truth against raw files using archive_entries
    print(f"\n{'='*90}")
    print(f"  GROUND TRUTH DEEP DIVE: {GROUND_TRUTH}")
    print(f"{'='*90}")
    print(f"\n  archive_entries has these machines:")
    ae = ae_query(GROUND_TRUTH.lower())
    for r in ae:
        print(f"    {r['machine']}: saved_at={r['saved_at']}  state={r['state']}  avg_bdr={r['avg_bdr']}")

    print(f"\n  ring_status has these machines:")
    rs = rs_query(GROUND_TRUTH)
    for r in rs:
        print(f"    {r['machine']}: saved_at={r['saved_at']}  state={r['state']}  avg_bdr={r.get('avg_bdr')}")

    # Compare
    ae_machines = set(r["machine"] for r in ae)
    rs_machines = set(r["machine"] for r in rs)
    missing_in_rs = ae_machines - rs_machines
    missing_in_ae = rs_machines - ae_machines
    if missing_in_rs:
        print(f"\n  ** ring_status MISSING from archive_entries: {sorted(missing_in_rs)}")
        for m in sorted(missing_in_rs):
            ae_row = [r for r in ae if r["machine"] == m][0]
            rs_row = [r for r in rs]
            print(f"     {m}: archive_entries saved_at={ae_row['saved_at']}")
            for r in rs_row:
                print(f"       vs ring_status {r['machine']}: saved_at={r['saved_at']}")
    if missing_in_ae:
        print(f"\n  ** archive_entries MISSING from ring_status: {sorted(missing_in_ae)}")
    if not missing_in_rs and not missing_in_ae:
        print(f"\n  MATCH: both have same machines")


if __name__ == "__main__":
    main()
