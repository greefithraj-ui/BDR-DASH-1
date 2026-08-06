import sqlite3
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=10)
cur = conn.cursor()
cur.execute("PRAGMA table_info(archive_entries)")
for row in cur.fetchall():
    print(row)
conn.close()
