"""Investigate the 2441 serials missing from PG."""
import sqlite3, os, sys
sys.path.insert(0, ".")

DB_PATH = os.path.join(os.path.dirname(__file__), "archive.db")
conn = sqlite3.connect(DB_PATH, timeout=60)
cur = conn.cursor()

# Get PG serials
from data.postgres_db import get_connection
pg_conn = get_connection()
with pg_conn.cursor() as pgcur:
    pgcur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
    pg_serials = set(r[0] for r in pgcur.fetchall() if r[0])
pg_conn.close()

# Get all SQLite serials with their date ranges
cur.execute("""
    SELECT LOWER(serial_number), MIN(saved_at), MAX(saved_at), COUNT(*) as cnt
    FROM archive_entries
    GROUP BY LOWER(serial_number)
""")
all_sqlite = {}
for row in cur.fetchall():
    all_sqlite[row[0]] = (row[1], row[2], row[3])
conn.close()

missing = {s: all_sqlite[s] for s in all_sqlite if s not in pg_serials}
print(f"Total missing serials: {len(missing)}")

# Group by earliest date
date_groups = {}
for s, (min_d, max_d, cnt) in missing.items():
    prefix = min_d[:10] if min_d else "unknown"
    date_groups.setdefault(prefix, []).append((s, min_d, max_d, cnt))

print("\nMissing serials grouped by earliest date:")
for date in sorted(date_groups.keys()):
    items = date_groups[date]
    print(f"  {date}: {len(items)} serials")
    for s, mn, mx, c in items[:3]:
        print(f"    {s}: {mn[:19]} to {mx[:19]} ({c} rows)")
    if len(items) > 3:
        print(f"    ... and {len(items)-3} more")

# Check if missing serials exist on disk in the archive
archive_root = os.path.join(os.path.dirname(__file__), "..", "DESTINATION", "archive")
if os.path.isdir(archive_root):
    found_on_disk = 0
    missing_on_disk = 0
    for s, (mn, mx, cnt) in list(missing.items())[:100]:
        # Search for this serial in the archive directories
        found = False
        for machine_dir in os.listdir(archive_root):
            machine_path = os.path.join(archive_root, machine_dir)
            if not os.path.isdir(machine_path):
                continue
            for date_dir in os.listdir(machine_path):
                date_path = os.path.join(machine_path, date_dir)
                if not os.path.isdir(date_path):
                    continue
                for fname in os.listdir(date_path):
                    if fname.endswith(".json"):
                        fpath = os.path.join(date_path, fname)
                        try:
                            import json
                            with open(fpath, "r") as f:
                                data = json.load(f)
                            for slot_id, slot_data in data.get("slots", {}).items():
                                if slot_data.get("serial_number", "").lower() == s:
                                    found = True
                                    break
                        except:
                            pass
                    if found:
                        break
                if found:
                    break
            if found:
                break
        if found:
            found_on_disk += 1
        else:
            missing_on_disk += 1

    print(f"\nDisk check (first 100 missing serials):")
    print(f"  Found on disk: {found_on_disk}")
    print(f"  NOT on disk: {missing_on_disk}")
