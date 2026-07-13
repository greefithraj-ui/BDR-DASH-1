"""Investigation script for machine-coverage issues."""
import sys, os, json, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
from postgres_db import get_connection, init_db, search_archive_in_pg
import psycopg2.extras

SERIAL_TARGET = "RA-CH3-HF3-WB-AS09-0000111"
GROUND_TRUTH_SERIAL = "RA-CH2-LFK-W1-MG07-0000106"
ARCHIVE_ROOT = Path(r"D:\BDR\DESTINATION\archive")


def search_raw_files(serial_lower):
    """Scan raw archive JSON files for a serial. Returns {machine: (file_path, saved_at)}."""
    results = {}
    for machine_dir in sorted(ARCHIVE_ROOT.iterdir()):
        if not machine_dir.is_dir():
            continue
        latest_file = None
        latest_saved = None
        for json_file in machine_dir.rglob("*.json"):
            try:
                text = json_file.read_text("utf-8", errors="replace")
                if serial_lower not in text.lower():
                    continue
                data = json.loads(text)
                saved = data.get("saved_at", "")
                for slot_id, slot in data.get("slots", {}).items():
                    sn = (slot.get("serial_number") or "").strip().lower()
                    if sn == serial_lower:
                        if latest_saved is None or saved > latest_saved:
                            latest_saved = saved
                            latest_file = json_file
                        break
            except Exception:
                continue
        if latest_file:
            results[machine_dir.name] = (str(latest_file), latest_saved)
    return results


def search_ring_status(serial):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM ring_status WHERE serial_number = %s ORDER BY machine", (serial,))
            rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


def search_archive_entries(serial_lower):
    """Query archive_entries for all machines this serial appears on, with latest saved_at per machine."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            # Get latest snapshot per machine
            cur.execute("""
                SELECT DISTINCT ON (content->>'machine')
                    content->>'machine' as machine,
                    content->>'saved_at' as saved_at,
                    content->>'state' as state,
                    content->>'avg_bdr' as avg_bdr
                FROM archive_entries
                WHERE serial_lower = %s
                ORDER BY content->>'machine', content->>'saved_at' DESC
            """, (serial_lower,))
            rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
    return rows


def search_old_path(serial_key):
    """Run the old merge path and return results."""
    pg = search_archive_in_pg([serial_key])
    return pg.get(serial_key, [])


def compare_off_by_one(serial):
    """Compare bdr_state.cycle vs len(completed_cycles) for a serial."""
    # Find a raw file containing this serial
    serial_lower = serial.lower()
    for machine_dir in ARCHIVE_ROOT.iterdir():
        if not machine_dir.is_dir():
            continue
        for json_file in machine_dir.rglob("*.json"):
            try:
                text = json_file.read_text("utf-8", errors="replace")
                if serial_lower not in text.lower():
                    continue
                data = json.loads(text)
                for slot_id, slot in data.get("slots", {}).items():
                    sn = (slot.get("serial_number") or "").strip().lower()
                    if sn != serial_lower:
                        continue
                    bdr_state = slot.get("bdr_state") or {}
                    bdr_data = slot.get("bdr_data") or {}
                    completed_cycles_list = bdr_state.get("completed_cycles") or []
                    bdr_state_cycle = bdr_state.get("cycle")
                    bdr_data_final_cycle = bdr_data.get("final_cycle")
                    bdr_data_avg = bdr_data.get("avg_bdr")
                    return {
                        "file": str(json_file),
                        "machine": machine_dir.name,
                        "saved_at": data.get("saved_at"),
                        "slot": slot_id,
                        "state": slot.get("state"),
                        "bdr_state_cycle": bdr_state_cycle,
                        "bdr_data_final_cycle": bdr_data_final_cycle,
                        "len_completed_cycles": len(completed_cycles_list) if isinstance(completed_cycles_list, list) else "not_a_list",
                        "completed_cycles_type": type(completed_cycles_list).__name__,
                        "bdr_data_avg": bdr_data_avg,
                        "bdr_state_avg": bdr_state.get("avg_bdr"),
                    }
            except Exception:
                continue
    return None


def print_header(title):
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}")


def main():
    init_db()

    # ================================================================
    # PART 1: RA-CH3-HF3-WB-AS09-0000111
    # ================================================================
    print_header(f"PART 1: ring_status rows for {SERIAL_TARGET}")
    rs_rows = search_ring_status(SERIAL_TARGET)
    print(f"  ring_status rows: {len(rs_rows)}")
    for r in rs_rows:
        print(f"  machine={r['machine']}  state={r['state']}  saved_at={r['saved_at']}  "
              f"phase={r.get('phase')}  cycle={r.get('cycle')}  avg_bdr={r.get('avg_bdr')}")

    print_header(f"PART 1: raw archive files for {SERIAL_TARGET}")
    raw = search_raw_files(SERIAL_TARGET.lower())
    print(f"  Raw files found across {len(raw)} machine(s):")
    for machine, (fp, saved) in sorted(raw.items()):
        print(f"  {machine}: saved_at={saved}  file={fp}")

    print_header(f"PART 1: archive_entries (old PG) for {SERIAL_TARGET}")
    ae_rows = search_archive_entries(SERIAL_TARGET.lower())
    print(f"  archive_entries machines: {len(ae_rows)}")
    for r in ae_rows:
        print(f"  machine={r['machine']}  saved_at={r['saved_at']}  state={r['state']}  avg_bdr={r['avg_bdr']}")

    print_header(f"PART 1: old merge path for {SERIAL_TARGET}")
    old_rows = search_old_path(SERIAL_TARGET.lower())
    old_machines = sorted(set(r.get("machine","") for r in old_rows))
    print(f"  Old path rows: {len(old_rows)}  machines: {old_machines}")

    # Compare
    raw_machines = set(raw.keys())
    rs_machines = set(r["machine"] for r in rs_rows)
    ae_machines = set(r["machine"] for r in ae_rows)
    old_machines_set = set(old_machines)

    print_header(f"PART 1: MACHINE COVERAGE COMPARISON")
    print(f"  Raw files:          {sorted(raw_machines)}")
    print(f"  ring_status:        {sorted(rs_machines)}")
    print(f"  archive_entries PG: {sorted(ae_machines)}")
    print(f"  old merge path:     {sorted(old_machines_set)}")

    missing_in_rs = raw_machines - rs_machines
    extra_in_rs = rs_machines - raw_machines
    if missing_in_rs:
        print(f"  ** MISSING from ring_status: {sorted(missing_in_rs)}")
    if extra_in_rs:
        print(f"  ** EXTRA in ring_status: {sorted(extra_in_rs)}")
    if not missing_in_rs and not extra_in_rs:
        print(f"  ring_status matches raw files EXACTLY")

    missing_in_ae = raw_machines - ae_machines
    if missing_in_ae:
        print(f"  ** MISSING from archive_entries: {sorted(missing_in_ae)}")

    # Determine root cause for ring_status gaps
    if missing_in_rs:
        print_header(f"PART 1: ROOT CAUSE ANALYSIS for ring_status gaps")
        for m in sorted(missing_in_rs):
            raw_file, raw_saved = raw[m]
            print(f"\n  Machine '{m}':")
            print(f"    Raw file saved_at: {raw_saved}")
            print(f"    Raw file path: {raw_file}")

            # Check if archive_entries has this machine
            ae_for_machine = [r for r in ae_rows if r["machine"] == m]
            if ae_for_machine:
                print(f"    archive_entries has it: YES (saved_at={ae_for_machine[0]['saved_at']})")
            else:
                print(f"    archive_entries has it: NO -- this machine's data was never ingested to PG")

            # Check if ring_status has any data for this serial at all
            rs_for_serial = [r for r in rs_rows]
            if rs_for_serial:
                print(f"    ring_status has this serial on other machines: YES")
                # Check staleness guard
                for rsr in rs_for_serial:
                    print(f"      {rsr['machine']}: saved_at={rsr['saved_at']}")
                    if raw_saved and str(raw_saved) <= str(rsr['saved_at']):
                        print(f"        -> staleness guard would REJECT ({raw_saved} <= {rsr['saved_at']})")
                    else:
                        print(f"        -> staleness guard would ACCEPT ({raw_saved} > {rsr['saved_at']})")
            else:
                print(f"    ring_status has this serial on ANY machine: NO")

    # ================================================================
    # PART 2: 3 other serials that moved machines
    # ================================================================
    print_header(f"PART 2: Other serials that moved machines")

    # Find serials with multiple machines in raw files
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT serial_number, COUNT(DISTINCT machine) as mc
                FROM ring_status
                GROUP BY serial_number
                HAVING COUNT(DISTINCT machine) >= 2
                LIMIT 10
            """)
            dual_serials = [(r[0], r[1]) for r in cur.fetchall()]
    finally:
        conn.close()

    print(f"  Serials on 2+ machines in ring_status: {len(dual_serials)}")
    for sn, mc in dual_serials:
        print(f"    {sn}: {mc} machines")

    for sn, _ in dual_serials[:3]:
        print_header(f"  Checking {sn}")
        rs = search_ring_status(sn)
        rs_m = sorted(set(r["machine"] for r in rs))
        raw = search_raw_files(sn.lower())
        raw_m = sorted(raw.keys())
        print(f"    Raw files:   {raw_m}")
        print(f"    ring_status: {rs_m}")
        missing = set(raw_m) - set(rs_m)
        if missing:
            print(f"    MISSING from ring_status: {sorted(missing)}")
            for m in sorted(missing):
                fp, saved = raw[m]
                print(f"      {m}: saved_at={saved}  file={fp}")
        else:
            print(f"    MATCH")

    # ================================================================
    # PART 3: Ground truth test RA-CH2-LFK-W1-MG07-0000106
    # ================================================================
    print_header(f"PART 3: GROUND TRUTH - {GROUND_TRUTH_SERIAL}")

    print(f"\n  [a] Raw archive files:")
    raw = search_raw_files(GROUND_TRUTH_SERIAL.lower())
    print(f"  Found across {len(raw)} machine(s):")
    for machine, (fp, saved) in sorted(raw.items()):
        print(f"    {machine}: saved_at={saved}")
        print(f"      file={fp}")

    print(f"\n  [b] Old merge path:")
    old_key = GROUND_TRUTH_SERIAL.lower()
    old_rows = search_old_path(old_key)
    old_machines = sorted(set(r.get("machine","") for r in old_rows))
    print(f"  Old path rows: {len(old_rows)}  machines: {old_machines}")

    print(f"\n  [c] ring_status:")
    rs_rows = search_ring_status(GROUND_TRUTH_SERIAL)
    rs_machines = sorted(set(r["machine"] for r in rs_rows))
    print(f"  ring_status rows: {len(rs_rows)}  machines: {rs_machines}")
    for r in rs_rows:
        print(f"    machine={r['machine']}  state={r['state']}  saved_at={r['saved_at']}  avg_bdr={r.get('avg_bdr')}")

    print(f"\n  [d] Coverage comparison:")
    raw_machines = set(raw.keys())
    print(f"    Raw files:   {sorted(raw_machines)}")
    print(f"    ring_status: {rs_machines}")
    print(f"    old path:    {old_machines}")

    missing_rs = raw_machines - set(rs_machines)
    missing_old = raw_machines - set(old_machines)
    if missing_rs:
        print(f"    ** ring_status MISSING: {sorted(missing_rs)}")
        for m in sorted(missing_rs):
            fp, saved = raw[m]
            print(f"      {m}: raw saved_at={saved}")
            # Why?
            ae = search_archive_entries(GROUND_TRUTH_SERIAL.lower())
            ae_m = [r for r in ae if r["machine"] == m]
            if ae_m:
                print(f"        archive_entries has it: YES (saved_at={ae_m[0]['saved_at']})")
            else:
                print(f"        archive_entries has it: NO -- never ingested to PG")
            # Check staleness
            for rsr in rs_rows:
                if raw_saved := saved:
                    if str(raw_saved) <= str(rsr['saved_at']):
                        print(f"        staleness guard: WOULD REJECT ({raw_saved} <= {rsr['saved_at']})")
                    else:
                        print(f"        staleness guard: WOULD ACCEPT ({raw_saved} > {rsr['saved_at']})")
    else:
        print(f"    ring_status matches raw files: ALL {len(raw_machines)} machines present")

    if missing_old:
        print(f"    ** old path MISSING: {sorted(missing_old)}")

    if not missing_rs and missing_old:
        print(f"\n  [e] CONCLUSION: ring_status returns BOTH machines (correct).")
        print(f"      old path MISSES {sorted(missing_old)} (confirmed bug in old path).")
        print(f"      ring_status fixes this class of bug.")

    # ================================================================
    # PART 4: Off-by-one investigation
    # ================================================================
    print_header(f"PART 4: Off-by-one: bdr_state.cycle vs len(completed_cycles)")

    test_off_by_one = [
        "RA-CH3-LFK-W1-AG08-0000206",
        "RA-CH3-LFK-W1-AS07-0000141",
        "RA-CH2-IR3-W1-RT06-E83",
    ]

    for sn in test_off_by_one:
        print(f"\n  {sn}:")
        info = compare_off_by_one(sn)
        if info:
            print(f"    file: {info['file']}")
            print(f"    machine: {info['machine']}  saved_at: {info['saved_at']}")
            print(f"    state: {info['state']}")
            print(f"    bdr_state.cycle:          {info['bdr_state_cycle']}")
            print(f"    bdr_data.final_cycle:     {info['bdr_data_final_cycle']}")
            print(f"    len(completed_cycles):    {info['len_completed_cycles']}  (type={info['completed_cycles_type']})")
            print(f"    bdr_data.avg_bdr:         {info['bdr_data_avg']}")
        else:
            print(f"    (no raw file found)")


if __name__ == "__main__":
    main()
