import sys, psycopg2, psycopg2.extras, json
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = 'ra-ch3-lfk-w1-ag08-0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT content FROM archive_entries WHERE serial_lower = %s LIMIT 1', (serial,))
    row = cur.fetchone()
    print(row['content'].get('file_path'))
