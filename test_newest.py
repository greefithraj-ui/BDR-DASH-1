import sys, os, json
from pathlib import Path
p = Path('D:/BDR/DESTINATION/archive')
files = list(p.rglob('*.json'))
files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
for f in files[:50]:
    with open(f, 'r') as fd:
        content = fd.read()
        if '0000038' in content:
            print(f'FOUND IN: {f}')
            data = json.loads(content)
            for k, v in data.get('slots', {}).items():
                if '0000038' in str(v.get('serial_number')):
                    print(json.dumps(v.get('bdr_state'), indent=2))
