"""Calculate projected storage after full backfill."""
import json

with open(r"D:\BDR\data\backfill_plan.json") as f:
    plan = json.load(f)

# Current state (after dry-run)
current_rows = 202759
current_total_mb = 102
current_tbl_mb = 58
current_idx_mb = 44

# Dry-run added ~194k rows (live ingestion also added some during the run)
# Original was 8,679 rows / 9 MB
original_rows = 8679
original_total_mb = 9

# Per-row cost (from dry-run delta)
added_rows = current_rows - original_rows  # ~194k
added_mb = current_total_mb - original_total_mb  # ~93 MB
per_row_bytes = (added_mb * 1024 * 1024) / added_rows
print(f"Per-row cost: {per_row_bytes:.0f} bytes/row")
print(f"  Table per-row: {((current_tbl_mb - 4) * 1024 * 1024) / added_rows:.0f} bytes")
print(f"  Index per-row: {((current_idx_mb - 5) * 1024 * 1024) / added_rows:.0f} bytes")

# Full backfill estimate
with open(r"D:\BDR\data\backfill_missing_list.json") as f:
    missing = json.load(f)

# Get average rows per serial from details
with open(r"D:\BDR\data\backfill_plan.json") as f:
    details = json.load(f)["details"]

total_sqlite_rows = sum(d["count"] for d in details.values())
avg_per_serial = total_sqlite_rows / len(details) if details else 0
print(f"\nMissing serials: {len(missing)}")
print(f"Total SQLite rows to backfill: {total_sqlite_rows:,}")
print(f"Avg rows per serial: {avg_per_serial:,.0f}")

# Estimate for ALL 2,441 serials (not just the 50 we have details for)
# The 50 samples had 147,702 rows, avg 2,954 per serial
est_total_rows = len(missing) * avg_per_serial
print(f"\nEstimated total rows for full backfill: {est_total_rows:,.0f}")

# Projected sizes
proj_tbl_mb = (current_tbl_mb) + (est_total_rows * per_row_bytes / (1024*1024))
proj_idx_mb = (current_idx_mb) + (est_total_rows * per_row_bytes / (1024*1024)) * 0.4  # index is ~40% of table
proj_total_mb = proj_tbl_mb + proj_idx_mb
proj_total_gb = proj_total_mb / 1024

print(f"\n=== RAW BACKFILL (no dedup) ===")
print(f"  Table: {proj_tbl_mb:,.0f} MB ({proj_tbl_mb/1024:.1f} GB)")
print(f"  Indexes: {proj_idx_mb:,.0f} MB ({proj_idx_mb/1024:.1f} GB)")
print(f"  Total: {proj_total_mb:,.0f} MB ({proj_total_gb:.1f} GB)")
print(f"  vs today: {current_total_mb} MB")
print(f"  Increase: {proj_total_mb - current_total_mb:,.0f} MB ({proj_total_gb:.1f} GB)")

# Dedup scenario: these serials span Jul 1-8 (8 days)
# Daily dedup: one row per (serial, machine, day) + best-good fallback
# Average machines per serial: ~2
# So ~8 days × 2 machines = ~16 rows per serial
days = 8
avg_machines = 2
dedup_rows_per_serial = days * avg_machines + 2  # +2 for fallback records
dedup_total = len(missing) * dedup_rows_per_serial
dedup_tbl = (current_tbl_mb) + (dedup_total * per_row_bytes / (1024*1024))
dedup_idx = (current_idx_mb) + (dedup_total * per_row_bytes / (1024*1024)) * 0.4
dedup_total_mb = dedup_tbl + dedup_idx

print(f"\n=== DAILY DEDUP (one row per serial/machine/day + fallback) ===")
print(f"  Estimated rows: {dedup_total:,} ({dedup_total/est_total_rows*100:.1f}% of raw)")
print(f"  Table: {dedup_tbl:,.0f} MB")
print(f"  Indexes: {dedup_idx:,.0f} MB")
print(f"  Total: {dedup_total_mb:,.0f} MB ({dedup_total_mb/1024:.1f} GB)")
print(f"  vs today: {current_total_mb} MB")
print(f"  Increase: {dedup_total_mb - current_total_mb:,.0f} MB")

# Minimal scenario: just enough for fallback logic
# One good record per (serial, machine) — ~2 machines per serial
minimal_per_serial = avg_machines + 1  # one good + one latest
minimal_total = len(missing) * minimal_per_serial
minimal_tbl = (current_tbl_mb) + (minimal_total * per_row_bytes / (1024*1024))
minimal_idx = (current_idx_mb) + (minimal_total * per_row_bytes / (1024*1024)) * 0.4
minimal_total_mb = minimal_tbl + minimal_idx

print(f"\n=== MINIMAL (one good record per serial/machine for fallback) ===")
print(f"  Estimated rows: {minimal_total:,}")
print(f"  Total: {minimal_total_mb:,.0f} MB ({minimal_total_mb/1024:.1f} GB)")
print(f"  vs today: {current_total_mb} MB")
print(f"  Increase: {minimal_total_mb - current_total_mb:,.0f} MB")
