import sys, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = 'ra-ch3-lfk-w1-ag08-0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT content FROM archive_entries WHERE serial_lower = %s', (serial,))
    rows = cur.fetchall()
    found = False
    for row in rows:
        rec = row['content']
        bdr = rec.get('avg_bdr')
        cycles = rec.get('completed_cycles', 0)
        state = rec.get('state')
        if bdr is not None or cycles > 5 or state != 'BDR_RUNNING':
            print(f'Machine: {rec.get("machine")} | State: {state} | Cycles: {cycles} | BDR: {bdr} | saved_at: {rec.get("saved_at")}')
            found = True
    if not found:
        print(f'No valid rows found in {len(rows)} records for {serial}')
