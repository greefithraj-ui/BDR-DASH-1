import sys, psycopg2, psycopg2.extras
sys.path.append('d:/BDR/data')
from postgres_db import get_connection
conn = get_connection()
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SET statement_timeout = 0;")
    cur.execute('''
        UPDATE archive_entries
        SET machine_avg_bdr = (
            SELECT avg(cast(value->>'bdr' as float))
            FROM jsonb_array_elements(
                case 
                    when content->'bdr_state'->'completed_cycles' is not null 
                    then content->'bdr_state'->'completed_cycles' 
                    else '[]'::jsonb 
                end
            )
        )
        WHERE content->'bdr_state'->'completed_cycles' is not null 
          AND jsonb_array_length(content->'bdr_state'->'completed_cycles') > 0
    ''')
print('Fixed avg_bdr for historical records.')
