import sqlite3
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()
cur.execute("SELECT substr(saved_at,1,10) as d, COUNT(*) FROM archive_entries GROUP BY d ORDER BY d")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]:,} rows")
conn.close()
