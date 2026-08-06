"""Compare search results between archive_entries (v1) and archive_entries_v2.

Runs the exact same fallback logic as search_archive_in_pg against both tables
and diffs the output for a set of test serials.
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from postgres_db import get_connection
import psycopg2.extras


TEST_SERIALS = [
    "RA-CH3-LFK-W1-RT08-0000161",   # two machines, one with bad avg_bdr
    "RA-CH3-LFK-W1-AG08-0000261",   # missing from ring_status, should exist here
    "RA-CH3-LFK-W1-AG07-0000193",   # stale: latest avg_bdr=NULL, fallback needed
    "RA-CH3-LFK-W1-AG07-0000417",   # MISMATCH: v1 fallback found avg_bdr=2.892, v2=None
    "RA-CH3-LFK-W1-AG06-0000060",   # MISMATCH: v1 avg_bdr=0.0, v2=None
    "RA-CH2-IW1-WB-WM13-315",       # MISMATCH: extra fields differ
    "RA-CH3-LFK-W1-AG06-0000159",   # MISMATCH: extra fields differ
    "RA-CH3-LFK-WB-BR09-0000017",   # random
    "RA-CH3-LFK-W1-AS07-0000211",   # random
    "RA-CH3-IW3-WB-WR12-0002012",   # random
]

TEST_SERIAL_KEYS = [s.lower() for s in TEST_SERIALS]


def search_v1(conn, serial_keys):
    """Exact copy of search_archive_in_pg logic — reads from v1 JSONB."""
    results_map = {key: [] for key in serial_keys}
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        query = """
            SELECT content
            FROM archive_entries
            WHERE serial_lower = ANY(%s)
            ORDER BY serial_lower, machine, saved_at DESC
        """
        cur.execute(query, (serial_keys,))
        rows = cur.fetchall()

        grouped_rows = {}
        for row in rows:
            rec = row["content"]
            if not rec:
                continue
            s_lower = str(rec.get("serial_number", "")).lower()
            machine = rec.get("machine", "")
            combo_key = (s_lower, machine)
            if combo_key not in grouped_rows:
                grouped_rows[combo_key] = []
            grouped_rows[combo_key].append(rec)

        for combo_key, recs in grouped_rows.items():
            s_lower, machine = combo_key
            best_bdr_rec = None
            for r in recs:
                avg = r.get("avg_bdr")
                if avg is not None and avg != 0.0:
                    best_bdr_rec = r
                    break

            for i, rec in enumerate(recs):
                row_type = "latest" if i == 0 else "history"
                is_stale = rec.get("avg_bdr_is_stale", False) or rec.get("avg_bdr") is None or rec.get("avg_bdr") == 0.0

                final_avg = rec.get("avg_bdr")
                final_est = rec.get("avg_bdr_is_estimated", False)
                final_stored = rec.get("stored_avg_bdr")
                final_inter = rec.get("inter_cycle_avg_bdr")
                final_completed = rec.get("completed_cycles", 0)
                final_workouts = rec.get("completed_workouts")
                final_stale = rec.get("avg_bdr_is_stale", False)

                if is_stale and best_bdr_rec:
                    final_avg = best_bdr_rec.get("avg_bdr")
                    final_est = best_bdr_rec.get("avg_bdr_is_estimated", False)
                    final_stored = best_bdr_rec.get("stored_avg_bdr")
                    final_inter = best_bdr_rec.get("inter_cycle_avg_bdr")
                    final_completed = best_bdr_rec.get("completed_cycles", 0)
                    final_workouts = best_bdr_rec.get("completed_workouts")
                    final_stale = False
                    if not str(rec.get("state", "")).strip():
                        hs = str(best_bdr_rec.get("state", ""))
                        if hs and "bdr" not in hs.lower() and hs.strip():
                            rec["state"] = hs

                if s_lower in results_map:
                    results_map[s_lower].append({
                        "type": row_type,
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
                        "avg_bdr": final_avg,
                        "machine_avg_bdr": final_avg,
                        "avg_bdr_is_stale": final_stale,
                        "avg_bdr_is_estimated": final_est,
                        "stored_avg_bdr": final_stored,
                        "inter_cycle_avg_bdr": final_inter,
                        "test_start": rec.get("test_start"),
                        "phase": rec.get("phase"),
                        "cycle": rec.get("cycle"),
                        "snapshots": rec.get("snapshots", 1),
                        "total_cycles": rec.get("total_cycles", 0),
                        "completed_cycles": final_completed,
                        "completed_workouts": final_workouts,
                        "start_time": rec.get("start_time") or rec.get("test_start"),
                        "last_update": rec.get("saved_at", ""),
                        "saved_at": rec.get("saved_at", ""),
                        "file_path": rec.get("file_path", "")
                    })
    return results_map


def search_v2(conn, serial_keys):
    """Same fallback logic but reads from v2 proper columns."""
    results_map = {key: [] for key in serial_keys}
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        query = """
            SELECT serial_number, machine, date, time, slot, state,
                   battery_current, firmware_version, ring_mac, ring_name,
                   avg_bdr, avg_bdr_is_stale, avg_bdr_is_estimated,
                   stored_avg_bdr, inter_cycle_avg_bdr, test_start,
                   phase, cycle, snapshots, total_cycles, completed_cycles,
                   completed_workouts, start_time, last_update, saved_at,
                   file_path
            FROM archive_entries_v2
            WHERE serial_lower = ANY(%s)
            ORDER BY serial_lower, machine, saved_at DESC
        """
        cur.execute(query, (serial_keys,))
        rows = cur.fetchall()

        grouped_rows = {}
        for row in rows:
            rec = dict(row)
            s_lower = str(rec.get("serial_number", "")).lower()
            machine = rec.get("machine", "")
            combo_key = (s_lower, machine)
            if combo_key not in grouped_rows:
                grouped_rows[combo_key] = []
            grouped_rows[combo_key].append(rec)

        for combo_key, recs in grouped_rows.items():
            s_lower, machine = combo_key
            best_bdr_rec = None
            for r in recs:
                avg = r.get("avg_bdr")
                if avg is not None and avg != 0.0:
                    best_bdr_rec = r
                    break

            for i, rec in enumerate(recs):
                row_type = "latest" if i == 0 else "history"
                is_stale = rec.get("avg_bdr_is_stale", False) or rec.get("avg_bdr") is None or rec.get("avg_bdr") == 0.0

                final_avg = rec.get("avg_bdr")
                final_est = rec.get("avg_bdr_is_estimated", False)
                final_stored = rec.get("stored_avg_bdr")
                final_inter = rec.get("inter_cycle_avg_bdr")
                final_completed = rec.get("completed_cycles", 0)
                final_workouts = rec.get("completed_workouts")
                final_stale = rec.get("avg_bdr_is_stale", False)

                if is_stale and best_bdr_rec:
                    final_avg = best_bdr_rec.get("avg_bdr")
                    final_est = best_bdr_rec.get("avg_bdr_is_estimated", False)
                    final_stored = best_bdr_rec.get("stored_avg_bdr")
                    final_inter = best_bdr_rec.get("inter_cycle_avg_bdr")
                    final_completed = best_bdr_rec.get("completed_cycles", 0)
                    final_workouts = best_bdr_rec.get("completed_workouts")
                    final_stale = False
                    if not str(rec.get("state", "")).strip():
                        hs = str(best_bdr_rec.get("state", ""))
                        if hs and "bdr" not in hs.lower() and hs.strip():
                            rec["state"] = hs

                if s_lower in results_map:
                    results_map[s_lower].append({
                        "type": row_type,
                        "serial_number": rec.get("serial_number", ""),
                        "machine": machine,
                        "date": rec.get("date", "") or "",
                        "time": rec.get("time", "") or "",
                        "slot": rec.get("slot"),
                        "state": rec.get("state", "") or "",
                        "battery_current": rec.get("battery_current"),
                        "firmware_version": rec.get("firmware_version", "") or "",
                        "ring_mac": rec.get("ring_mac", "") or "",
                        "ring_name": rec.get("ring_name", "") or "",
                        "avg_bdr": final_avg,
                        "machine_avg_bdr": final_avg,
                        "avg_bdr_is_stale": final_stale,
                        "avg_bdr_is_estimated": final_est,
                        "stored_avg_bdr": final_stored,
                        "inter_cycle_avg_bdr": final_inter,
                        "test_start": rec.get("test_start"),
                        "phase": rec.get("phase", "") or "",
                        "cycle": rec.get("cycle"),
                        "snapshots": rec.get("snapshots") or 1,
                        "total_cycles": rec.get("total_cycles") or 0,
                        "completed_cycles": final_completed,
                        "completed_workouts": final_workouts,
                        "start_time": rec.get("start_time") or rec.get("test_start"),
                        "last_update": rec.get("saved_at", "") or "",
                        "saved_at": rec.get("saved_at", "") or "",
                        "file_path": rec.get("file_path", "") or ""
                    })
    return results_map


def normalize_val(v):
    """Normalize a value for comparison (handle None vs 0, float precision, etc.)."""
    if v is None:
        return None
    if isinstance(v, float):
        if v != v:  # NaN
            return None
        return round(v, 6)
    return v


def compare_records(rec_v1, rec_v2, idx):
    """Compare two records field by field. Returns list of differences."""
    diffs = []
    all_keys = sorted(set(list(rec_v1.keys()) + list(rec_v2.keys())))
    for k in all_keys:
        v1 = normalize_val(rec_v1.get(k))
        v2 = normalize_val(rec_v2.get(k))
        if v1 != v2:
            diffs.append(f"    field '{k}': v1={v1!r}  v2={v2!r}")
    return diffs


def main():
    conn = get_connection()
    try:
        print("=" * 80)
        print("ARCHIVE ENTRIES v1 vs v2 COMPARISON")
        print("=" * 80)

        v1_results = search_v1(conn, TEST_SERIAL_KEYS)
        v2_results = search_v2(conn, TEST_SERIAL_KEYS)

        total_diffs = 0
        total_matches = 0

        for serial in TEST_SERIALS:
            sk = serial.lower()
            v1_rows = v1_results.get(sk, [])
            v2_rows = v2_results.get(sk, [])
            print(f"\n{'-' * 80}")
            print(f"Serial: {serial}")
            print(f"  v1 rows: {len(v1_rows)}  |  v2 rows: {len(v2_rows)}")

            if len(v1_rows) != len(v2_rows):
                print(f"  WARNING: ROW COUNT MISMATCH: v1 has {len(v1_rows)} rows, v2 has {len(v2_rows)} rows")
                if len(v2_rows) < len(v1_rows):
                    print(f"  (Expected: v2 has fewer rows due to daily dedup -- frontend dedup shows only the latest anyway)")

            # Compare the "latest" row (index 0) — this is what the frontend displays
            if v1_rows and v2_rows:
                latest_v1 = v1_rows[0]
                latest_v2 = v2_rows[0]
                print(f"\n  LATEST ROW comparison:")
                print(f"    v1 type={latest_v1.get('type')}, v2 type={latest_v2.get('type')}")
                diffs = compare_records(latest_v1, latest_v2, 0)
                if diffs:
                    print(f"    *** DIFFERENCES ({len(diffs)}):")
                    for d in diffs:
                        print(d)
                    total_diffs += len(diffs)
                else:
                    print(f"    [OK] IDENTICAL (all fields match)")
                    total_matches += 1

                # Also check if fallback was needed
                v1_is_stale = latest_v1.get("avg_bdr_is_stale", False)
                v1_avg = latest_v1.get("avg_bdr")
                v2_is_stale = latest_v2.get("avg_bdr_is_stale", False)
                v2_avg = latest_v2.get("avg_bdr")
                if v1_is_stale or v1_avg is None or v1_avg == 0.0:
                    print(f"    [INFO] Stale fallback was active in v1 (avg_bdr={v1_avg}, stale={v1_is_stale})")
                if v2_is_stale or v2_avg is None or v2_avg == 0.0:
                    print(f"    [INFO] Stale fallback was active in v2 (avg_bdr={v2_avg}, stale={v2_is_stale})")
            elif not v1_rows and not v2_rows:
                print(f"  WARNING: NO DATA in either table for this serial")
            elif not v2_rows:
                print(f"  WARNING: NO DATA in v2 (exists in v1 only)")
                total_diffs += 1
            else:
                print(f"  WARNING: NO DATA in v1 (exists in v2 only)")
                total_diffs += 1

        print(f"\n{'=' * 80}")
        print(f"SUMMARY")
        print(f"  Latest rows compared identically: {total_matches}")
        print(f"  Total field differences: {total_diffs}")
        if total_diffs == 0:
            print(f"  [OK] ALL TEST SERIALS MATCH -- v2 produces identical output to v1")
        else:
            print(f"  [FAIL] {total_diffs} DIFFERENCES FOUND -- review needed")
        print(f"{'=' * 80}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
