import os
import sys
import json
import psycopg2
import psycopg2.extras
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.postgres_db import get_connection, init_db
from data.api import _make_archive_entry

def _get_archive_root():
    machines_json_path = Path(__file__).resolve().parent.parent / "machines.json"
    if not machines_json_path.exists():
        return None
    with machines_json_path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    destination = config.get("destination", "")
    if not destination:
        return None
    archive = Path(destination) / "archive"
    return archive if archive.is_dir() else None

# Process chunk function that just returns parsed records instead of hitting DB
def process_chunk(file_chunk):
    records = []
    for snap_file_str in file_chunk:
        snap_file = Path(snap_file_str)
        try:
            with open(snap_file, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
        except Exception:
            continue
            
        saved_at = data.get("saved_at", "")
        for slot_key, slot_data in data.get("slots", {}).items():
            sn = slot_data.get("serial_number", "").strip()
            if not sn or sn in ("--", "N/A"):
                continue
                
            try:
                # Fully enrich the data exactly how the API expects it
                entry = _make_archive_entry(snap_file, saved_at, slot_key, slot_data)
                records.append(entry)
            except Exception:
                pass
                
    return records

def migrate():
    print("Initializing PostgreSQL schema...")
    init_db()
    
    conn = get_connection()
    if not conn:
        print("Could not connect to PostgreSQL.")
        return
        
    print("Resuming migration without truncating existing data...")
    
    archive_root = _get_archive_root()
    if not archive_root:
        print("Archive root not found. Nothing to migrate.")
        return
        
    print("Collecting all JSON files from archive (this may take a moment)...")
    # Convert to string to pass safely to processes
    all_files = [str(p) for p in archive_root.rglob("*.json")]
    print(f"Found {len(all_files)} archive files.")
    
    WORKERS = min(8, os.cpu_count() or 4)
    chunk_size = 500  # Smaller chunks to return frequently
    
    total_success = 0
    total_fail = 0
    
    # We will use execute_values for fast bulk inserts
    insert_query = """
        INSERT INTO archive_entries (
            serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
            snapshots, total_cycles, completed_cycles, start_time, last_update, saved_at, content
        ) VALUES %s
        ON CONFLICT (serial_number, machine, saved_at) DO NOTHING
    """
    
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = [
            executor.submit(process_chunk, all_files[i:i + chunk_size])
            for i in range(0, len(all_files), chunk_size)
        ]
        
        for idx, future in enumerate(as_completed(futures)):
            try:
                records = future.result()
                if not records:
                    continue
                    
                # Prepare bulk data
                bulk_data = []
                for rec in records:
                    bulk_data.append((
                        rec.get("serial_number"),
                        str(rec.get("serial_number", "")).lower(),
                        rec.get("machine"),
                        rec.get("state"),
                        rec.get("machine_avg_bdr"),
                        rec.get("bdr"),
                        rec.get("snapshots"),
                        rec.get("total_cycles"),
                        rec.get("completed_cycles"),
                        rec.get("start_time"),
                        rec.get("last_update"),
                        rec.get("saved_at"),
                        json.dumps(rec)
                    ))
                
                # Bulk insert
                try:
                    with conn.cursor() as cur:
                        psycopg2.extras.execute_values(cur, insert_query, bulk_data, page_size=1000)
                    conn.commit()
                    total_success += len(bulk_data)
                except Exception as db_err:
                    conn.rollback()
                    print(f"  DB Insert failed for a chunk: {db_err}")
                    total_fail += len(bulk_data)
                    
            except Exception as e:
                print(f"  Chunk {idx + 1} processing failed: {e}")
                
            if (idx + 1) % 10 == 0:
                print(f"  {idx + 1}/{len(futures)} chunks processed. Inserted: {total_success}...")
                
    conn.close()
    print(f"\nMigration Complete!")
    print(f"Successfully Migrated (Enriched Entries): {total_success}")
    print(f"Failed: {total_fail}")

if __name__ == "__main__":
    migrate()
