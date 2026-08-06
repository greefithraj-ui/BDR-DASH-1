"""Stage 2 verification: all 4 tests."""
import requests, json, time, sys
sys.path.insert(0, r"D:\BDR")

BASE = "http://127.0.0.1:8000"
FORMERLY_MISSING = "ra-ch2-hf3-w1-ds08-0000023"
NORMAL = "ra-ch2-hf3-w1-as10-0000047"

print("=" * 60)
print("TEST 1: Server startup — check no import errors", flush=True)
print("=" * 60)
try:
    r = requests.get(f"{BASE}/api/health", timeout=5)
    print(f"  Health check: HTTP {r.status_code}", flush=True)
except Exception as e:
    try:
        r = requests.get(f"{BASE}/", timeout=5)
        print(f"  Root check: HTTP {r.status_code}", flush=True)
    except Exception as e2:
        print(f"  Server not responding: {e2}", flush=True)
        sys.exit(1)

print(f"\n{'=' * 60}")
print("TEST 2: Formerly-missing serial (SQLite fallback was needed before)", flush=True)
print("=" * 60)
r = requests.get(f"{BASE}/api/old-data/search/{FORMERLY_MISSING}", timeout=30)
d = r.json()
print(f"  HTTP {r.status_code}", flush=True)
print(f"  ok: {d.get('ok')}", flush=True)
print(f"  count: {d.get('count')}", flush=True)
print(f"  index_source: {d.get('index_source')}", flush=True)
if d.get("results"):
    print(f"  serial_number: {d['results'][0].get('serial_number')}", flush=True)
    print(f"  avg_bdr: {d['results'][0].get('avg_bdr')}", flush=True)
test2_pass = d.get("ok") and d.get("count", 0) > 0 and d.get("index_source") == "pg"
print(f"  PASS: {test2_pass}", flush=True)

print(f"\n{'=' * 60}")
print("TEST 3: Normal serial (always had PG coverage)", flush=True)
print("=" * 60)
r = requests.get(f"{BASE}/api/old-data/search/{NORMAL}", timeout=30)
d = r.json()
print(f"  HTTP {r.status_code}", flush=True)
print(f"  ok: {d.get('ok')}", flush=True)
print(f"  count: {d.get('count')}", flush=True)
print(f"  index_source: {d.get('index_source')}", flush=True)
test3_pass = d.get("ok") and d.get("count", 0) > 0 and d.get("index_source") == "pg"
print(f"  PASS: {test3_pass}", flush=True)

print(f"\n{'=' * 60}")
print("TEST 4: New data ingestion (PG write path)", flush=True)
print("=" * 60)
import os
from pathlib import Path
archive_root = Path(r"D:\BDR\DESTINATION\archive")
latest_file = None
for machine_dir in sorted(archive_root.iterdir()):
    if not machine_dir.is_dir():
        continue
    for date_dir in sorted(machine_dir.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue
        files = sorted(date_dir.glob("*.json"), reverse=True)
        if files:
            latest_file = files[0]
            break
    if latest_file:
        break

if latest_file:
    print(f"  Latest archive file: {latest_file}", flush=True)
    r = requests.post(f"{BASE}/api/old-data/ingest-file",
        json={"file_path": str(latest_file)}, timeout=30)
    d = r.json()
    print(f"  Ingest response: HTTP {r.status_code}", flush=True)
    print(f"  ok: {d.get('ok')}", flush=True)
    print(f"  entries: {d.get('entries')}", flush=True)
    test4_pass = d.get("ok")
else:
    print("  No archive files found", flush=True)
    test4_pass = False
print(f"  PASS: {test4_pass}", flush=True)

print(f"\n{'=' * 60}")
print("FINAL VERDICT", flush=True)
print("=" * 60)
if test2_pass and test3_pass and test4_pass:
    print("ALL TESTS PASSED", flush=True)
else:
    print(f"FAILURES: test2={test2_pass}, test3={test3_pass}, test4={test4_pass}", flush=True)
