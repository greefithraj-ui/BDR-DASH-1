"""Test: reproduce the dry-run extraction speed."""
import sqlite3, time

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=30)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = __import__("json").load(f)

# Dry run used individual queries per serial
sn = missing[0]
t0 = time.time()
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
print(f"Single serial: {len(rows)} rows ({time.time()-t0:.3f}s)")

# Batch of 50
batch = missing[:50]
t0 = time.time()
all_rows = []
for s in batch:
    cur.execute("""
        SELECT serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
               snapshots, total_cycles, completed_cycles, start_time, last_update,
               saved_at, slot, firmware_version, ring_mac, ring_name,
               stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
               completed_workouts, avg_bdr_is_estimated, file_path
        FROM archive_entries
        WHERE serial_lower = ?
        ORDER BY saved_at
    """, (s,))
    all_rows.extend([dict(r) for r in cur.fetchall()])
print(f"50 serials (individual queries): {len(all_rows)} rows ({time.time()-t0:.1f}s)")

# Batch of 50 via IN clause
t0 = time.time()
placeholders = ",".join("?" for _ in batch)
cur.execute(f"""
    SELECT serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
           snapshots, total_cycles, completed_cycles, start_time, last_update,
           saved_at, slot, firmware_version, ring_mac, ring_name,
           stored_avg_bdr, inter_cycle_avg_bdr, phase, cycle,
           completed_workouts, avg_bdr_is_estimated, file_path
    FROM archive_entries
    WHERE serial_lower IN ({placeholders})
    ORDER BY serial_lower, saved_at
""", batch)
all_rows2 = [dict(r) for r in cur.fetchall()]
print(f"50 serials (IN clause): {len(all_rows2)} rows ({time.time()-t0:.1f}s)")

conn.close()
