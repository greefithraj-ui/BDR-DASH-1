"""Step 2: Insert deduped backfill chunks into PostgreSQL."""
import json, time, os, sys
sys.path.insert(0, r"D:\BDR")
from data.postgres_db import get_connection

CHUNKS_DIR = r"D:\BDR\data\bf_chunks"
BATCH_SIZE = 1000

pg_conn = get_connection()
t0 = time.time()
total_inserted = 0
total_skipped = 0
total_errors = 0

for fn in sorted(os.listdir(CHUNKS_DIR)):
    if not (fn.startswith("chunk_") and fn.endswith(".json")):
        continue
    with open(os.path.join(CHUNKS_DIR, fn)) as f:
        rows = json.load(f)
    print(f"\n{fn}: {len(rows):,} rows", flush=True)

    inserted = 0
    skipped = 0
    errors = 0
    t1 = time.time()

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i+BATCH_SIZE]
        try:
            with pg_conn.cursor() as cur:
                for r in batch:
                    try:
                        cur.execute("""
                            INSERT INTO archive_entries (
                                serial_number, serial_lower, machine, state, machine_avg_bdr, bdr,
                                snapshots, total_cycles, completed_cycles, start_time, last_update,
                                saved_at, date, time, slot, battery_current, firmware_version,
                                ring_mac, ring_name, avg_bdr, avg_bdr_is_stale, avg_bdr_is_estimated,
                                stored_avg_bdr, inter_cycle_avg_bdr, test_start, phase, cycle,
                                completed_workouts
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (serial_number, machine, saved_at) DO NOTHING
                        """, (
                            r.get("serial_number"), r.get("serial_lower"), r.get("machine"),
                            r.get("state"), r.get("machine_avg_bdr") or r.get("avg_bdr"),
                            r.get("bdr"), r.get("snapshots"), r.get("total_cycles"),
                            r.get("completed_cycles"), r.get("start_time"), r.get("last_update"),
                            r.get("saved_at"), r.get("date"), r.get("time"), r.get("slot"),
                            r.get("battery_current"), r.get("firmware_version"),
                            r.get("ring_mac"), r.get("ring_name"), r.get("avg_bdr"),
                            r.get("avg_bdr_is_stale", False), r.get("avg_bdr_is_estimated", False),
                            r.get("stored_avg_bdr"), r.get("inter_cycle_avg_bdr"),
                            r.get("test_start"), r.get("phase"), r.get("cycle"),
                            r.get("completed_workouts"),
                        ))
                        inserted += 1
                    except Exception as e:
                        pg_conn.rollback()
                        errors += 1
                        if errors <= 3:
                            print(f"    Error: {e}", flush=True)
            pg_conn.commit()
        except Exception as e:
            pg_conn.rollback()
            errors += len(batch)

    total_inserted += inserted
    total_skipped += skipped
    total_errors += errors
    elapsed = time.time() - t1
    print(f"  Inserted: {inserted:,}, Errors: {errors}, Time: {elapsed:.0f}s ({inserted/elapsed:.0f}/s)", flush=True)

pg_conn.close()
elapsed = time.time() - t0
print(f"\n=== TOTAL ===")
print(f"Inserted: {total_inserted:,}")
print(f"Errors: {total_errors}")
print(f"Time: {elapsed:.0f}s ({total_inserted/elapsed:.0f}/s)")
