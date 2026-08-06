"""Check if PG row count difference is purely duplicate (serial, machine, saved_at) tuples in SQLite."""
import sqlite3, json

with open(r"D:\BDR\data\dryrun_result.json") as f:
    samples = json.load(f)["samples"]

conn = sqlite3.connect(r"D:\BDR\data\archive.db", timeout=60)
cur = conn.cursor()

total_raw = 0
total_dedup = 0

for sn in samples[:5]:
    cur.execute("SELECT COUNT(*) FROM archive_entries WHERE serial_lower = ?", (sn,))
    raw = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT serial_lower, machine, saved_at FROM archive_entries WHERE serial_lower = ?)", (sn,))
    dedup = cur.fetchone()[0]
    dupes = raw - dedup
    total_raw += raw
    total_dedup += dedup
    print(f"  {sn}: raw={raw}, deduped={dedup}, duplicates={dupes}")

print(f"\n  Totals (first 5): raw={total_raw}, deduped={total_dedup}, duplicates={total_raw - total_dedup}")
print(f"  Duplicate rate: {(total_raw - total_dedup) / total_raw * 100:.1f}%")
conn.close()
