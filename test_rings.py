import sys, json, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = '0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT machine_name, content FROM live_rings_raw')
    rows = cur.fetchall()
    for row in rows:
        data = json.loads(row['content'])
        for k, v in data.items():
            if serial in str(v.get('serial_number')):
                print(f'RINGS Machine: {row["machine_name"]} | Slot: {k}')
                print(json.dumps(v, indent=2))
