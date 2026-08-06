"""Full backfill: extract 2,441 serials from SQLite, daily dedup, insert into PG."""
import sqlite3, sys, json, time, re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import get_connection

# ── Load plan ────────────────────────────────────────────────────────────────
with open(r"D:\BDR\data\backfill_plan.json") as f:
    plan = json.load(f)
all_details = plan["details"]
missing_serials = sorted(all_details.keys())
print(f"Full backfill: {len(missing_serials)} serials")

# ── Step 1: Clean up dry-run rows ───────────────────────────────────────────
with open(r"D:\BDR\data\dryrun_result.json") as f:
    dryrun = json.load(f)
dryrun_serials = dryrun["serials_backfilled"]
print(f"\nCleaning up {len(dryrun_serials)} dry-run serials from PG...")
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("DELETE FROM archive_entries WHERE serial_lower = ANY(%s)", (dryrun_serials,))
    deleted = cur.rowcount
pg_conn.commit()
pg_conn.close()
print(f"  Deleted {deleted} dry-run rows")

# ── Step 2: Extract all rows from SQLite ─────────────────────────────────────
print(f"\nExtracting from SQLite...")
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

all_raw = []
t0 = time.time()
BATCH = 200
for i in range(0, len(missing_serials), BATCH):
    batch = missing_serials[i:i+BATCH]
    placeholders = ",".join("?" for _ in batch)
    cur.execute(f"""
        SELECT serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
               snapshots, total_cycles, completed_cycles, start_time, last_update,
               saved_at, slot, firmware_version, ring_mac, ring_name,
               stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
               completed_workouts, avg_bdr_is_estimated, file_path
        FROM archive_entries
        WHERE serial_lower IN ({placeholders})
        ORDER BY serial_lower, machine, saved_at
    """, batch)
    rows = [dict(r) for r in cur.fetchall()]
    all_raw.extend(rows)
    if (i+BATCH) % 1000 == 0 or i + BATCH >= len(missing_serials):
        print(f"  {min(i+BATCH, len(missing_serials))}/{len(missing_serials)} serials, {len(all_raw):,} rows ({time.time()-t0:.1f}s)")

conn.close()
print(f"  Total raw: {len(all_raw):,} rows ({time.time()-t0:.1f}s)")

# ── Step 3: Map SQLite schema → PG schema ───────────────────────────────────
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

for r in all_raw:
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

# ── Step 4: Daily dedup ─────────────────────────────────────────────────────
print(f"\nApplying daily dedup...")
t0 = time.time()

# Group by (serial_lower, machine, day)
by_combo = defaultdict(list)
for r in all_raw:
    day = r.get("date", "")[:10]
    key = (r["serial_lower"], r.get("machine", ""), day)
    by_combo[key].append(r)

# For each (serial, machine, day): keep the latest row
deduped = []
for key, rows in by_combo.items():
    rows.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
    deduped.append(rows[0])

# Find best-good fallback per (serial, machine)
# A "good" row has non-null, non-zero avg_bdr
by_sm = defaultdict(list)
for r in all_raw:
    sm_key = (r["serial_lower"], r.get("machine", ""))
    by_sm[sm_key].append(r)

fallback_added = 0
for sm_key, rows in by_sm.items():
    sn, machine = sm_key
    # Check if any deduped row for this (serial, machine) has good avg_bdr
    deduped_for_sm = [d for d in deduped if d["serial_lower"] == sn and d.get("machine") == machine]
    has_good = any(d.get("avg_bdr") is not None and d.get("avg_bdr", 0) != 0.0 for d in deduped_for_sm)
    if not has_good:
        # Find best-good from raw
        good_rows = [r for r in rows if r.get("avg_bdr") is not None and r.get("avg_bdr", 0) != 0.0]
        if good_rows:
            best = max(good_rows, key=lambda x: x.get("saved_at", ""))
            # Check if already in deduped
            already = any(d["serial_lower"] == best["serial_lower"] and
                         d.get("machine") == best.get("machine") and
                         d.get("saved_at") == best.get("saved_at") for d in deduped)
            if not already:
                deduped.append(best)
                fallback_added += 1

print(f"  Raw rows: {len(all_raw):,}")
print(f"  After dedup: {len(deduped):,} ({len(deduped)/len(all_raw)*100:.1f}% of raw)")
print(f"  Fallback records added: {fallback_added}")

# ── Step 5: Batched insert ──────────────────────────────────────────────────
print(f"\nInserting {len(deduped):,} rows into PG...")
pg_conn = get_connection()
t0 = time.time()
inserted = 0
errors = 0
BATCH_SIZE = 1000

for i in range(0, len(deduped), BATCH_SIZE):
    batch = deduped[i:i+BATCH_SIZE]
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
                        print(f"    Row error: {e}")
        pg_conn.commit()
    except Exception as e:
        pg_conn.rollback()
        errors += len(batch)
    if (i+BATCH_SIZE) % 5000 == 0 or i + BATCH_SIZE >= len(deduped):
        elapsed = time.time() - t0
        rate = inserted / elapsed if elapsed > 0 else 0
        print(f"  {min(i+BATCH_SIZE, len(deduped)):,}/{len(deduped):,} processed, {inserted:,} inserted ({elapsed:.0f}s, {rate:.0f} rows/s)")

pg_conn.close()
print(f"\n  Inserted: {inserted:,}")
print(f"  Errors: {errors}")
print(f"  Time: {time.time()-t0:.1f}s")

# ── Step 6: Quick verification ──────────────────────────────────────────────
print(f"\n=== QUICK VERIFICATION ===")
from data.postgres_db import search_archive_in_pg

# Check all backfilled serials
t0 = time.time()
VERIF_BATCH = 200
all_ok = 0
empty_count = 0
no_fallback_needed = 0

for i in range(0, len(missing_serials), VERIF_BATCH):
    batch = missing_serials[i:i+VERIF_BATCH]
    results = search_archive_in_pg(batch)
    for sn in batch:
        rows = results.get(sn, [])
        if not rows:
            empty_count += 1
        else:
            all_ok += 1
    if (i+VERIF_BATCH) % 1000 == 0 or i + VERIF_BATCH >= len(missing_serials):
        print(f"  Verified {min(i+VERIF_BATCH, len(missing_serials)):,}/{len(missing_serials)} ({time.time()-t0:.1f}s)")

print(f"\n  Search results OK: {all_ok}/{len(missing_serials)}")
print(f"  Empty results: {empty_count}")

# Check that none need SQLite fallback
from data.api import _search_archive_db_for_serials
sample_for_fb = missing_serials[:200]
pg_res = search_archive_in_pg(sample_for_fb)
need_fb = [s for s in sample_for_fb if not pg_res.get(s)]
print(f"  SQLite fallback needed (sample 200): {len(need_fb)}")

# Spot check avg_bdr
print(f"\n  Avg BDR spot check:")
for sn in missing_serials[:5]:
    rows = results.get(sn, [])
    if rows:
        r = rows[0]
        print(f"    {sn}: avg_bdr={r.get('avg_bdr')}, state={r.get('state')}, machine={r.get('machine')}")

# Save result
result = {
    "missing_count": len(missing_serials),
    "raw_rows": len(all_raw),
    "deduped_rows": len(deduped),
    "fallback_added": fallback_added,
    "inserted": inserted,
    "errors": errors,
    "search_ok": all_ok,
    "search_empty": empty_count,
}
with open(r"D:\BDR\data\backfill_result.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"\nSaved to backfill_result.json")
