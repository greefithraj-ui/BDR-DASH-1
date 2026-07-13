import sys, psycopg2, psycopg2.extras, json
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT content FROM archive_entries')
    rows = cur.fetchall()
    for row in rows:
        data = row['content']
        for k, v in data.get('slots', {}).items():
            bdr_state = v.get('bdr_state', {})
            cycles = bdr_state.get('completed_cycles', [])
            if len(cycles) == 6:
                total = sum([c.get('bdr', 0) for c in cycles])
                if abs(total / 6.0 - 12.04) < 0.1:
                    print(f"FOUND 12.04 AVG BDR ON SERIAL: {v.get('serial_number')}")
                    sys.exit(0)
    print("No 6-cycle ring with 12.04 avg BDR found.")
