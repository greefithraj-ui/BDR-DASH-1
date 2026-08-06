"""Test: can we query a large batch from SQLite quickly?"""
import sqlite3, time

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=30)
cur = conn.cursor()

# Test: query 500 serials
with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = __import__("json").load(f)

batch = missing[:500]
placeholders = ",".join("?" for _ in batch)
t0 = time.time()
cur.execute(f"""
    SELECT count(*) FROM archive_entries
    WHERE serial_lower IN ({placeholders})
""", batch)
count = cur.fetchone()[0]
print(f"500 serials: {count:,} rows ({time.time()-t0:.1f}s)")

# Test: fetch all rows for 50 serials
batch50 = missing[:500:10]  # every 10th = 50 serials
placeholders50 = ",".join("?" for _ in batch50)
t0 = time.time()
cur.execute(f"""
    SELECT serial_lower, saved_at, machine, machine_avg_bdr
    FROM archive_entries
    WHERE serial_lower IN ({placeholders50})
""", batch50)
rows = cur.fetchall()
print(f"50 serials: {len(rows):,} rows fetched ({time.time()-t0:.1f}s)")

conn.close()
