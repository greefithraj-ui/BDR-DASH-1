import sys, json, time
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import search_archive_in_pg, get_connection

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)

print(f"=== FULL VERIFICATION: {len(missing)} serials ===", flush=True)

t0 = time.time()
ok = 0
empty = 0
empty_serials = []
BATCH = 200
for i in range(0, len(missing), BATCH):
    batch = missing[i:i+BATCH]
    results = search_archive_in_pg(batch)
    for sn in batch:
        rows = results.get(sn, [])
        if rows:
            ok += 1
        else:
            empty += 1
            empty_serials.append(sn)

print(f"Search OK: {ok}/{len(missing)}", flush=True)
print(f"Empty: {empty}", flush=True)
if empty_serials:
    print(f"Empty serials: {empty_serials[:10]}", flush=True)
print(f"Verification time: {time.time()-t0:.0f}s", flush=True)

print(f"\n=== AVG_BDR SANITY CHECK ===", flush=True)
conn = get_connection()
with conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM archive_entries WHERE avg_bdr IS NOT NULL AND avg_bdr != 0")
    good = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM archive_entries WHERE avg_bdr IS NULL OR avg_bdr = 0")
    null_zero = cur.fetchone()[0]
    cur.execute("SELECT count(DISTINCT serial_lower) FROM archive_entries")
    dist_serials = cur.fetchone()[0]
    cur.execute("SELECT count(DISTINCT serial_lower || '|' || COALESCE(machine,'')) FROM archive_entries")
    dist_sm = cur.fetchone()[0]
    cur.execute("SELECT min(saved_at), max(saved_at) FROM archive_entries")
    min_max = cur.fetchone()
print(f"Distinct serials: {dist_serials:,}", flush=True)
print(f"Distinct (serial, machine): {dist_sm:,}", flush=True)
print(f"Rows with good avg_bdr: {good:,}", flush=True)
print(f"Rows with NULL/0 avg_bdr: {null_zero:,}", flush=True)
print(f"Date range: {min_max[0]} to {min_max[1]}", flush=True)

print(f"\n=== STORAGE COMPARISON ===", flush=True)
with conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM archive_entries")
    total_rows = cur.fetchone()[0]
    cur.execute("SELECT pg_size_pretty(pg_total_relation_size('archive_entries'))")
    total_size = cur.fetchone()[0]
    cur.execute("SELECT pg_size_pretty(pg_relation_size('archive_entries'))")
    table_size = cur.fetchone()[0]
    cur.execute("SELECT pg_size_pretty(pg_indexes_size('archive_entries'))")
    index_size = cur.fetchone()[0]
print(f"Total rows: {total_rows:,}", flush=True)
print(f"Total (table + indexes): {total_size}", flush=True)
print(f"Table only: {table_size}", flush=True)
print(f"Indexes: {index_size}", flush=True)

# Before backfill numbers for comparison
print(f"\n=== BEFORE vs AFTER ===", flush=True)
print(f"Before backfill: 92,161 rows, ~102 MB", flush=True)
print(f"After backfill:  {total_rows:,} rows, {total_size}", flush=True)
print(f"Added: {total_rows - 92161:,} rows", flush=True)

conn.close()
