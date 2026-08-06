"""Build covering index on SQLite archive_entries for fast serial lookups."""
import sqlite3, time

DB = r"D:\BDR\data\archive.db"
print("Enabling WAL mode...")
conn = sqlite3.connect(DB, timeout=120)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
print(f"WAL mode: {conn.execute('PRAGMA journal_mode').fetchone()[0]}")

print("Creating covering index (this may take several minutes)...")
t0 = time.time()
try:
    conn.execute("PRAGMA busy_timeout=120000")
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_se_backfill
        ON archive_entries(LOWER(serial_number), saved_at, machine, machine_avg_bdr,
                           avg_bdr_is_estimated, state, slot, firmware_version,
                           ring_mac, ring_name, stored_avg_bdr, inter_cycle_avg_bdr,
                           phase, cycle, completed_workouts, snapshots, total_cycles,
                           completed_cycles, start_time, last_update, bdr)
    """)
    conn.commit()
    elapsed = time.time() - t0
    print(f"Index created in {elapsed:.1f}s")
except Exception as e:
    elapsed = time.time() - t0
    print(f"Failed after {elapsed:.1f}s: {e}")
finally:
    conn.close()
