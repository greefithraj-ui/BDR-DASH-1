"""Rigorous A/B verification: old merge path vs ring_status path.

NO CODE CHANGES -- this is read-only verification.
Avoids importing from api.py to prevent module-level side effects.
"""
import sys, os, json, time, re
sys.path.insert(0, os.path.dirname(__file__))

from postgres_db import get_connection, init_db
import psycopg2.extras


COMPARE_FIELDS = [
    "serial_number", "machine", "state", "avg_bdr", "cycle", "phase",
    "saved_at", "firmware_version", "ring_mac", "battery_current",
    "test_start", "start_time", "snapshots", "total_cycles",
    "completed_cycles", "file_path",
]


def parse_serial(values):
    if isinstance(values, str):
        candidates = re.split(r"[\n,;]+", values)
    elif isinstance(values, (list, tuple, set)):
        candidates = []
        for v in values:
            candidates.extend(re.split(r"[\n,;]+", str(v or "")))
    else:
        candidates = [str(values or "")]
    parsed = []
    seen = set()
    for c in candidates:
        s = c.strip()
        if not s:
            continue
        sk = s.lower()
        if sk in seen:
            continue
        seen.add(sk)
        parsed.append({"serial": s, "key": sk})
    return parsed


def search_old_path(serial_keys):
    """Replicate the old three-tier merge: PG archive_entries + SQLite."""
    results_map = {k: [] for k in serial_keys}

    # Source 1: PostgreSQL archive_entries
    try:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT content
                    FROM archive_entries
                    WHERE serial_lower = ANY(%s)
                    ORDER BY serial_lower, machine, saved_at DESC
                """, (serial_keys,))
                rows = cur.fetchall()
            grouped = {}
            for row in rows:
                rec = row["content"]
                if not rec:
                    continue
                s_lower = str(rec.get("serial_number", "")).lower()
                machine = rec.get("machine", "")
                combo = (s_lower, machine)
                if combo not in grouped:
                    grouped[combo] = []
                grouped[combo].append(rec)

            for (s_lower, machine), recs in grouped.items():
                # Find best historical BDR
                best = None
                for r in recs:
                    avg = r.get("avg_bdr")
                    if avg is not None and avg != 0.0:
                        best = r
                        break
                for i, rec in enumerate(recs):
                    is_latest = (i == 0)
                    is_stale = rec.get("avg_bdr_is_stale", False) or rec.get("avg_bdr") is None or rec.get("avg_bdr") == 0.0
                    fa = rec.get("avg_bdr")
                    if is_stale and best:
                        fa = best.get("avg_bdr")
                    if s_lower in results_map:
                        results_map[s_lower].append({
                            "type": "latest" if is_latest else "history",
                            "serial_number": rec.get("serial_number", ""),
                            "machine": machine,
                            "date": rec.get("date", ""),
                            "time": rec.get("time", ""),
                            "slot": rec.get("slot"),
                            "state": rec.get("state", ""),
                            "battery_current": rec.get("battery_current"),
                            "firmware_version": rec.get("firmware_version", ""),
                            "ring_mac": rec.get("ring_mac", ""),
                            "ring_name": rec.get("ring_name", ""),
                            "avg_bdr": fa,
                            "machine_avg_bdr": fa,
                            "avg_bdr_is_stale": False if best else rec.get("avg_bdr_is_stale", False),
                            "stored_avg_bdr": rec.get("stored_avg_bdr"),
                            "inter_cycle_avg_bdr": rec.get("inter_cycle_avg_bdr"),
                            "test_start": rec.get("test_start") or rec.get("start_time"),
                            "phase": rec.get("phase"),
                            "cycle": rec.get("cycle"),
                            "snapshots": rec.get("snapshots", 1),
                            "total_cycles": rec.get("total_cycles", 0),
                            "completed_cycles": rec.get("completed_cycles", 0),
                            "completed_workouts": rec.get("completed_workouts"),
                            "start_time": rec.get("start_time") or rec.get("test_start"),
                            "last_update": rec.get("saved_at", ""),
                            "saved_at": rec.get("saved_at", ""),
                            "file_path": rec.get("file_path", ""),
                        })
        finally:
            conn.close()
    except Exception as e:
        print(f"  [OLD PG ERROR] {e}")

    return results_map


def search_new_path(serial_keys):
    """Query ring_status table."""
    results_map = {k: [] for k in serial_keys}
    try:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM ring_status
                    WHERE LOWER(serial_number) = ANY(%s)
                       OR LOWER(machine) = ANY(%s)
                    ORDER BY serial_number, machine
                """, (serial_keys, serial_keys))
                rows = cur.fetchall()
        finally:
            conn.close()
    except Exception as e:
        print(f"  [NEW RS ERROR] {e}")
        return results_map

    for row in rows:
        rec = dict(row)
        sn_lower = str(rec.get("serial_number", "")).lower()
        machine = rec.get("machine", "")

        matched = [k for k in serial_keys if k == sn_lower or k == machine.lower()]
        if not matched:
            continue

        saved_at_val = rec.get("saved_at")
        if saved_at_val is not None and hasattr(saved_at_val, "isoformat"):
            saved_at_val = saved_at_val.isoformat()
        elif saved_at_val is not None:
            saved_at_val = str(saved_at_val)

        phase_start_val = rec.get("phase_start_time")
        if phase_start_val is not None and hasattr(phase_start_val, "isoformat"):
            phase_start_val = phase_start_val.isoformat()
        elif phase_start_val is not None:
            phase_start_val = str(phase_start_val)

        entry = {
            "type": "latest",
            "serial_number": rec.get("serial_number", ""),
            "machine": machine,
            "state": rec.get("state", "") or "",
            "battery_current": rec.get("battery_current"),
            "firmware_version": rec.get("firmware_version", "") or "",
            "ring_mac": rec.get("ring_mac", "") or "",
            "ring_name": rec.get("ring_name", "") or "",
            "avg_bdr": rec.get("avg_bdr"),
            "machine_avg_bdr": rec.get("avg_bdr"),
            "avg_bdr_is_stale": False,
            "avg_bdr_is_estimated": False,
            "stored_avg_bdr": None,
            "inter_cycle_avg_bdr": None,
            "test_start": phase_start_val,
            "phase": rec.get("phase", "") or "",
            "cycle": rec.get("cycle"),
            "snapshots": 1,
            "total_cycles": rec.get("cycle"),
            "completed_cycles": rec.get("cycle"),
            "completed_workouts": None,
            "start_time": phase_start_val,
            "last_update": saved_at_val or "",
            "saved_at": saved_at_val or "",
            "file_path": rec.get("file_path", "") or "",
        }

        for sk in matched:
            results_map[sk].append(entry)

    return results_map


def build_test_set():
    """Pick a diverse set of serials from ring_status, confirmed in archive_entries."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT rs.serial_number, rs.machine, rs.state, rs.phase
                FROM ring_status rs
                JOIN archive_entries ae ON ae.serial_lower = LOWER(rs.serial_number)
                WHERE rs.state = 'BDR_RUNNING'
                GROUP BY rs.serial_number, rs.machine, rs.state, rs.phase
                LIMIT 5
            """)
            running = cur.fetchall()

            cur.execute("""
                SELECT rs.serial_number, rs.machine, rs.state, rs.phase
                FROM ring_status rs
                JOIN archive_entries ae ON ae.serial_lower = LOWER(rs.serial_number)
                WHERE rs.state = 'PASSED'
                GROUP BY rs.serial_number, rs.machine, rs.state, rs.phase
                LIMIT 5
            """)
            passed = cur.fetchall()

            cur.execute("""
                SELECT rs.serial_number, rs.machine, rs.state, rs.phase
                FROM ring_status rs
                JOIN archive_entries ae ON ae.serial_lower = LOWER(rs.serial_number)
                WHERE rs.state = 'FAILED'
                GROUP BY rs.serial_number, rs.machine, rs.state, rs.phase
                LIMIT 3
            """)
            failed = cur.fetchall()

            cur.execute("""
                SELECT rs.serial_number
                FROM ring_status rs
                JOIN archive_entries ae ON ae.serial_lower = LOWER(rs.serial_number)
                GROUP BY rs.serial_number
                HAVING COUNT(DISTINCT rs.machine) >= 2
                LIMIT 4
            """)
            dual = cur.fetchall()
            dual_full = []
            for r in dual:
                sn = r["serial_number"]
                cur.execute(
                    "SELECT serial_number, machine, state, phase FROM ring_status WHERE serial_number = %s",
                    (sn,),
                )
                dual_full.extend(cur.fetchall())

            cur.execute("""
                SELECT rs.serial_number, rs.machine, rs.state, rs.phase
                FROM ring_status rs
                JOIN archive_entries ae ON ae.serial_lower = LOWER(rs.serial_number)
                GROUP BY rs.serial_number, rs.machine, rs.state, rs.phase
                LIMIT 6 OFFSET 20
            """)
            random_extra = cur.fetchall()

    finally:
        conn.close()

    serials = []
    seen = set()

    def add(label, rows):
        for r in rows:
            sn = r["serial_number"]
            if sn not in seen:
                seen.add(sn)
                serials.append({"serial": sn, "label": label, "info": dict(r)})

    add("BDR_RUNNING", running)
    add("PASSED", passed)
    add("FAILED", failed)
    add("DUAL_MACHINE", dual_full)
    add("RANDOM", random_extra)

    serials.append({"serial": "FAKE-SERIAL-DOES-NOT-EXIST-001", "label": "NONEXISTENT", "info": {}})
    serials.append({"serial": "ZZZZ-9999-ZZZZ-9999", "label": "NONEXISTENT", "info": {}})

    return serials


def pick_best_old(results):
    for r in results:
        if r.get("type") == "latest":
            return r
    return results[0] if results else {}


def compare_fields(old_row, new_row, fields):
    diffs = []
    for f in fields:
        ov = old_row.get(f)
        nv = new_row.get(f)
        o_norm = ov if ov is not None else ""
        n_norm = nv if nv is not None else ""
        try:
            if float(o_norm) == float(n_norm):
                continue
        except (TypeError, ValueError):
            pass
        if str(o_norm) != str(n_norm):
            diffs.append({"field": f, "old": ov, "new": nv})
    return diffs


def main():
    init_db()
    test_set = build_test_set()

    print("=" * 100)
    print(f"  VERIFICATION: old merge path vs ring_status -- {len(test_set)} serials")
    print("=" * 100)

    all_diffs = []
    all_match = True
    timing_old = []
    timing_new = []

    for i, item in enumerate(test_set):
        serial = item["serial"]
        label = item["label"]

        parsed = parse_serial([serial])
        key = parsed[0]["key"] if parsed else serial.lower()

        t0 = time.perf_counter()
        old_results_all = search_old_path([key])
        t1 = time.perf_counter()
        old_results = old_results_all.get(key, [])
        old_ms = round((t1 - t0) * 1000, 2)

        t0 = time.perf_counter()
        new_results_all = search_new_path([key])
        t1 = time.perf_counter()
        new_results = new_results_all.get(key, [])
        new_ms = round((t1 - t0) * 1000, 2)

        timing_old.append(old_ms)
        timing_new.append(new_ms)

        old_count = len(old_results)
        new_count = len(new_results)

        print(f"\n{'-' * 100}")
        print(f"  [{i+1}/{len(test_set)}] {serial}  ({label})")
        print(f"{'-' * 100}")
        print(f"  OLD rows={old_count}  time={old_ms}ms")
        print(f"  NEW rows={new_count}  time={new_ms}ms")

        def truncate_json(obj, max_str=80):
            if isinstance(obj, dict):
                return {k: truncate_json(v, max_str) for k, v in obj.items()}
            if isinstance(obj, list):
                return [truncate_json(v, max_str) for v in obj]
            if isinstance(obj, str) and len(obj) > max_str:
                return obj[:max_str-3] + "..."
            return obj

        # Show first row from each path
        print(f"\n  OLD best row:")
        old_best = pick_best_old(old_results)
        if old_best:
            print(f"    {json.dumps(truncate_json(old_best), indent=4, default=str)}")
        else:
            print(f"    (empty)")

        print(f"\n  NEW best row:")
        new_best = pick_best_old(new_results)
        if new_best:
            print(f"    {json.dumps(truncate_json(new_best), indent=4, default=str)}")
        else:
            print(f"    (empty)")

        serial_diffs = []

        if old_count != new_count:
            serial_diffs.append({
                "type": "ROW_COUNT_MISMATCH",
                "old": old_count,
                "new": new_count,
            })

        old_machines = {r.get("machine", "") for r in old_results}
        new_machines = {r.get("machine", "") for r in new_results}
        if old_machines != new_machines:
            serial_diffs.append({
                "type": "MACHINE_COVERAGE_MISMATCH",
                "old_machines": sorted(old_machines),
                "new_machines": sorted(new_machines),
                "missing_in_new": sorted(old_machines - new_machines),
                "extra_in_new": sorted(new_machines - old_machines),
            })

        field_diffs = compare_fields(old_best, new_best, COMPARE_FIELDS)
        for fd in field_diffs:
            serial_diffs.append({"type": "FIELD_DIFF", **fd})

        if serial_diffs:
            all_match = False
            print(f"\n  *** MISMATCHES ({len(serial_diffs)}) ***")
            for d in serial_diffs:
                if d["type"] == "ROW_COUNT_MISMATCH":
                    print(f"    [ROW_COUNT] old={d['old']}  new={d['new']}")
                elif d["type"] == "MACHINE_COVERAGE_MISMATCH":
                    print(f"    [MACHINES]  old={d['old_machines']}  new={d['new_machines']}")
                    if d["missing_in_new"]:
                        print(f"              MISSING in new: {d['missing_in_new']}")
                    if d["extra_in_new"]:
                        print(f"              EXTRA in new:   {d['extra_in_new']}")
                elif d["type"] == "FIELD_DIFF":
                    ov_s = str(d["old"]) if d["old"] is not None else "(null)"
                    nv_s = str(d["new"]) if d["new"] is not None else "(null)"
                    if len(ov_s) > 60: ov_s = ov_s[:57] + "..."
                    if len(nv_s) > 60: nv_s = nv_s[:57] + "..."
                    print(f"    [FIELD] {d['field']:<25} OLD={ov_s:<62} NEW={nv_s}")
            all_diffs.append({"serial": serial, "label": label, "diffs": serial_diffs})
        else:
            print(f"\n  MATCH -- all fields identical")

    # Timing
    print(f"\n{'=' * 100}")
    print(f"  TIMING SUMMARY")
    print(f"{'=' * 100}")
    print(f"  {'Serial':<45} {'OLD (ms)':>10} {'NEW (ms)':>10} {'Speedup':>10}")
    print(f"  {'-'*45} {'-'*10} {'-'*10} {'-'*10}")
    for i, item in enumerate(test_set):
        ot = timing_old[i]
        nt = timing_new[i]
        sp = f"{ot/nt:.1f}x" if nt > 0 else "inf"
        print(f"  {item['serial']:<45} {ot:>10.1f} {nt:>10.1f} {sp:>10}")
    avg_old = sum(timing_old) / len(timing_old)
    avg_new = sum(timing_new) / len(timing_new)
    print(f"  {'--- AVERAGE ---':<45} {avg_old:>10.1f} {avg_new:>10.1f} {avg_old/avg_new:.1f}x")

    # Edge cases
    print(f"\n{'=' * 100}")
    print(f"  EDGE CASE TESTS")
    print(f"{'=' * 100}")

    print(f"\n  [EMPTY_INPUT] serial=''")
    pk = parse_serial([""])
    k = pk[0]["key"]
    oe = search_old_path([k]).get(k, [])
    ne = search_new_path([k]).get(k, [])
    print(f"    OLD: {len(oe)} rows")
    print(f"    NEW: {len(ne)} rows")

    print(f"\n  [GARBAGE_INPUT] serial='!!!NOT_A_SERIAL%%%'")
    pk = parse_serial(["!!!NOT_A_SERIAL%%%"])
    k = pk[0]["key"]
    og = search_old_path([k]).get(k, [])
    ng = search_new_path([k]).get(k, [])
    print(f"    OLD: {len(og)} rows")
    print(f"    NEW: {len(ng)} rows")

    print(f"\n  [MACHINE_SEARCH] serial='aqc-41' (machine name)")
    pk = parse_serial(["aqc-41"])
    k = pk[0]["key"]
    om = search_old_path([k]).get(k, [])
    nm = search_new_path([k]).get(k, [])
    print(f"    OLD: {len(om)} rows")
    print(f"    NEW: {len(nm)} rows")
    if nm:
        nm_machines = sorted({r.get("machine", "") for r in nm})
        print(f"    NEW machines: {nm_machines}")

    # Final
    print(f"\n{'=' * 100}")
    print(f"  FINAL VERDICT")
    print(f"{'=' * 100}")
    if all_match:
        print(f"  PASS -- ring_status output is equivalent to old path")
        print(f"          across all {len(test_set)} test serials.")
    else:
        print(f"  DIFF found in {len(all_diffs)} / {len(test_set)} serials:\n")
        for d in all_diffs:
            print(f"    {d['serial']} ({d['label']}):")
            for diff in d["diffs"]:
                if diff["type"] == "ROW_COUNT_MISMATCH":
                    print(f"      ROW_COUNT: old={diff['old']} new={diff['new']}")
                elif diff["type"] == "MACHINE_COVERAGE_MISMATCH":
                    print(f"      MACHINES: old={diff['old_machines']} new={diff['new_machines']}")
                    if diff["missing_in_new"]:
                        print(f"        Missing in new: {diff['missing_in_new']}")
                elif diff["type"] == "FIELD_DIFF":
                    ov = str(diff["old"]) if diff["old"] is not None else "(null)"
                    nv = str(diff["new"]) if diff["new"] is not None else "(null)"
                    print(f"      {diff['field']}: OLD={ov}  NEW={nv}")


if __name__ == "__main__":
    main()
