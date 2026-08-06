"""Extract a batch of serials from SQLite using temp table approach."""
import sqlite3, json, time, sys, os
from pathlib import Path
from datetime import datetime

START = int(sys.argv[1]) if len(sys.argv) > 1 else 0
COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 500
OUT_DIR = r"D:\BDR\data\bf_chunks"
os.makedirs(OUT_DIR, exist_ok=True)

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)
batch = missing[START:START+COUNT]
print(f"Serials {START}-{START+COUNT} of {len(missing)}")

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=30)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

t0=time.time()
cur.execute('DROP TABLE IF EXISTS _bf_serials')
cur.execute('CREATE TABLE _bf_serials (serial_lower TEXT)')
cur.executemany('INSERT INTO _bf_serials VALUES (?)', [(s,) for s in batch])
conn.commit()
print(f"Temp table: {time.time()-t0:.1f}s")

t0=time.time()
cur.execute('''
    SELECT a.serial_lower, a.machine, substr(a.saved_at, 1, 10) as day_key, max(a.saved_at) as latest
    FROM archive_entries a
    JOIN _bf_serials s ON a.serial_lower = s.serial_lower
    GROUP BY a.serial_lower, a.machine, substr(a.saved_at, 1, 10)
''')
daily = cur.fetchall()
print(f"Daily keys: {len(daily):,} ({time.time()-t0:.1f}s)")

t0=time.time()
cur.execute('DROP TABLE IF EXISTS _bf_keys')
cur.execute('CREATE TABLE _bf_keys (serial_lower TEXT, saved_at TEXT)')
cur.executemany('INSERT INTO _bf_keys VALUES (?,?)', [(r[0], r[3]) for r in daily])
conn.commit()
print(f"Keys table: {time.time()-t0:.1f}s")

t0=time.time()
cur.execute('''
    SELECT a.serial_number, a.serial_lower, a.machine, a.state, a.machine_avg_bdr, a.bdr,
           a.snapshots, a.total_cycles, a.completed_cycles, a.start_time, a.last_update,
           a.saved_at, a.slot, a.firmware_version, a.ring_mac, a.ring_name,
           a.stored_avg_bdr, a.inter_cycle_avg_bdr, a.phase, a.cycle,
           a.completed_workouts, a.avg_bdr_is_estimated, a.file_path
    FROM archive_entries a
    JOIN _bf_keys k ON a.serial_lower = k.serial_lower AND a.saved_at = k.saved_at
''')
daily_rows = [dict(r) for r in cur.fetchall()]
print(f"Daily-latest rows: {len(daily_rows):,} ({time.time()-t0:.1f}s)")

# Fallback: best-good per (serial_lower, machine) where all daily rows have NULL/0 avg_bdr
sm_has_good = set()
for d in daily_rows:
    avg = d.get("avg_bdr")
    if avg is not None and avg != 0.0:
        sm_has_good.add((d["serial_lower"], d.get("machine", "")))

all_sm = set((d["serial_lower"], d.get("machine", "")) for d in daily_rows)
needs_fb = all_sm - sm_has_good
print(f"Needs fallback: {len(needs_fb)}")

fallback_rows = []
if needs_fb:
    t0=time.time()
    fb_count = 0
    for sn, machine in needs_fb:
        cur.execute('''
            SELECT serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
                   snapshots, total_cycles, completed_cycles, start_time, last_update,
                   saved_at, slot, firmware_version, ring_mac, ring_name,
                   stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
                   completed_workouts, avg_bdr_is_estimated, file_path
            FROM archive_entries
            WHERE serial_lower = ? AND machine = ?
              AND machine_avg_bdr IS NOT NULL AND machine_avg_bdr != 0
            ORDER BY saved_at DESC LIMIT 1
        ''', (sn, machine))
        r = cur.fetchone()
        if r:
            fallback_rows.append(dict(r))
            fb_count += 1
    print(f"Fallback rows: {len(fallback_rows)} from {len(needs_fb)} serials ({time.time()-t0:.1f}s)")

conn.close()

all_rows = daily_rows + fallback_rows

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

for d in all_rows:
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

fn = os.path.join(OUT_DIR, f"chunk_{START:06d}.json")
with open(fn, "w") as f:
    json.dump(all_rows, f)
print(f"Saved {len(all_rows):,} rows to {fn}")
