"""Broad comparison: set higher statement timeout and batch more carefully."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from postgres_db import get_connection
import psycopg2.extras

COMPARE_FIELDS = [
    "slot", "state", "avg_bdr", "avg_bdr_is_stale", "avg_bdr_is_estimated",
    "stored_avg_bdr", "inter_cycle_avg_bdr", "completed_cycles",
    "completed_workouts", "test_start", "phase", "cycle", "total_cycles",
    "start_time", "saved_at", "battery_current", "firmware_version",
    "ring_mac", "ring_name", "date", "time", "file_path",
]


def normalize(v):
    if v is None:
        return None
    if isinstance(v, float):
        if v != v:
            return None
        return round(v, 6)
    return v


def main():
    conn = get_connection()
    conn.autocommit = True
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SET statement_timeout = '300s';")

            # Step 1: Get all latest rows from v2
            cur.execute("""
                SELECT DISTINCT ON (serial_lower, machine)
                    serial_lower, machine, slot, state, avg_bdr,
                    avg_bdr_is_stale, avg_bdr_is_estimated,
                    stored_avg_bdr, inter_cycle_avg_bdr, test_start,
                    phase, cycle, snapshots, total_cycles, completed_cycles,
                    completed_workouts, start_time, saved_at,
                    battery_current, firmware_version, ring_mac, ring_name,
                    date, time, file_path
                FROM archive_entries_v2
                ORDER BY serial_lower, machine, saved_at DESC
            """)
            v2_latest = {}
            for r in cur.fetchall():
                v2_latest[(r["serial_lower"], r["machine"])] = r
            print(f"v2 latest rows: {len(v2_latest)}")

            # Step 2: For v1, use a CTE that does the fallback in SQL
            # Process in smaller batches of serial_lower
            all_s_lowers = list(set(k[0] for k in v2_latest.keys()))
            print(f"Unique serial_lower values: {len(all_s_lowers)}")

            BATCH = 100
            total_identical = 0
            total_mismatched = 0
            mismatch_details = []
            fallback_count = 0

            for bi in range(0, len(all_s_lowers), BATCH):
                batch = all_s_lowers[bi:bi+BATCH]

                # Use CTE to compute latest + best_bdr per group in SQL
                cur.execute("""
                    WITH rows AS (
                        SELECT
                            serial_lower, machine,
                            (content->>'slot')::int AS slot,
                            COALESCE(content->>'state', '') AS state,
                            (content->>'avg_bdr')::double precision AS avg_bdr,
                            COALESCE((content->>'avg_bdr_is_stale')::boolean, false) AS avg_bdr_is_stale,
                            COALESCE((content->>'avg_bdr_is_estimated')::boolean, false) AS avg_bdr_is_estimated,
                            (content->>'stored_avg_bdr')::double precision AS stored_avg_bdr,
                            (content->>'inter_cycle_avg_bdr')::double precision AS inter_cycle_avg_bdr,
                            (content->>'test_start')::double precision AS test_start,
                            content->>'phase' AS phase,
                            (content->>'cycle')::int AS cycle,
                            (content->>'snapshots')::int AS snapshots,
                            (content->>'total_cycles')::int AS total_cycles,
                            (content->>'completed_cycles')::int AS completed_cycles,
                            (content->>'completed_workouts')::int AS completed_workouts,
                            (content->>'start_time')::double precision AS start_time,
                            (content->>'battery_current')::double precision AS battery_current,
                            content->>'firmware_version' AS firmware_version,
                            content->>'ring_mac' AS ring_mac,
                            content->>'ring_name' AS ring_name,
                            content->>'date' AS date,
                            content->>'time' AS time,
                            content->>'file_path' AS file_path,
                            saved_at,
                            ROW_NUMBER() OVER (
                                PARTITION BY serial_lower, machine
                                ORDER BY saved_at DESC
                            ) AS rn
                        FROM archive_entries
                        WHERE serial_lower = ANY(%s)
                    ),
                    best_bdr AS (
                        SELECT DISTINCT ON (serial_lower, machine)
                            serial_lower, machine,
                            avg_bdr AS best_avg,
                            avg_bdr_is_estimated AS best_est,
                            stored_avg_bdr AS best_stored,
                            inter_cycle_avg_bdr AS best_inter,
                            completed_cycles AS best_completed,
                            completed_workouts AS best_workouts
                        FROM rows
                        WHERE avg_bdr IS NOT NULL AND avg_bdr != 0.0
                        ORDER BY serial_lower, machine, saved_at DESC
                    ),
                    latest AS (
                        SELECT * FROM rows WHERE rn = 1
                    )
                    SELECT
                        l.serial_lower, l.machine, l.slot, l.state,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN bb.best_avg ELSE l.avg_bdr END AS avg_bdr,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN false ELSE l.avg_bdr_is_stale END AS avg_bdr_is_stale,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN bb.best_est ELSE l.avg_bdr_is_estimated END AS avg_bdr_is_estimated,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN bb.best_stored ELSE l.stored_avg_bdr END AS stored_avg_bdr,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN bb.best_inter ELSE l.inter_cycle_avg_bdr END AS inter_cycle_avg_bdr,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN bb.best_completed ELSE l.completed_cycles END AS completed_cycles,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN bb.best_workouts ELSE l.completed_workouts END AS completed_workouts,
                        l.test_start, l.phase, l.cycle, l.total_cycles,
                        l.start_time, l.saved_at, l.battery_current,
                        l.firmware_version, l.ring_mac, l.ring_name,
                        l.date, l.time, l.file_path,
                        CASE WHEN (l.avg_bdr IS NULL OR l.avg_bdr = 0.0) AND bb.best_avg IS NOT NULL
                             THEN 1 ELSE 0 END AS fallback_used
                    FROM latest l
                    LEFT JOIN best_bdr bb ON l.serial_lower = bb.serial_lower AND l.machine = bb.machine
                """, (batch,))
                v1_rows = {(r["serial_lower"], r["machine"]): r for r in cur.fetchall()}

                for s_lower in batch:
                    for machine in set(
                        k[1] for k in v2_latest if k[0] == s_lower
                    ):
                        key = (s_lower, machine)
                        v1r = v1_rows.get(key)
                        v2r = v2_latest.get(key)
                        if not v1r:
                            total_mismatched += 1
                            mismatch_details.append(f"  MISSING in v1: {key}")
                            continue
                        if not v2r:
                            total_mismatched += 1
                            mismatch_details.append(f"  MISSING in v2: {key}")
                            continue

                        if v1r.get("fallback_used"):
                            fallback_count += 1

                        diffs = []
                        for f in COMPARE_FIELDS:
                            v1val = normalize(v1r.get(f))
                            v2val = normalize(v2r.get(f))
                            if v1val != v2val:
                                diffs.append(f"    {f}: v1={v1val!r} v2={v2val!r}")

                        if diffs:
                            total_mismatched += 1
                            mismatch_details.append(f"  {key[0]} / {key[1]}:")
                            mismatch_details.extend(diffs)
                        else:
                            total_identical += 1

                pct = min(100, (bi + len(batch)) / len(all_s_lowers) * 100)
                print(f"  Batch {bi//BATCH+1}: {total_identical} match, {total_mismatched} mismatch ({pct:.0f}%)")

        print(f"\n{'=' * 80}")
        print(f"BROAD COMPARISON RESULTS (v1 vs v2)")
        print(f"{'=' * 80}")
        print(f"  Total (serial, machine) pairs compared: {total_identical + total_mismatched}")
        print(f"  Identical:    {total_identical}")
        print(f"  Mismatched:   {total_mismatched}")
        print(f"  Stale fallbacks triggered: {fallback_count}")

        if mismatch_details:
            print(f"\n  MISMATCH DETAILS:")
            for line in mismatch_details[:200]:
                print(line)
        else:
            print(f"\n  [OK] ZERO MISMATCHES across ALL serial+machine pairs")
        print(f"{'=' * 80}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
