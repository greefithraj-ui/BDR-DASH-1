import sys, json, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = 'ra-ch3-lfk-w1-ag08-0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT content FROM archive_entries WHERE serial_lower = %s ORDER BY saved_at DESC', (serial,))
    rows = cur.fetchall()
    valid = []
    for i, row in enumerate(rows):
        rec = row['content']
        if rec.get('avg_bdr') is not None or rec.get('completed_cycles', 0) > 0 or rec.get('state') != 'BDR_RUNNING':
            valid.append(rec)
    print(f'Found {len(valid)} valid rows out of {len(rows)}.')
    for rec in valid:
        print(f'saved_at: {rec.get("saved_at")} | state: {rec.get("state")} | cycles: {rec.get("completed_cycles")} | bdr: {rec.get("avg_bdr")} | machine: {rec.get("machine")}')
