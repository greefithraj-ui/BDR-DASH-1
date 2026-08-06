"""Sample 50 missing serials to check their date ranges in SQLite."""
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

# Get serials not in PG, with their date ranges
cur.execute("""
    SELECT LOWER(serial_number), MIN(saved_at), MAX(saved_at), COUNT(*)
    FROM archive_entries
    GROUP BY LOWER(serial_number)
""")
missing = []
for row in cur:
    if row[0] and row[0] not in pg_serials:
        missing.append(row)
conn.close()

print(f"Total missing serials: {len(missing)}")

# Group by earliest date
by_day = {}
for sn, mn, mx, cnt in missing:
    day = mn[:10] if mn else "unknown"
    by_day.setdefault(day, []).append((sn, mn, mx, cnt))

for day in sorted(by_day.keys()):
    items = by_day[day]
    print(f"  {day}: {len(items)} serials")
    for s, mn, mx, c in items[:2]:
        print(f"    {s}: {mn[:19]} to {mx[:19]} ({c} rows)")

# How many have ANY data on or after Jul 9?
recent = [m for m in missing if m[2] >= "2026-07-09"]
print(f"\nMissing serials with ANY data on/after Jul 9: {len(recent)}")
for sn, mn, mx, cnt in recent[:10]:
    print(f"  {sn}: {mn[:19]} to {mx[:19]} ({cnt} rows)")
