import sys, json
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import search_archive_in_pg, get_connection

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)

test_missing = missing[0]

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT DISTINCT serial_lower FROM archive_entries WHERE serial_lower NOT IN %s LIMIT 1", (tuple(missing[:100]),))
    row = cur.fetchone()
    test_normal = row[0] if row else missing[500]
conn.close()

results = search_archive_in_pg([test_missing, test_normal])
print(f"Formerly-missing serial: {test_missing}")
print(f"  PG rows: {len(results.get(test_missing, []))}")
print(f"Normal serial: {test_normal}")
print(f"  PG rows: {len(results.get(test_normal, []))}")
