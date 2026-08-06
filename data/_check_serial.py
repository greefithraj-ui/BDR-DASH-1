"""Check if RA-CH3-LFN-W1-AA08-0000102 exists anywhere."""
import sys
sys.path.insert(0, r"D:\BDR")
target = "ra-ch3-lfn-w1-aa08-0000102"

# 1. Check PG archive_entries
from data.postgres_db import get_connection
pg_conn = get_connection()
with pg_conn.cursor() as cur:
    cur.execute("SELECT * FROM archive_entries WHERE serial_lower = %s ORDER BY saved_at DESC", (target,))
    pg_rows = cur.fetchall()
    pg_cols = [d[0] for d in cur.description] if pg_rows else []
    print(f"PG archive_entries: {len(pg_rows)} rows")

with pg_conn.cursor() as cur:
    cur.execute("SELECT * FROM ring_status WHERE LOWER(serial_number) = %s", (target,))
    rs_rows = cur.fetchall()
    rs_cols = [d[0] for d in cur.description] if rs_rows else []
    print(f"PG ring_status: {len(rs_rows)} rows")

# Check if it exists with LIKE (maybe typo)
with pg_conn.cursor() as cur:
    cur.execute("SELECT DISTINCT serial_lower, machine FROM archive_entries WHERE serial_lower LIKE %s", (f"%aa08-0000102%",))
    like_rows = cur.fetchall()
    print(f"PG LIKE match: {like_rows}")

with pg_conn.cursor() as cur:
    cur.execute("SELECT DISTINCT LOWER(serial_number), machine FROM ring_status WHERE LOWER(serial_number) LIKE %s", (f"%aa08-0000102%",))
    rs_like = cur.fetchall()
    print(f"ring_status LIKE match: {rs_like}")
pg_conn.close()

# 2. Check SQLite
import sqlite3, os
db_path = os.path.join(r"D:\BDR\data", "archive.db")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path, timeout=60)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM archive_entries WHERE LOWER(serial_number) = ? ORDER BY saved_at DESC LIMIT 5", (target,))
    sq_rows = cur.fetchall()
    print(f"SQLite archive_entries: {len(sq_rows)} rows")
    if sq_rows:
        for r in sq_rows:
            print(f"  machine={r['machine']}, saved_at={r['saved_at'][:19]}, state={r['state']}")
    # Also try LIKE
    cur.execute("SELECT DISTINCT LOWER(serial_number), machine FROM archive_entries WHERE LOWER(serial_number) LIKE ?", (f"%aa08-0000102%",))
    sq_like = cur.fetchall()
    print(f"SQLite LIKE match: {sq_like}")
    conn.close()
else:
    print("SQLite archive.db not found")

# 3. Check raw files on disk
import os
archive_root = os.path.join(r"D:\BDR\DESTINATION", "archive")
if os.path.isdir(archive_root):
    found = []
    for machine_dir in os.listdir(archive_root):
        machine_path = os.path.join(archive_root, machine_dir)
        if not os.path.isdir(machine_path):
            continue
        for date_dir in os.listdir(machine_path):
            date_path = os.path.join(machine_path, date_dir)
            if not os.path.isdir(date_path):
                continue
            for fname in os.listdir(date_path):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(date_path, fname)
                try:
                    import json
                    with open(fpath, "r") as f:
                        data = json.load(f)
                    for slot_id, slot_data in data.get("slots", {}).items():
                        if slot_data.get("serial_number", "").lower() == target:
                            found.append((machine_dir, date_dir, fname, slot_data.get("state")))
                except:
                    pass
    print(f"Raw JSON files on disk: {len(found)} matches")
    for m, d, f, s in found[:5]:
        print(f"  {m}/{d}/{f} state={s}")
else:
    print("Archive directory not found")
