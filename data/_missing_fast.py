"""Fast: extract missing serials (SQLite distinct minus PG distinct)."""
import sqlite3, sys, json, time
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import get_connection

pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
    pg_serials = set(r[0] for r in cur.fetchall() if r[0])
pg_conn.close()
print(f"PG: {len(pg_serials)} serials")

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()
cur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
all_sqlite = set(r[0] for r in cur.fetchall() if r[0])
conn.close()
print(f"SQLite: {len(all_sqlite)} serials")

missing = sorted(all_sqlite - pg_serials)
print(f"Missing: {len(missing)}")

with open(r"D:\BDR\data\backfill_missing_list.json", "w") as f:
    json.dump(missing, f)
print("Saved to backfill_missing_list.json")
