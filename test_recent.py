import sys, os
from pathlib import Path
p = Path('D:/BDR/DESTINATION/archive')
files = list(p.rglob('*.json'))
files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
for f in files[:10]:
    print(f"{f} - {os.path.getmtime(f)}")
