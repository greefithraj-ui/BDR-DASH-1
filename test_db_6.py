import sys, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = 'ra-ch3-lfk-w1-ag08-0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT content FROM archive_entries WHERE serial_lower = %s ORDER BY saved_at DESC', (serial,))
    rows = cur.fetchall()
    for i, row in enumerate(rows):
        rec = row['content']
        cycles = rec.get('completed_cycles', 0)
        bdr = rec.get('avg_bdr')
        if cycles == 6 or (bdr is not None and abs(bdr - 12.04) < 0.1):
            print(f'FOUND: {rec.get("saved_at")} | State: {rec.get("state")} | Cycles: {cycles} | BDR: {bdr}')
