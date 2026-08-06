"""Get details for missing serials using batch queries."""
import sqlite3, json, time

with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)
print(f"Missing serials: {len(missing)}")

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()

# Batch query: get min/max/count for all missing serials at once
BATCH = 500
details = {}
t0 = time.time()
for i in range(0, len(missing), BATCH):
    batch = missing[i:i+BATCH]
    placeholders = ",".join("?" for _ in batch)
    cur.execute(f"""
        SELECT serial_lower, MIN(saved_at), MAX(saved_at), COUNT(*)
        FROM archive_entries
        WHERE serial_lower IN ({placeholders})
        GROUP BY serial_lower
    """, batch)
    for row in cur:
        details[row[0]] = {"min": row[1], "max": row[2], "count": row[3],
                           "last_day": row[2][:10] if row[2] else "unknown"}
    print(f"  Batch {i//BATCH + 1}: {len(batch)} serials")
conn.close()
print(f"Done in {time.time()-t0:.1f}s")

# Group by last-seen date
by_day = {}
for sn, d in details.items():
    by_day.setdefault(d["last_day"], []).append((sn, d))
print(f"\nBy last-seen date:")
for day in sorted(by_day.keys()):
    items = by_day[day]
    print(f"  {day}: {len(items)} serials")

# Pick samples: 30 pre-Jul-9, 20 Jul-9+
import random
random.seed(42)
pre = [(sn, d) for sn, d in details.items() if d["last_day"] < "2026-07-09"]
post = [(sn, d) for sn, d in details.items() if d["last_day"] >= "2026-07-09"]
sample_pre = [sn for sn, _ in random.sample(pre, min(30, len(pre)))]
sample_post = [sn for sn, _ in random.sample(post, min(20, len(post)))]
samples = sample_pre + sample_post

print(f"\nSamples: {len(samples)} ({len(sample_pre)} pre-Jul-9, {len(sample_post)} Jul-9+)")
for sn in samples[:5]:
    d = details[sn]
    print(f"  {sn}: {d['min'][:19]} to {d['max'][:19]} ({d['count']} rows)")

# Save everything
output = {"missing": missing, "details": details, "samples": samples,
          "sample_pre": sample_pre, "sample_post": sample_post}
with open(r"D:\BDR\data\backfill_plan.json", "w") as f:
    json.dump(output, f, indent=2)
print("Saved to backfill_plan.json")
