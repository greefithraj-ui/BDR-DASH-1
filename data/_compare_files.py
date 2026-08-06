"""Compare extracted SQLite summary against PG serials."""
import sys
sys.path.insert(0, r"D:\BDR")

# Read PG serials
from data.postgres_db import get_connection
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
    pg_serials = set(r[0] for r in cur.fetchall() if r[0])
pg_conn.close()
print(f"PG serials: {len(pg_serials)}")

# Read SQLite summary
sqlite_data = {}
with open(r"C:\Users\meshe\AppData\Local\Temp\sqlite_summary.txt") as f:
    for line in f:
        parts = line.strip().split("\t")
        if len(parts) == 4:
            sn, min_d, max_d, cnt = parts
            sqlite_data[sn] = (min_d, max_d, int(cnt))

print(f"SQLite serials: {len(sqlite_data)}")

missing = {s: sqlite_data[s] for s in sqlite_data if s not in pg_serials}
print(f"Missing from PG: {len(missing)}")

# Group by earliest date
by_day = {}
for s, (mn, mx, c) in missing.items():
    day = mn[:10] if mn else "unknown"
    by_day.setdefault(day, []).append((s, mx, c))

for day in sorted(by_day.keys()):
    items = by_day[day]
    print(f"  {day}: {len(items)} serials")
    for s, mx, c in items[:2]:
        print(f"    {s} last={mx[:19]} ({c} rows)")
    if len(items) > 2:
        print(f"    ... +{len(items)-2} more")

# Check: are any missing serials from Jul 9+ (should be in PG)?
recent_missing = {s: v for s, v in missing.items() if v[0][:10] >= "2026-07-09"}
print(f"\nMissing serials with data from Jul 9+ (should be in PG): {len(recent_missing)}")
for s, (mn, mx, c) in sorted(recent_missing.items())[:10]:
    print(f"  {s}: {mn[:19]} to {mx[:19]} ({c} rows)")
