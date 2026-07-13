import sys, json, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = '0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT machine_name, downloaded_at, content FROM live_bdr_raw')
    rows = cur.fetchall()
    for row in rows:
        machine = row['machine_name']
        data = json.loads(row['content'])
        for k, v in data.get('slots', {}).items():
            if serial in str(v.get('serial_number')):
                print(f'LIVE Machine: {machine}')
                bdr_state = v.get('bdr_state', {})
                cycles = bdr_state.get('completed_cycles', [])
                print(f'State: {v.get("state")} | Cycles: {len(cycles)} | Last Update: {row["downloaded_at"]}')
