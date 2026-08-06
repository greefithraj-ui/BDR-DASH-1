import sys, json, time
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import search_archive_in_pg, get_connection

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)

sample = missing[:200]
pg_res = search_archive_in_pg(sample)
need_fb = [s for s in sample if not pg_res.get(s)]
print(f"PG returned results for {200-len(need_fb)}/200")
print(f"SQLite fallback needed: {len(need_fb)}")

conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM archive_entries")
    total = cur.fetchone()[0]
    cur.execute("SELECT pg_size_pretty(pg_total_relation_size('archive_entries'))")
    size = cur.fetchone()[0]
print(f"\nTotal PG rows: {total:,}")
print(f"Table size: {size}")
conn.close()
