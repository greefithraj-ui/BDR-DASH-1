"""Dry-run backfill v2: handles ISO timestamp conversion + per-row rollback."""
import sqlite3, sys, json, time, re
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import get_connection

with open(r"D:\BDR\data\backfill_plan.json") as f:
    plan = json.load(f)
samples = plan["samples"]
print(f"Dry-run backfill: {len(samples)} serials")

# 1. Extract from SQLite
print("\n--- EXTRACTING FROM SQLITE ---")
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

all_rows = []
t0 = time.time()
for i, sn in enumerate(samples):
    cur.execute("""
        SELECT serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
               snapshots, total_cycles, completed_cycles, start_time, last_update,
               saved_at, slot, firmware_version, ring_mac, ring_name,
               stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
               completed_workouts, avg_bdr_is_estimated, file_path
        FROM archive_entries
        WHERE serial_lower = ?
        ORDER BY saved_at
    """, (sn,))
    rows = [dict(r) for r in cur.fetchall()]
    all_rows.extend(rows)
    if (i+1) % 10 == 0:
        print(f"  {i+1}/{len(samples)} serials, {len(all_rows)} rows ({time.time()-t0:.1f}s)")
conn.close()
print(f"  Total: {len(all_rows)} rows ({time.time()-t0:.1f}s)")

# 2. Convert types
def to_epoch(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        try:
            return float(val)
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(val)
            return dt.timestamp()
        except (ValueError, TypeError):
            pass
    return None

for r in all_rows:
    fp = r.get("file_path", "")
    if fp:
        p = Path(fp)
        r["date"] = p.parent.name if p.parent else ""
        r["time"] = p.stem if p else ""
    else:
        r["date"] = ""
        r["time"] = ""
    r["avg_bdr"] = r.get("machine_avg_bdr")
    r["test_start"] = to_epoch(r.get("start_time"))
    r["start_time"] = to_epoch(r.get("start_time"))
    r["last_update"] = to_epoch(r.get("last_update"))
    r["battery_current"] = r.get("bdr")
    r["avg_bdr_is_stale"] = False
    if r.get("avg_bdr_is_estimated") is not None:
        r["avg_bdr_is_estimated"] = bool(r["avg_bdr_is_estimated"])

# 3. Check PG existing
print("\n--- CHECKING PG ---")
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT serial_lower, COUNT(*) FROM archive_entries WHERE serial_lower = ANY(%s) GROUP BY serial_lower", (samples,))
    pg_existing = dict(cur.fetchall())
pg_conn.close()
print(f"  Already in PG: {len(pg_existing)} serials")

rows_to_insert = [r for r in all_rows if r["serial_lower"] not in pg_existing]
serials_to_backfill = set(r["serial_lower"] for r in rows_to_insert)
print(f"  Rows to insert: {len(rows_to_insert)} from {len(serials_to_backfill)} serials")

# 4. Insert with per-row rollback
print("\n--- INSERTING INTO PG ---")
pg_conn = get_connection()
t0 = time.time()
inserted = 0
errors = 0
error_examples = []

for i, r in enumerate(rows_to_insert):
    try:
        with pg_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO archive_entries (
                    serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
                    snapshots, total_cycles, completed_cycles, start_time, last_update,
                    saved_at, date, time, slot, battery_current, firmware_version,
                    ring_mac, ring_name, avg_bdr, avg_bdr_is_stale, avg_bdr_is_estimated,
                    stored_avg_bdr, inter_cycle_avg_bdr, test_start, phase, cycle,
                    completed_workouts
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (serial_number, machine, saved_at) DO NOTHING
            """, (
                r.get("serial_number"), r.get("serial_lower"), r.get("machine"),
                r.get("state"), r.get("machine_avg_bdr") or r.get("avg_bdr"),
                r.get("bdr"), r.get("snapshots"), r.get("total_cycles"),
                r.get("completed_cycles"), r.get("start_time"), r.get("last_update"),
                r.get("saved_at"), r.get("date"), r.get("time"), r.get("slot"),
                r.get("battery_current"), r.get("firmware_version"),
                r.get("ring_mac"), r.get("ring_name"), r.get("avg_bdr"),
                r.get("avg_bdr_is_stale", False), r.get("avg_bdr_is_estimated", False),
                r.get("stored_avg_bdr"), r.get("inter_cycle_avg_bdr"),
                r.get("test_start"), r.get("phase"), r.get("cycle"),
                r.get("completed_workouts"),
            ))
        pg_conn.commit()
        inserted += 1
    except Exception as e:
        pg_conn.rollback()
        errors += 1
        if len(error_examples) < 5:
            error_examples.append(f"Row {i} ({r.get('serial_lower')}): {e}")
    if (i+1) % 1000 == 0:
        print(f"  {i+1}/{len(rows_to_insert)} processed, {inserted} inserted ({time.time()-t0:.1f}s)")

pg_conn.close()
print(f"\n  Inserted: {inserted}")
print(f"  Errors: {errors}")
print(f"  Time: {time.time()-t0:.1f}s")
if error_examples:
    print(f"\n  Error examples:")
    for e in error_examples:
        print(f"    {e}")

# 5. Save result
result = {"samples": samples, "inserted": inserted, "errors": errors,
          "serials_backfilled": list(serials_to_backfill)}
with open(r"D:\BDR\data\dryrun_result.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"\nSaved to dryrun_result.json")
