import sys, json, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = 'ra-ch3-lfk-w1-ag08-0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT content FROM live_bdr_raw WHERE machine_name = %s', ('aqc-28',))
    row = cur.fetchone()
    data = json.loads(row['content'])
    for k, v in data.get('slots', {}).items():
        if str(v.get('serial_number')).lower() == serial:
            from api import _count_workouts_from_completed_cycles
            cycles = v.get('bdr_state', {}).get('completed_cycles', [])
            w = _count_workouts_from_completed_cycles(cycles)
            print(f'Workouts computed: {w}')
