"""Check if the 164 Jul9+ missing serials have good data in SQLite that should be in PG."""
import sqlite3, sys
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import get_connection

pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
    pg_serials = set(r[0] for r in cur.fetchall() if r[0])
pg_conn.close()

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()
cur.execute("SELECT LOWER(serial_number), MIN(saved_at), MAX(saved_at), COUNT(*) FROM archive_entries GROUP BY LOWER(serial_number)")

recent_missing = []
for row in cur:
    sn, mn, mx, cnt = row
    if sn and sn not in pg_serials and mx >= "2026-07-09":
        recent_missing.append((sn, mn, mx, cnt))
conn.close()

print(f"Missing serials with data on/after Jul 9: {len(recent_missing)}")
print()

# Count by last-seen date
by_last = {}
for sn, mn, mx, cnt in recent_missing:
    day = mx[:10]
    by_last.setdefault(day, []).append((sn, mn, mx, cnt))

for day in sorted(by_last.keys()):
    items = by_last[day]
    print(f"Last seen {day}: {len(items)} serials")
    for s, mn, mx, c in items[:3]:
        print(f"  {s}: {mn[:10]} to {mx[:19]} ({c} rows)")
    if len(items) > 3:
        print(f"  ... +{len(items)-3} more")

# Also check: do these serials appear in ring_status?
print("\nChecking ring_status for these...")
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    for sn, mn, mx, cnt in recent_missing[:5]:
        cur.execute("SELECT serial_number, machine FROM ring_status WHERE LOWER(serial_number) = %s", (sn,))
        rs = cur.fetchall()
        if rs:
            print(f"  {sn}: FOUND in ring_status ({rs[0][1]})")
        else:
            print(f"  {sn}: NOT in ring_status")
pg_conn.close()
