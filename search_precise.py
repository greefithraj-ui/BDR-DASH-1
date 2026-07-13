import sys, os, json
from multiprocessing import Pool
from pathlib import Path

def check_file(f):
    try:
        with open(f, 'r', encoding='utf-8') as fd:
            content = fd.read()
            if '0000038' not in content:
                return None
            data = json.loads(content)
            for k, v in data.get('slots', {}).items():
                if '0000038' in str(v.get('serial_number')).upper():
                    bdr_state = v.get('bdr_state', {})
                    cycles = bdr_state.get('completed_cycles', [])
                    if len(cycles) == 6:
                        return f'MATCH 6 CYCLES: {f}'
                    for c in cycles:
                        if abs(c.get('bdr', 0) - 12.04) < 0.1:
                            return f'MATCH 12.04 BDR: {f}'
    except:
        pass
    return None

if __name__ == '__main__':
    p = Path('D:/BDR/DESTINATION/archive')
    files = list(p.rglob('*.json'))
    with Pool(8) as pool:
        for result in pool.imap_unordered(check_file, files, chunksize=1000):
            if result:
                print(result)
                sys.exit(0)
    print('No match found.')
