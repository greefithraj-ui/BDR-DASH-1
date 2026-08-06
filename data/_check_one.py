"""Quick SQLite check for this serial only."""
import sqlite3
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()
cur.execute("""
    SELECT LOWER(serial_number), machine, machine_avg_bdr, state, saved_at, slot,
           completed_cycles, total_cycles
    FROM archive_entries
    WHERE LOWER(serial_number) = 'ra-ch3-lfn-w1-aa08-0000102'
    ORDER BY saved_at DESC
""")
rows = cur.fetchall()
print(f"SQLite: {len(rows)} rows")
for r in rows:
    print(f"  machine={r[1]}, avg_bdr={r[2]}, state={r[3]}, saved_at={r[4][:19]}, slot={r[5]}, cycles={r[6]}/{r[7]}")
conn.close()
