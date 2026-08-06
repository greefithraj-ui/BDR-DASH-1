"""Compare SQLite archive.db serials against PG archive_entries to prove full coverage."""
import sqlite3, os, sys
sys.path.insert(0, ".")

DB_PATH = os.path.join(os.path.dirname(__file__), "archive.db")
if not os.path.exists(DB_PATH):
    print("archive.db not found")
    sys.exit(1)

conn = sqlite3.connect(DB_PATH, timeout=30)
try:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM archive_entries")
    total_rows = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT LOWER(serial_number)) FROM archive_entries")
    total_sqlite_serials = cur.fetchone()[0]
    cur.execute("SELECT DISTINCT LOWER(serial_number) FROM archive_entries")
    sqlite_serials = set(r[0] for r in cur.fetchall() if r[0])
finally:
    conn.close()

print(f"SQLite: {total_rows} rows, {total_sqlite_serials} unique serials")

from data.postgres_db import get_connection
pg_conn = get_connection()
try:
    with pg_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM archive_entries")
        pg_rows = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT serial_lower) FROM archive_entries")
        pg_serials_count = cur.fetchone()[0]
        cur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
        pg_serials = set(r[0] for r in cur.fetchall() if r[0])
finally:
    pg_conn.close()

print(f"PG: {pg_rows} rows, {pg_serials_count} unique serials")

missing_in_pg = sqlite_serials - pg_serials
extra_in_pg = pg_serials - sqlite_serials

print(f"\nMissing from PG (in SQLite but not PG): {len(missing_in_pg)}")
if missing_in_pg:
    for s in sorted(missing_in_pg)[:20]:
        print(f"  {s}")
    if len(missing_in_pg) > 20:
        print(f"  ... and {len(missing_in_pg) - 20} more")

print(f"\nExtra in PG (in PG but not SQLite): {len(extra_in_pg)}")
if extra_in_pg:
    for s in sorted(extra_in_pg)[:20]:
        print(f"  {s}")
    if len(extra_in_pg) > 20:
        print(f"  ... and {len(extra_in_pg) - 20} more")

coverage = len(sqlite_serials - missing_in_pg) / len(sqlite_serials) * 100 if sqlite_serials else 0
print(f"\nPG coverage of SQLite serials: {coverage:.1f}%")
print(f"RESULT: {'PASS' if not missing_in_pg else 'FAIL - missing serials found'}")
