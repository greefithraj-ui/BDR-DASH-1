import os
from pathlib import Path

p = Path('D:/BDR/DESTINATION/archive')
files = list(p.rglob('*0000038*'))
for f in files:
    print(f'FOUND FILE BY NAME: {f}')
files2 = list(p.rglob('*12.04*'))
for f in files2:
    print(f'FOUND FILE BY NAME: {f}')
print('Done searching file names')
