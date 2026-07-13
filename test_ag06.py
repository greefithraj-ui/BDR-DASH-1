import sys, json, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
serial = 'ra-ch3-lfk-w1-ag06-0000038'
conn = get_connection()
with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
    cur.execute('SELECT content FROM live_bdr_raw WHERE machine_name = %s', ('aqc-15',))
    row = cur.fetchone()
    data = json.loads(row['content'])
    for k, v in data.get('slots', {}).items():
        if str(v.get('serial_number')).lower() == serial:
            from api import _count_workouts_from_completed_cycles, _calc_avg_bdr
            cycles = v.get('bdr_state', {}).get('completed_cycles', [])
            print(f'Cycles: {len(cycles)}')
            avg, est = _calc_avg_bdr(v)
            print(f'Avg BDR: {avg}')
            print(json.dumps(cycles, indent=2))
