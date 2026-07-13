import sys, json, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = '0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT machine_name, content FROM live_bdr_raw WHERE machine_name = %s', ('aqc-28',))
    row = cur.fetchone()
    data = json.loads(row['content'])
    for k, v in data.get('slots', {}).items():
        if serial in str(v.get('serial_number')):
            print('RAW DATA:')
            print(json.dumps(v, indent=2))
