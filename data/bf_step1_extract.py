import sqlite3, json, time
from pathlib import Path
from datetime import datetime

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)
print(f"Extracting {len(missing)} serials from SQLite...")

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

all_raw = []
t0 = time.time()
BATCH = 200
for i in range(0, len(missing), BATCH):
    batch = missing[i:i+BATCH]
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
    for r in cur.fetchall():
        all_raw.append(dict(r))
    elapsed = time.time() - t0
    print(f"  {min(i+BATCH, len(missing))}/{len(missing)} serials, {len(all_raw):,} rows ({elapsed:.0f}s)")

conn.close()
print(f"Total: {len(all_raw):,} rows ({time.time()-t0:.0f}s)")

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

with open(r"D:\BDR\data\backfill_raw.json", "w") as f:
    json.dump(all_raw, f)
print(f"Saved {len(all_raw):,} rows to backfill_raw.json")
