import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from postgres_db import get_connection, init_db
import psycopg2.extras
init_db()
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute("SELECT * FROM ring_status WHERE serial_number = %s ORDER BY machine", ("RA-CH2-LFK-W1-MG07-0000106",))
    rows = cur.fetchall()
    print(f"Rows for RA-CH2-LFK-W1-MG07-0000106: {len(rows)}")
    for r in rows:
        print(f"  machine={r['machine']}  state={r['state']}  saved_at={r['saved_at']}  cycle={r['cycle']}  avg_bdr={r['avg_bdr']}")
    print()

    cur.execute("SELECT COUNT(*) FROM ring_status")
    print(f"Total ring_status rows: {cur.fetchone()[0]}")

    cur.execute("SELECT * FROM ring_status WHERE serial_number = %s ORDER BY machine", ("RA-CH3-HF3-WB-AS09-0000111",))
    rows2 = cur.fetchall()
    print(f"\nRows for RA-CH3-HF3-WB-AS09-0000111: {len(rows2)}")
    for r in rows2:
        print(f"  machine={r['machine']}  state={r['state']}  saved_at={r['saved_at']}  cycle={r['cycle']}  avg_bdr={r['avg_bdr']}")
conn.close()
