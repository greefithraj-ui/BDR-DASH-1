"""Extract serials from SQLite in batches, save as chunked JSON files."""
import sqlite3, json, time, os
from pathlib import Path
from datetime import datetime

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)

CHUNK = 100
CHUNK_DIR = r"D:\BDR\data\bf_chunks"
os.makedirs(CHUNK_DIR, exist_ok=True)

# Check which chunks already exist
done = set()
for fn in os.listdir(CHUNK_DIR):
    if fn.startswith("chunk_") and fn.endswith(".json"):
        idx = int(fn.replace("chunk_","").replace(".json",""))
        done.add(idx)

total_chunks = (len(missing) + CHUNK - 1) // CHUNK
print(f"Total serials: {len(missing)}, chunk size: {CHUNK}, total chunks: {total_chunks}")
print(f"Already done: {len(done)} chunks")

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
conn.row_factory = sqlite3.Row

COLUMNS = """serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
       snapshots, total_cycles, completed_cycles, start_time, last_update,
       saved_at, slot, firmware_version, ring_mac, ring_name,
       stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
       completed_workouts, avg_bdr_is_estimated, file_path"""

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

t0 = time.time()
total_rows = 0

for ci in range(total_chunks):
    if ci in done:
        continue
    batch = missing[ci*CHUNK:(ci+1)*CHUNK]
    cur = conn.cursor()
    cur.execute(f"SELECT {COLUMNS} FROM archive_entries WHERE serial_lower = ? ORDER BY saved_at", ("__NEVER__",))

    rows = []
    for sn in batch:
        cur.execute(f"SELECT {COLUMNS} FROM archive_entries WHERE serial_lower = ? ORDER BY saved_at", (sn,))
        for r in cur.fetchall():
            d = dict(r)
            fp = d.get("file_path", "")
            if fp:
                p = Path(fp)
                d["date"] = p.parent.name if p.parent else ""
                d["time"] = p.stem if p else ""
            else:
                d["date"] = ""
                d["time"] = ""
            d["avg_bdr"] = d.get("machine_avg_bdr")
            d["test_start"] = to_epoch(d.get("start_time"))
            d["last_update"] = to_epoch(d.get("last_update"))
            d["battery_current"] = d.get("bdr")
            d["avg_bdr_is_stale"] = False
            if d.get("avg_bdr_is_estimated") is not None:
                d["avg_bdr_is_estimated"] = bool(d["avg_bdr_is_estimated"])
            rows.append(d)

    fn = os.path.join(CHUNK_DIR, f"chunk_{ci:04d}.json")
    with open(fn, "w") as f:
        json.dump(rows, f)
    total_rows += len(rows)
    elapsed = time.time() - t0
    print(f"Chunk {ci+1}/{total_chunks}: {len(batch)} serials, {len(rows)} rows ({elapsed:.0f}s) [total: {total_rows:,}]")

conn.close()
print(f"\nDone: {total_rows:,} rows in {time.time()-t0:.0f}s")
