import sys, os
from pathlib import Path
p = Path('D:/BDR/DESTINATION/archive')
files = [f for f in p.rglob('*') if f.is_file()]
files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
for f in files[:20]:
    print(f'{f} - {os.path.getmtime(f)}')
