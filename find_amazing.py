import sys, os, json
from pathlib import Path
p = Path('D:/BDR/DESTINATION/archive')
files = list(p.rglob('*.json'))
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fd:
            content = fd.read()
            if '12.04' in content and '0000038' in content:
                print(f'FOUND AMAZING FILE: {f}')
    except:
        pass
