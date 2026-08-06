import sys
sys.path.insert(0, ".")
from data.postgres_db import search_archive_in_pg

keys = ["ra-ch3-lfk-w1-ag07-0000417", "ra-ch3-lfk-w1-ag06-0000060"]
result = search_archive_in_pg(keys)
for k, rows in result.items():
    print(f"{k}: {len(rows)} rows")
    for r in rows:
        m = r["machine"]
        t = r["type"]
        b = r["avg_bdr"]
        s = r["state"]
        sa = r["saved_at"][:20]
        print(f"  {m} | type={t} | avg_bdr={b} | state={s} | saved_at={sa}")
print("OK")
