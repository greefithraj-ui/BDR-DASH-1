"""Full backfill: dedup in SQLite SQL, extract ~44k rows, insert into PG."""
import sqlite3, sys, json, time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import get_connection

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)
print(f"Backfill: {len(missing)} serials")

# ── Step 1: DEDUP IN SQLite ─────────────────────────────────────────────────
print("\n=== DEDUP IN SQLITE ===")
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1a: Daily latest per (serial_lower, machine, day)
# SQLite doesn't have date column, derive from saved_at
t0 = time.time()
BATCH = 500
daily_latest = []

for i in range(0, len(missing), BATCH):
    batch = missing[i:i+BATCH]
    placeholders = ",".join("?" for _ in batch)
    cur.execute(f"""
        SELECT * FROM (
            SELECT *,
                substr(saved_at, 1, 10) as day_key,
                ROW_NUMBER() OVER (
                    PARTITION BY serial_lower, machine, substr(saved_at, 1, 10)
                    ORDER BY saved_at DESC
                ) AS rn
            FROM archive_entries
            WHERE serial_lower IN ({placeholders})
        ) WHERE rn = 1
    """, batch)
    rows = [dict(r) for r in cur.fetchall()]
    daily_latest.extend(rows)
    if (i+BATCH) % 1000 == 0 or i + BATCH >= len(missing):
        print(f"  Daily latest: {min(i+BATCH, len(missing))}/{len(missing)} serials, {len(daily_latest):,} rows ({time.time()-t0:.1f}s)")

print(f"  Daily latest rows: {len(daily_latest):,} ({time.time()-t0:.1f}s)")

# 1b: Best-good fallback per (serial_lower, machine)
# Find serials where ALL daily-latest rows have NULL/0 avg_bdr
sm_has_good = set()
for r in daily_latest:
    avg = r.get("machine_avg_bdr")
    if avg is not None and avg != 0.0:
        sm_has_good.add((r["serial_lower"], r.get("machine", "")))

# Get all (serial_lower, machine) combos from daily_latest
all_sm = set((r["serial_lower"], r.get("machine", "")) for r in daily_latest)
sm_needs_fallback = all_sm - sm_has_good
print(f"  Serials needing fallback: {len(sm_needs_fallback)}")

fallback_rows = []
if sm_needs_fallback:
    # Get best-good for each (serial, machine) that needs it
    for i in range(0, len(missing), BATCH):
        batch = missing[i:i+BATCH]
        placeholders = ",".join("?" for _ in batch)
        cur.execute(f"""
            SELECT * FROM (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY serial_lower, machine
                        ORDER BY
                            CASE WHEN machine_avg_bdr IS NOT NULL AND machine_avg_bdr != 0 THEN 0 ELSE 1 END,
                            saved_at DESC
                    ) AS good_rn
                FROM archive_entries
                WHERE serial_lower IN ({placeholders})
                  AND machine_avg_bdr IS NOT NULL AND machine_avg_bdr != 0
            ) WHERE good_rn = 1
        """, batch)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            sm = (r["serial_lower"], r.get("machine", ""))
            if sm in sm_needs_fallback:
                # Check if already in daily_latest with same saved_at
                already = any(d["serial_lower"] == r["serial_lower"] and
                             d.get("machine") == r.get("machine") and
                             d.get("saved_at") == r.get("saved_at") for d in daily_latest)
                if not already:
                    fallback_rows.append(r)

print(f"  Fallback records added: {len(fallback_rows)}")
conn.close()

# 1c: Combine and map schema
all_deduped = daily_latest + fallback_rows
print(f"  Total deduped rows: {len(all_deduped):,}")

def to_epoch(val):
    if val is None: return None
    if isinstance(val, (int, float)): return float(val)
    if isinstance(val, str):
        val = val.strip()
        if not val: return None
        try: return float(val)
        except ValueError: pass
        try: return datetime.fromisoformat(val).timestamp()
        except: pass
    return None

for r in all_deduped:
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

# Save to file for inspection
with open(r"D:\BDR\data\backfill_deduped.json", "w") as f:
    json.dump({"count": len(all_deduped), "serials": len(set(r["serial_lower"] for r in all_deduped))}, f)
print(f"  Saved summary to backfill_deduped.json")

# ── Step 2: BATCHED INSERT ──────────────────────────────────────────────────
print(f"\n=== INSERTING {len(all_deduped):,} ROWS ===")
pg_conn = get_connection()
t0 = time.time()
inserted = 0
errors = 0
BATCH_SIZE = 1000

for i in range(0, len(all_deduped), BATCH_SIZE):
    batch = all_deduped[i:i+BATCH_SIZE]
    try:
        with pg_conn.cursor() as cur:
            for r in batch:
                try:
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
                    inserted += 1
                except Exception as e:
                    pg_conn.rollback()
                    errors += 1
                    if errors <= 3:
                        print(f"    Error: {e}")
        pg_conn.commit()
    except Exception as e:
        pg_conn.rollback()
        errors += len(batch)
    if (i+BATCH_SIZE) % 5000 == 0 or i + BATCH_SIZE >= len(all_deduped):
        elapsed = time.time() - t0
        rate = inserted / elapsed if elapsed > 0 else 0
        print(f"  {min(i+BATCH_SIZE, len(all_deduped)):,}/{len(all_deduped):,} processed, {inserted:,} inserted ({elapsed:.0f}s, {rate:.0f}/s)")

pg_conn.close()
print(f"\n  Inserted: {inserted:,}")
print(f"  Errors: {errors}")
print(f"  Time: {time.time()-t0:.1f}s")

# ── Step 3: VERIFY ──────────────────────────────────────────────────────────
print(f"\n=== VERIFICATION ===")
from data.postgres_db import search_archive_in_pg

t0 = time.time()
VERIF_BATCH = 200
all_ok = 0
empty_count = 0

for i in range(0, len(missing), VERIF_BATCH):
    batch = missing[i:i+VERIF_BATCH]
    results = search_archive_in_pg(batch)
    for sn in batch:
        rows = results.get(sn, [])
        if not rows:
            empty_count += 1
        else:
            all_ok += 1
    if (i+VERIF_BATCH) % 1000 == 0 or i + VERIF_BATCH >= len(missing):
        print(f"  Verified {min(i+VERIF_BATCH, len(missing)):,}/{len(missing)} ({time.time()-t0:.1f}s)")

print(f"\n  Search OK: {all_ok}/{len(missing)}")
print(f"  Empty: {empty_count}")

# Check SQLite fallback not needed
from data.api import _search_archive_db_for_serials
sample_fb = missing[:200]
pg_res = search_archive_in_pg(sample_fb)
need_fb = [s for s in sample_fb if not pg_res.get(s)]
print(f"  SQLite fallback needed (sample 200): {len(need_fb)}")

# Storage
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM archive_entries")
    total = cur.fetchone()[0]
pg_conn.close()
print(f"\n  Total PG rows: {total:,}")

result = {
    "missing_count": len(missing),
    "deduped_rows": len(all_deduped),
    "inserted": inserted,
    "errors": errors,
    "search_ok": all_ok,
    "search_empty": empty_count,
    "total_pg_rows": total,
}
with open(r"D:\BDR\data\backfill_result.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"Saved to backfill_result.json")
