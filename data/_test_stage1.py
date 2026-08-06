"""Stage 1 verification: test both formerly-missing and normal serials via HTTP."""
import requests, json, sys

BASE = "http://127.0.0.1:8000"

# Test serials
FORMERLY_MISSING = "ra-ch2-hf3-w1-ds08-0000023"
NORMAL = "ra-ch2-hf3-w1-as10-0000047"

def test_serial(label, serial):
    print(f"\n{'='*60}", flush=True)
    print(f"TEST: {label} ({serial})", flush=True)
    print(f"{'='*60}", flush=True)

    url = f"{BASE}/api/old-data/search/{serial}"
    print(f"GET {url}", flush=True)
    r = requests.get(url, timeout=30)
    data = r.json()

    print(f"  HTTP {r.status_code}", flush=True)
    print(f"  ok: {data.get('ok')}", flush=True)
    print(f"  count: {data.get('count')}", flush=True)
    print(f"  index_source: {data.get('index_source')}", flush=True)

    results = data.get("results", [])
    if results:
        print(f"  results[0] keys: {list(results[0].keys())[:10]}...", flush=True)
        print(f"  serial_number: {results[0].get('serial_number')}", flush=True)
        print(f"  machine: {results[0].get('machine')}", flush=True)
        print(f"  avg_bdr: {results[0].get('avg_bdr')}", flush=True)
        print(f"  saved_at: {results[0].get('saved_at')}", flush=True)
    else:
        print(f"  NO RESULTS!", flush=True)

    return data

# Also test multi-serial (both at once)
print(f"\n{'='*60}", flush=True)
print(f"TEST: Multi-serial search", flush=True)
print(f"{'='*60}", flush=True)
r = requests.post(f"{BASE}/api/old-data/search",
    json={"serials": [FORMERLY_MISSING, NORMAL]}, timeout=30)
data = r.json()
print(f"  HTTP {r.status_code}", flush=True)
print(f"  ok: {data.get('ok')}", flush=True)
print(f"  count: {data.get('count')}", flush=True)
print(f"  index_source: {data.get('index_source')}", flush=True)
print(f"  serials: {data.get('serials')}", flush=True)

# Final verdict
print(f"\n{'='*60}", flush=True)
d1 = test_serial("Formerly-missing", FORMERLY_MISSING)
d2 = test_serial("Normal", NORMAL)
print(f"\n{'='*60}", flush=True)
if d1.get("ok") and d1.get("count", 0) > 0 and d2.get("ok") and d2.get("count", 0) > 0:
    if d1.get("index_source") == "pg" and d2.get("index_source") == "pg":
        print("ALL TESTS PASSED - index_source: pg, both serials return results", flush=True)
    else:
        print(f"PARTIAL PASS - results present but index_source not 'pg': {d1.get('index_source')}, {d2.get('index_source')}", flush=True)
else:
    print("FAILURE - one or more serials returned no results", flush=True)
    print(f"  Formerly-missing: ok={d1.get('ok')}, count={d1.get('count')}", flush=True)
    print(f"  Normal: ok={d2.get('ok')}, count={d2.get('count')}", flush=True)
