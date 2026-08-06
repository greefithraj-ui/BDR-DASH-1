import sqlite3
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=30)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM archive_entries WHERE serial_lower IS NOT NULL AND serial_lower != ''")
filled = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM archive_entries")
total = cur.fetchone()[0]
print(f"serial_lower filled: {filled}/{total}")
cur.execute("SELECT serial_lower FROM archive_entries WHERE serial_lower IS NOT NULL LIMIT 3")
print("Samples:", [r[0] for r in cur.fetchall()])
# Test: can we query efficiently using serial_lower?
import time
t0 = time.time()
cur.execute("SELECT COUNT(DISTINCT serial_lower) FROM archive_entries")
distinct = cur.fetchone()[0]
elapsed = time.time() - t0
print(f"Distinct serial_lower count: {distinct} (took {elapsed:.1f}s)")
conn.close()
