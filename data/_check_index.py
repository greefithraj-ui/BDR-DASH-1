import sqlite3
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=10)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%backfill%'")
print("backfill index:", cur.fetchall())
cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
print("all indexes:", [r[0] for r in cur.fetchall()])
conn.close()
