import sys, json
from pathlib import Path
sys.path.append('d:/BDR/data')
from api import _calc_avg_bdr
p = Path('d:/BDR/data/archive')
files = list(p.rglob('*.json'))
found = False
for f in files:
    with open(f) as fd:
        data = json.load(fd)
        for k, v in data.get('slots', {}).items():
            if '0000038' in str(v.get('serial_number')):
                avg, _ = _calc_avg_bdr(v)
                cycles = v.get('bdr_state', {}).get('completed_cycles', [])
                if avg is not None or len(cycles) > 5:
                    print(f'File: {f}')
                    print(f'BDR: {avg} | Cycles: {len(cycles)} | State: {v.get("state")}')
                    found = True
if not found:
    print('Not found in any JSON file!')
