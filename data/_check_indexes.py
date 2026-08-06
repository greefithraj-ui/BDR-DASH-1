import sqlite3
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=5)
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='archive_entries'")
for r in cur.fetchall():
    print(f"{r[0]}: {r[1]}")
conn.close()
