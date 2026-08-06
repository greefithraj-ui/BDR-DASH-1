"""Quick check: date ranges of serials missing from PG."""
import sqlite3, os, sys
sys.path.insert(0, ".")

DB_PATH = os.path.join(os.path.dirname(__file__), "archive.db")
conn = sqlite3.connect(DB_PATH, timeout=60)
cur = conn.cursor()

from data.postgres_db import get_connection
pg_conn = get_connection()
with pg_conn.cursor() as pgcur:
    pgcur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
    pg_serials = set(r[0] for r in pgcur.fetchall() if r[0])
pg_conn.close()

cur.execute("SELECT LOWER(serial_number), MIN(saved_at), MAX(saved_at), COUNT(*) FROM archive_entries GROUP BY LOWER(serial_number)")
missing = {}
for row in cur.fetchall():
    if row[0] and row[0] not in pg_serials:
        missing[row[0]] = (row[1], row[2], row[3])
conn.close()

print(f"Missing: {len(missing)} serials")

# Group by earliest month-day
by_date = {}
for s, (mn, mx, c) in missing.items():
    day = mn[:10] if mn else "unknown"
    by_date.setdefault(day, []).append((s, mx, c))

for day in sorted(by_date.keys()):
    items = by_date[day]
    print(f"  {day}: {len(items)} serials (example: {items[0][0]}, last seen {items[0][1][:19]})")
