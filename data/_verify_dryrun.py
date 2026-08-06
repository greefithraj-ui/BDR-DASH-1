"""Verify dry-run backfill: row counts, search results, avg_bdr values."""
import sqlite3, sys, json, time
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import search_archive_in_pg, get_connection

with open(r"D:\BDR\data\dryrun_result.json") as f:
    result = json.load(f)
samples = result["samples"]
print(f"Verifying {len(samples)} backfilled serials\n")

# 1. Row count comparison (PG vs SQLite)
print("=== ROW COUNT COMPARISON ===")
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT serial_lower, COUNT(*) FROM archive_entries WHERE serial_lower = ANY(%s) GROUP BY serial_lower", (samples,))
    pg_counts = dict(cur.fetchall())
pg_conn.close()

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()
BATCH = 500
sq_counts = {}
for i in range(0, len(samples), BATCH):
    batch = samples[i:i+BATCH]
    placeholders = ",".join("?" for _ in batch)
    cur.execute(f"SELECT serial_lower, COUNT(*) FROM archive_entries WHERE serial_lower IN ({placeholders}) GROUP BY serial_lower", batch)
    sq_counts.update(cur.fetchall())
conn.close()

mismatches = []
for sn in samples:
    pg_c = pg_counts.get(sn, 0)
    sq_c = sq_counts.get(sn, 0)
    match = "OK" if pg_c == sq_c else "MISMATCH"
    if pg_c != sq_c:
        mismatches.append((sn, pg_c, sq_c))
    if match != "OK":
        print(f"  {sn}: PG={pg_c}, SQLite={sq_c} {match}")

if not mismatches:
    print(f"  All {len(samples)} serials: row counts match")
else:
    print(f"  {len(mismatches)} mismatches:")
    for sn, pg_c, sq_c in mismatches[:10]:
        print(f"    {sn}: PG={pg_c}, SQLite={sq_c}")

# 2. search_archive_in_pg verification
print(f"\n=== SEARCH FUNCTION VERIFICATION ===")
t0 = time.time()
search_results = search_archive_in_pg(samples)
print(f"  search_archive_in_pg returned {sum(len(v) for v in search_results.values())} rows for {len(samples)} serials ({time.time()-t0:.1f}s)")

empty = [sn for sn in samples if not search_results.get(sn)]
print(f"  Serials with no results: {len(empty)}")
if empty:
    for sn in empty[:5]:
        print(f"    {sn}")

# 3. avg_bdr spot check
print(f"\n=== AVG_BDR SPOT CHECK ===")
for sn in samples[:10]:
    rows = search_results.get(sn, [])
    if rows:
        latest = rows[0]
        avg = latest.get("avg_bdr")
        state = latest.get("state", "")
        ma = latest.get("machine", "")
        print(f"  {sn}: avg_bdr={avg}, state={state}, machine={ma}, rows={len(rows)}")
    else:
        print(f"  {sn}: NO RESULTS")

# 4. Confirm these serials now hit PG in hybrid search (not SQLite fallback)
print(f"\n=== HYBRID SEARCH CHECK (pg=N, sqlite_fallback=M) ===")
from data.postgres_db import search_archive_in_pg as pg_search
from data.api import _search_archive_db_for_serials
pg_res = pg_search(samples)
sqlite_fb = _search_archive_db_for_serials([s for s in samples if not pg_res.get(s)])
print(f"  PG results: {sum(len(v) for v in pg_res.values())} rows")
print(f"  SQLite fallback needed: {len([s for s in samples if not pg_res.get(s)])} serials")

print(f"\n=== SUMMARY ===")
print(f"  Backfilled: {len(samples)} serials, {result['inserted']} rows")
print(f"  Row count mismatches: {len(mismatches)}")
print(f"  Empty search results: {len(empty)}")
print(f"  All previously-missing serials now served from PG: {'YES' if len([s for s in samples if not pg_res.get(s)]) == 0 else 'NO'}")
