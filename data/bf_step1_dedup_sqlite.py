"""Step 1: Get daily-latest and best-good from SQLite using simple GROUP BY queries."""
import sqlite3, json, time

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)
print(f"Processing {len(missing)} serials...")

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()

# For each serial_lower, get the max saved_at per day
# Then separately get the best-good fallback row
# This avoids window functions entirely

results = {}  # key: "serial_lower|machine|saved_at" -> row dict
t0 = time.time()
BATCH = 200

for i in range(0, len(missing), BATCH):
    batch = missing[i:i+BATCH]
    placeholders = ",".join("?" for _ in batch)

    # Daily latest: get max(saved_at) per (serial_lower, machine, day)
    # day = substr(saved_at, 1, 10)
    cur.execute(f"""
        SELECT serial_lower, machine, substr(saved_at, 1, 10) as day_key, max(saved_at) as latest_saved_at
        FROM archive_entries
        WHERE serial_lower IN ({placeholders})
        GROUP BY serial_lower, machine, substr(saved_at, 1, 10)
    """, batch)
    key_rows = cur.fetchall()
    print(f"  Batch {i//BATCH+1}: {len(key_rows)} daily keys ({time.time()-t0:.0f}s)")

    # Now fetch full rows for these keys - batch by (serial_lower, day_key)
    # Collect unique (serial_lower, latest_saved_at) pairs
    fetch_keys = [(r[0], r[3]) for r in key_rows]  # (serial_lower, saved_at)

    # Fetch in sub-batches
    for j in range(0, len(fetch_keys), 500):
        sub = fetch_keys[j:j+500]
        sub_placeholders = ",".join(f"({sn},{sv})" for sn, sv in sub)
        cur.execute(f"""
            SELECT serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
                   snapshots, total_cycles, completed_cycles, start_time, last_update,
                   saved_at, slot, firmware_version, ring_mac, ring_name,
                   stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
                   completed_workouts, avg_bdr_is_estimated, file_path
            FROM archive_entries
            WHERE (serial_lower, saved_at) IN ({sub_placeholders})
        """)
        for r in cur.fetchall():
            d = dict(r)
            key = f"{d['serial_lower']}|{d.get('machine','')}|{d['saved_at']}"
            results[key] = d

    if (i+BATCH) % 1000 == 0 or i+BATCH >= len(missing):
        print(f"  Progress: {min(i+BATCH, len(missing))}/{len(missing)} serials, {len(results):,} daily-latest rows ({time.time()-t0:.0f}s)")

print(f"Daily-latest rows: {len(results):,}")

# Best-good fallback: for (serial_lower, machine) combos with no good avg_bdr
sm_has_good = set()
for d in results.values():
    avg = d.get("avg_bdr")
    if avg is not None and avg != 0.0:
        sm_has_good.add((d["serial_lower"], d.get("machine", "")))

all_sm = set((d["serial_lower"], d.get("machine", "")) for d in results.values())
sm_needs_fallback = all_sm - sm_has_good
print(f"Serials needing fallback: {len(sm_needs_fallback)}")

# Get all unique serials for fallback query
fb_serials = list(set(sn for sn, _ in sm_needs_fallback))
fb_added = 0
for i in range(0, len(fb_serials), BATCH):
    batch = fb_serials[i:i+BATCH]
    placeholders = ",".join("?" for _ in batch)
    # Best good: first non-null/non-zero machine_avg_bdr per serial_lower, machine
    cur.execute(f"""
        SELECT serial_lower, machine, max(saved_at) as best_saved_at
        FROM archive_entries
        WHERE serial_lower IN ({placeholders})
          AND machine_avg_bdr IS NOT NULL AND machine_avg_bdr != 0
        GROUP BY serial_lower, machine
    """, batch)
    fb_keys = cur.fetchall()
    for r in fb_keys:
        sn, machine, sv = r[0], r[1], r[2]
        key = f"{sn}|{machine or ''}|{sv}"
        if key not in results:
            cur2 = conn.cursor()
            cur2.execute("""
                SELECT serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
                       snapshots, total_cycles, completed_cycles, start_time, last_update,
                       saved_at, slot, firmware_version, ring_mac, ring_name,
                       stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
                       completed_workouts, avg_bdr_is_estimated, file_path
                FROM archive_entries
                WHERE serial_lower = ? AND saved_at = ?
            """, (sn, sv))
            row = cur2.fetchone()
            if row:
                d = dict(row)
                key2 = f"{d['serial_lower']}|{d.get('machine','')}|{d['saved_at']}"
                results[key2] = d
                fb_added += 1

print(f"Fallback rows added: {fb_added}")
print(f"Total rows: {len(results):,}")

conn.close()

# Save
all_rows = list(results.values())
with open(r"D:\BDR\data\backfill_deduped.json", "w") as f:
    json.dump(all_rows, f)
print(f"Saved to backfill_deduped.json ({len(all_rows):,} rows)")
