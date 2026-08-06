"""Extract missing serials: in SQLite but not in PG archive_entries."""
import sqlite3, sys, os, json, time
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import get_connection

# 1. Get PG serials (fast)
print("Loading PG serials...")
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
    pg_serials = set(r[0] for r in cur.fetchall() if r[0])
pg_conn.close()
print(f"  PG serials: {len(pg_serials)}")

# 2. Get all SQLite serials (indexed, ~5s)
print("Loading SQLite serials...")
conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()
t0 = time.time()
cur.execute("SELECT DISTINCT serial_lower FROM archive_entries")
all_sqlite = set(r[0] for r in cur.fetchall() if r[0])
print(f"  SQLite serials: {len(all_sqlite)} ({time.time()-t0:.1f}s)")

# 3. Find missing
missing = all_sqlite - pg_serials
extra = pg_serials - all_sqlite
print(f"\nMissing from PG: {len(missing)}")
print(f"Extra in PG (not in SQLite): {len(extra)}")

# 4. For each missing serial, get date range and row count from SQLite
print("\nExtracting details for missing serials...")
t0 = time.time()
missing_details = {}
for i, sn in enumerate(sorted(missing)):
    cur.execute("""
        SELECT MIN(saved_at), MAX(saved_at), COUNT(*)
        FROM archive_entries WHERE serial_lower = ?
    """, (sn,))
    mn, mx, cnt = cur.fetchone()
    missing_details[sn] = {"min": mn, "max": mx, "count": cnt,
                           "last_day": mx[:10] if mx else "unknown"}
    if (i+1) % 500 == 0:
        print(f"  ... {i+1}/{len(missing)} ({time.time()-t0:.1f}s)")
conn.close()
print(f"  Done in {time.time()-t0:.1f}s")

# 5. Group by last-seen date
by_day = {}
for sn, d in missing_details.items():
    by_day.setdefault(d["last_day"], []).append((sn, d))
print(f"\nMissing serials by last-seen date:")
for day in sorted(by_day.keys()):
    items = by_day[day]
    print(f"  {day}: {len(items)} serials")

# 6. Pick 50 samples: 30 pre-Jul-9, 20 Jul-9+
pre_jul9 = [(sn, d) for sn, d in missing_details.items() if d["last_day"] < "2026-07-09"]
post_jul9 = [(sn, d) for sn, d in missing_details.items() if d["last_day"] >= "2026-07-09"]
import random
random.seed(42)
sample_pre = [sn for sn, _ in random.sample(pre_jul9, min(30, len(pre_jul9)))]
sample_post = [sn for sn, _ in random.sample(post_jul9, min(20, len(post_jul9)))]
samples = sample_pre + sample_post

print(f"\nDry-run samples: {len(samples)} serials")
print(f"  Pre-Jul-9: {len(sample_pre)}")
print(f"  Jul-9+: {len(sample_post)}")

# 7. Save full missing list and samples to files
output = {
    "missing_serials": sorted(list(missing)),
    "missing_count": len(missing),
    "details": missing_details,
    "samples": samples,
    "sample_pre": sample_pre,
    "sample_post": sample_post,
}
out_path = os.path.join(os.path.dirname(__file__), "backfill_missing.json")
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)
print(f"\nSaved to {out_path}")

# 8. Show sample details
print("\nSample serials for dry run:")
for sn in samples[:10]:
    d = missing_details[sn]
    print(f"  {sn}: {d['min'][:19]} to {d['max'][:19]} ({d['count']} rows)")
if len(samples) > 10:
    print(f"  ... +{len(samples)-10} more")
