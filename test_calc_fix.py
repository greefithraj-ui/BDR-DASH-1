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
            completed = v.get("bdr_state", {}).get("completed_cycles", [])
            print(f'completed_cycles length: {len(completed)}')
            values = [c.get("bdr") for c in completed if c.get("bdr") is not None]
            print(f'BDR values: {values}')
            if values:
                print(f'Avg: {sum(values) / len(values)}')
