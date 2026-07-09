"""Pre-build archive index and SQLite DB in parallel, then start API."""
import sys, os, time, json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
os.environ["NO_STARTUP_INDEX"] = "1"

import api

# Delete partial DB if it exists
if os.path.exists(api._archive_db_path):
    os.remove(api._archive_db_path)

api._init_archive_db()

archive_root = api._get_archive_root()
if not archive_root:
    print("Archive root not found, exiting.")
    sys.exit(1)

print("Collecting file paths...")
all_files = list(archive_root.rglob("*.json"))
print(f"Found {len(all_files)} archive files.")

signature = api._collect_archive_signature(archive_root)

WORKERS = min(16, os.cpu_count() or 4)
chunk_size = max(1, (len(all_files) + WORKERS - 1) // WORKERS)
print(f"Processing with {WORKERS} workers ({chunk_size} files per chunk)...")

merged = {}
start = time.time()

def process_chunk(file_chunk):
    local = {}
    for snap_file in file_chunk:
        try:
            data = json.loads(snap_file.read_text("utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        saved_at = data.get("saved_at", "")
        for slot_key, slot_data in data.get("slots", {}).items():
            sn = slot_data.get("serial_number", "").strip()
            if not sn or sn in ("--", "N/A"):
                continue
            serial_key = sn.lower()
            entry_key = api._archive_entry_key(snap_file.parent.parent.name, slot_key)
            slot_entries = local.setdefault(serial_key, {})
            existing = slot_entries.get(entry_key)
            if not existing or saved_at > existing.get("saved_at", ""):
                entry = api._make_archive_entry(snap_file, saved_at, slot_key, slot_data)
                slot_entries[entry_key] = entry
    return local

with ThreadPoolExecutor(max_workers=WORKERS) as executor:
    futures = [
        executor.submit(process_chunk, all_files[i:i + chunk_size])
        for i in range(0, len(all_files), chunk_size)
    ]
    for idx, future in enumerate(as_completed(futures)):
        try:
            chunk_results = future.result()
            for serial_key, entries in chunk_results.items():
                target = merged.setdefault(serial_key, {})
                for key, entry in entries.items():
                    existing = target.get(key)
                    if not existing or entry.get("saved_at", "") > existing.get("saved_at", ""):
                        target[key] = entry
        except Exception as e:
            print(f"  Chunk {idx + 1} failed: {e}")
        if (idx + 1) % 5 == 0:
            elapsed = time.time() - start
            print(f"  {idx + 1}/{len(futures)} chunks done ({elapsed:.0f}s)")

api._save_archive_index_cache(signature, merged)
total_entries = sum(len(v) for v in merged.values())
elapsed = time.time() - start
print(f"Index built in {elapsed:.0f}s: {len(merged)} serials, {total_entries} entries, cache saved.")


print("Starting API server...")

import uvicorn
uvicorn.run(api.app, host="0.0.0.0", port=8000)
